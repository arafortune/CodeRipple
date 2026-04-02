"""
AST结构追溯策略
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Set

from src.core.result import TraceResult
from src.core.strategies.base import TraceStrategy
from src.git.repo import GitRepository
from src.parser.ast import ASTNode, ASTParser
from src.parser.normalizer import ASTNormalizer


@dataclass
class Match:
    """匹配结果"""

    commit: str
    file: str
    similarity: float
    nodes: List[ASTNode]


class ASTStructureStrategy(TraceStrategy):
    """AST结构追溯策略"""

    def __init__(self, repo: GitRepository):
        super().__init__(repo)
        self.parser = ASTParser("python")
        self.normalizer = ASTNormalizer()

    def trace(self, fix_commit: str, target_ref: str) -> TraceResult:
        """执行追溯"""
        code_snippet = self._extract_code_snippet(fix_commit)
        if not code_snippet:
            return TraceResult.not_found()
        candidate_paths = self._extract_candidate_paths(fix_commit)

        try:
            snippet_ast = self.parser.parse(code_snippet)
            if snippet_ast is None:
                return TraceResult.not_found()
        except Exception:
            return TraceResult.not_found()

        normalized_snippet = self.normalizer.normalize(snippet_ast)

        matches = self._search_ast_structure(normalized_snippet, target_ref, candidate_paths)
        if matches:
            best_match = matches[0]
            return TraceResult(
                found=True,
                commit=best_match.commit,
                method="ast_structure",
                confidence=0.90,
                details={
                    "file": best_match.file,
                    "similarity": best_match.similarity,
                    "matched_nodes": len(best_match.nodes),
                },
            )

        return TraceResult.not_found()

    def _extract_code_snippet(self, commit_hash: str) -> Optional[str]:
        """提取修复commit修改的代码片段"""
        commit = self.repo.get_commit(commit_hash)
        if not commit.parents:
            return None

        for diff in commit.parents[0].diff(commit, create_patch=True):
            path = diff.b_path or diff.a_path
            if not path:
                continue
            try:
                content = self.repo.get_file_content(commit, path)
                if not content:
                    continue
                changed_lines = self._extract_added_lines(self._to_text(diff.diff))
                if not changed_lines:
                    continue
                return self.parser.extract_relevant_snippet(content, changed_lines)
            except Exception:
                continue

        return None

    def _extract_added_lines(self, diff_text: str) -> List[int]:
        """从diff中提取新增行号"""
        added_lines: List[int] = []
        current_line = 0

        for line in diff_text.split("\n"):
            if line.startswith("@@"):
                parts = line.split(" ")
                if len(parts) < 3:
                    continue
                plus_part = parts[2]
                try:
                    current_line = int(plus_part[1:].split(",")[0])
                except ValueError:
                    current_line = 0
            elif line.startswith("+") and not line.startswith("+++"):
                added_lines.append(current_line)
                current_line += 1
            elif line.startswith("-") and not line.startswith("---"):
                continue
            else:
                current_line += 1

        return added_lines

    def _to_text(self, value) -> str:
        if isinstance(value, bytes):
            return value.decode("utf-8", errors="ignore")
        if isinstance(value, str):
            return value
        return ""

    def _search_ast_structure(self, query_ast, target_ref: str, candidate_paths: Set[str]) -> List[Match]:
        """在目标分支中搜索AST结构"""
        matches: List[Match] = []

        for commit in self.repo.iter_commits(target_ref, max_count=200):
            for item in commit.tree.traverse():
                if item.type != "blob":
                    continue

                file_path = item.path
                if not self._is_code_file(file_path):
                    continue
                if not self._is_candidate_file(file_path, candidate_paths):
                    continue

                try:
                    file_content = self.repo.get_file_content(commit, file_path)
                    if not file_content:
                        continue

                    file_ast = self.parser.parse(file_content)
                    if file_ast is None:
                        continue

                    normalized_file = self.normalizer.normalize(file_ast)
                    matched_nodes = self._find_subtree(normalized_file.root, query_ast.root)

                    if matched_nodes:
                        matches.append(
                            Match(
                                commit=commit.hexsha,
                                file=file_path,
                                similarity=1.0,
                                nodes=matched_nodes,
                            )
                        )
                except Exception:
                    continue

        matches.sort(key=lambda x: x.similarity, reverse=True)
        return matches

    def _extract_candidate_paths(self, commit_hash: str) -> Set[str]:
        """提取fix commit关联的候选文件路径"""
        commit = self.repo.get_commit(commit_hash)
        if not commit.parents:
            return set()

        paths: Set[str] = set()
        for diff in commit.parents[0].diff(commit):
            for path in (diff.a_path, diff.b_path):
                if path and self._is_code_file(path):
                    paths.add(path)
        return paths

    def _is_candidate_file(self, file_path: str, candidate_paths: Set[str]) -> bool:
        """检查文件是否在候选范围内"""
        if not candidate_paths:
            return True
        if file_path in candidate_paths:
            return True

        file_name = Path(file_path).name
        return any(file_name == Path(candidate).name for candidate in candidate_paths)

    def _find_subtree(self, tree: ASTNode, subtree: ASTNode) -> List[ASTNode]:
        """在树中查找子树"""
        matches: List[ASTNode] = []
        if self._match_node(tree, subtree):
            matches.append(tree)

        for child in tree.children:
            matches.extend(self._find_subtree(child, subtree))

        return matches

    def _match_node(self, node1: ASTNode, node2: ASTNode) -> bool:
        """检查两个节点是否匹配"""
        if node1.type != node2.type:
            return False

        if len(node1.children) != len(node2.children):
            return False

        for child1, child2 in zip(node1.children, node2.children):
            if not self._match_node(child1, child2):
                return False

        return True

    def _is_code_file(self, file_path: str) -> bool:
        """检查是否是代码文件"""
        code_extensions = [".py", ".c", ".cpp", ".h", ".java", ".go", ".js", ".ts"]
        return any(file_path.endswith(ext) for ext in code_extensions)

    @property
    def priority(self) -> int:
        return 3

    @property
    def confidence(self) -> float:
        return 0.90
