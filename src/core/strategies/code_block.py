"""
代码块追溯策略
"""

from dataclasses import dataclass
from typing import List, Optional, Set

from src.core.result import TraceResult
from src.core.strategies.base import TraceStrategy


@dataclass
class CodeBlock:
    """代码块"""

    file_path: str
    start_line: int
    end_line: int
    content: str
    lines: List[str]


class CodeBlockStrategy(TraceStrategy):
    """代码块追溯策略"""

    def trace(self, fix_commit: str, target_ref: str) -> TraceResult:
        """执行追溯"""
        code_block = self._extract_fix_code_block(fix_commit)
        if not code_block:
            return TraceResult.not_found()

        query_lines = self._normalize_lines(code_block.lines)
        if not query_lines:
            return TraceResult.not_found()

        for commit in self.repo.iter_commits(target_ref, max_count=500):
            if not commit.parents:
                continue
            parent = commit.parents[0]
            for diff in parent.diff(commit, create_patch=True):
                added = self._extract_added_content(diff)
                score = self._overlap(query_lines, self._normalize_lines(added))
                if score >= 0.8:
                    return TraceResult(
                        found=True,
                        commit=commit.hexsha,
                        method="code_block",
                        confidence=min(0.95, score),
                        details={
                            "file": diff.b_path or diff.a_path,
                            "lines": [code_block.start_line, code_block.end_line],
                            "match_score": score,
                        },
                    )

        return TraceResult.not_found()

    def _extract_fix_code_block(self, commit_hash: str) -> Optional[CodeBlock]:
        """提取修复commit修改的代码块"""
        commit = self.repo.get_commit(commit_hash)
        if not commit.parents:
            return None

        for diff in commit.parents[0].diff(commit):
            if diff.change_type in {"M", "A"}:
                diff_text = self._to_text(diff.diff)
                added_lines = self._extract_added_lines(diff_text)
                if added_lines:
                    return CodeBlock(
                        file_path=diff.b_path or diff.a_path or "",
                        start_line=min(added_lines),
                        end_line=max(added_lines),
                        content=self._get_code_at_lines(commit, diff.b_path or diff.a_path or "", added_lines),
                        lines=self._get_lines_at_lines(commit, diff.b_path or diff.a_path or "", added_lines),
                    )

        return None

    def _extract_added_lines(self, diff_text: str) -> List[int]:
        """从diff中提取新增的行号"""
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

    def _get_code_at_lines(self, commit, file_path: str, lines: List[int]) -> str:
        """获取指定行的代码"""
        content = self.repo.get_file_content(commit, file_path)
        if not content:
            return ""

        all_lines = content.split("\n")
        return "\n".join(all_lines[min(lines) - 1 : max(lines)])

    def _get_lines_at_lines(self, commit, file_path: str, lines: List[int]) -> List[str]:
        """获取指定行的内容"""
        content = self.repo.get_file_content(commit, file_path)
        if not content:
            return []

        all_lines = content.split("\n")
        return [all_lines[i - 1] for i in lines if 0 < i <= len(all_lines)]

    def _extract_added_content(self, diff) -> List[str]:
        patch_text = self._to_text(diff.diff)
        lines: List[str] = []
        for line in patch_text.split("\n"):
            if line.startswith("+") and not line.startswith("+++"):
                lines.append(line[1:])
        return lines

    def _to_text(self, value) -> str:
        if isinstance(value, bytes):
            return value.decode("utf-8", errors="ignore")
        if isinstance(value, str):
            return value
        return ""

    def _normalize_lines(self, lines: List[str]) -> Set[str]:
        normalized = set()
        for line in lines:
            text = " ".join(line.strip().split())
            if text:
                normalized.add(text)
        return normalized

    def _overlap(self, left: Set[str], right: Set[str]) -> float:
        if not left or not right:
            return 0.0
        return len(left & right) / len(left)

    @property
    def priority(self) -> int:
        return 2

    @property
    def confidence(self) -> float:
        return 0.95
