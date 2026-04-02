"""
相似度搜索策略
"""

from dataclasses import dataclass
from typing import List, Optional

from src.core.result import TraceResult
from src.core.strategies.base import TraceStrategy
from src.git.repo import GitRepository
from src.parser.features import FeatureExtractor
from src.parser.similarity import SimilarityCalculator


@dataclass
class Match:
    """匹配结果"""

    commit: str
    file: str
    similarity: float
    lines: List[int]


class SimilarityStrategy(TraceStrategy):
    """相似度搜索策略"""

    def __init__(self, repo: GitRepository, threshold: float):
        super().__init__(repo)
        self.threshold = threshold
        self.feature_extractor = FeatureExtractor("python")
        self.similarity_calculator = SimilarityCalculator()

    def trace(self, fix_commit: str, target_ref: str) -> TraceResult:
        """执行追溯"""
        code_snippet = self._extract_code_snippet(fix_commit)
        if not code_snippet:
            return TraceResult.not_found()

        try:
            query_features = self.feature_extractor.extract(code_snippet)
        except Exception:
            return TraceResult.not_found()

        matches = self._search_similar(query_features, target_ref)

        if matches:
            best_match = matches[0]
            if best_match.similarity >= self.threshold:
                return TraceResult(
                    found=True,
                    commit=best_match.commit,
                    method="similarity",
                    confidence=best_match.similarity,
                    details={
                        "file": best_match.file,
                        "similarity": best_match.similarity,
                        "matched_lines": best_match.lines,
                    },
                )

        return TraceResult.not_found()

    def _extract_code_snippet(self, commit_hash: str) -> Optional[str]:
        """提取修复commit修改的代码片段"""
        commit = self.repo.get_commit(commit_hash)
        if not commit.parents:
            return None

        for diff in commit.parents[0].diff(commit):
            if diff.change_type in {"M", "A"} and (diff.b_path or diff.a_path):
                try:
                    return self.repo.get_file_content(commit, diff.b_path or diff.a_path)  # type: ignore[arg-type]
                except Exception:
                    continue

        return None

    def _search_similar(self, query_features, target_ref: str) -> List[Match]:
        """搜索相似代码"""
        matches: List[Match] = []

        for commit in self.repo.iter_commits(target_ref, max_count=200):
            for item in commit.tree.traverse():
                if item.type != "blob":
                    continue

                file_path = item.path
                if not self._is_code_file(file_path):
                    continue

                try:
                    file_content = self.repo.get_file_content(commit, file_path)
                    if not file_content:
                        continue

                    file_features = self.feature_extractor.extract(file_content)

                    similarity = self.similarity_calculator.calculate(query_features, file_features)

                    if similarity > 0:
                        matches.append(Match(commit=commit.hexsha, file=file_path, similarity=similarity, lines=[]))
                except Exception:
                    continue

        matches.sort(key=lambda x: x.similarity, reverse=True)
        return matches

    def _is_code_file(self, file_path: str) -> bool:
        """检查是否是代码文件"""
        code_extensions = [".py", ".c", ".cpp", ".h", ".java", ".go", ".js", ".ts"]
        return any(file_path.endswith(ext) for ext in code_extensions)

    @property
    def priority(self) -> int:
        return 4

    @property
    def confidence(self) -> float:
        return 0.85
