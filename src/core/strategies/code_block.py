"""
代码块追溯策略
"""

from dataclasses import dataclass
from difflib import SequenceMatcher
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
    context_lines: List[str]


@dataclass
class PatchCandidate:
    """候选patch"""

    file_path: str
    added_lines: List[str]
    context_lines: List[str]
    line_numbers: List[int]
    source: str


class CodeBlockStrategy(TraceStrategy):
    """代码块追溯策略"""

    def trace(self, fix_commit: str, target_ref: str) -> TraceResult:
        """执行追溯"""
        code_block = self._extract_fix_code_block(fix_commit)
        if not code_block:
            return TraceResult.not_found()

        query_lines = self._normalize_lines(code_block.lines)
        query_context = self._normalize_lines(code_block.context_lines)
        if not query_lines:
            return TraceResult.not_found()

        for commit in self.repo.iter_commits(target_ref, max_count=500):
            if not commit.parents:
                continue
            parent = commit.parents[0]
            for candidate in self._build_patch_candidates(parent.diff(commit, create_patch=True)):
                candidate_lines = self._normalize_lines(candidate.added_lines)
                added_score = max(
                    self._overlap(query_lines, candidate_lines),
                    self._fuzzy_overlap(query_lines, candidate_lines),
                )
                score = self._calculate_match_score(
                    added_score,
                    self._overlap(query_context, self._normalize_lines(candidate.context_lines)),
                    bool(query_context),
                )
                if added_score >= 0.6 and score >= 0.75:
                    return TraceResult(
                        found=True,
                        commit=commit.hexsha,
                        method="code_block",
                        confidence=min(0.95, score),
                        details={
                            "file": candidate.file_path,
                            "lines": [code_block.start_line, code_block.end_line],
                            "match_score": score,
                            "added_score": added_score,
                            "candidate_source": candidate.source,
                        },
                    )

        return TraceResult.not_found()

    def _extract_fix_code_block(self, commit_hash: str) -> Optional[CodeBlock]:
        """提取修复commit修改的代码块"""
        commit = self.repo.get_commit(commit_hash)
        if not commit.parents:
            return None

        for candidate in self._build_patch_candidates(commit.parents[0].diff(commit, create_patch=True)):
            if candidate.line_numbers:
                return CodeBlock(
                    file_path=candidate.file_path,
                    start_line=min(candidate.line_numbers),
                    end_line=max(candidate.line_numbers),
                    content=self._get_code_at_lines(commit, candidate.file_path, candidate.line_numbers),
                    lines=self._get_lines_at_lines(commit, candidate.file_path, candidate.line_numbers),
                    context_lines=candidate.context_lines,
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

    def _extract_patch_content(self, diff_or_text) -> tuple[List[str], List[str]]:
        patch_text = self._to_text(diff_or_text.diff) if hasattr(diff_or_text, "diff") else self._to_text(diff_or_text)
        added_lines: List[str] = []
        context_lines: List[str] = []
        for line in patch_text.split("\n"):
            if line.startswith("+") and not line.startswith("+++"):
                added_lines.append(line[1:])
            elif line.startswith(" ") or line.startswith("@@"):
                if line.startswith(" "):
                    context_lines.append(line[1:])
        return added_lines, context_lines

    def _build_patch_candidates(self, diffs) -> List[PatchCandidate]:
        candidates: List[PatchCandidate] = []
        deleted: List[object] = []
        added: List[object] = []

        for diff in diffs:
            added_lines, context_lines = self._extract_patch_content(diff)

            if added_lines:
                candidates.append(
                    PatchCandidate(
                        file_path=diff.b_path or diff.a_path or "",
                        added_lines=added_lines,
                        context_lines=context_lines,
                        line_numbers=self._extract_added_lines(self._to_text(diff.diff)),
                        source="direct",
                    )
                )

            if diff.a_path and not diff.b_path:
                deleted.append(diff)
            elif diff.b_path and not diff.a_path:
                added.append(diff)

        candidates.extend(self._pair_move_candidates(deleted, added))
        return candidates

    def _pair_move_candidates(self, deleted_diffs, added_diffs) -> List[PatchCandidate]:
        candidates: List[PatchCandidate] = []
        used_added_paths: Set[str] = set()

        for deleted in deleted_diffs:
            best_added = None
            best_score = 0.0
            deleted_text = self._to_text(deleted.diff)

            for added in added_diffs:
                added_path = added.b_path or ""
                if not added_path or added_path in used_added_paths:
                    continue

                score = self._move_similarity(
                    deleted.a_path or "",
                    added_path,
                    deleted_text,
                    self._to_text(added.diff),
                )
                if score > best_score:
                    best_score = score
                    best_added = added

            if best_added is None or best_score < 0.45:
                continue

            added_lines, context_lines = self._extract_patch_content(best_added)
            line_numbers = self._extract_added_lines(self._to_text(best_added.diff))
            if not added_lines:
                continue

            added_path = best_added.b_path or ""
            used_added_paths.add(added_path)
            candidates.append(
                PatchCandidate(
                    file_path=added_path,
                    added_lines=added_lines,
                    context_lines=context_lines,
                    line_numbers=line_numbers,
                    source="paired_move",
                )
            )

        return candidates

    def _move_similarity(
        self,
        old_path: str,
        new_path: str,
        deleted_patch_text: str,
        added_patch_text: str,
    ) -> float:
        old_lines = self._extract_removed_content(deleted_patch_text)
        new_lines, _ = self._extract_patch_content(added_patch_text)
        content_score = self._overlap(
            self._normalize_lines(old_lines),
            self._normalize_lines(new_lines),
        )
        path_score = SequenceMatcher(None, old_path, new_path).ratio()
        return (0.8 * content_score) + (0.2 * path_score)

    def _extract_removed_content(self, diff_or_text) -> List[str]:
        patch_text = self._to_text(diff_or_text.diff) if hasattr(diff_or_text, "diff") else self._to_text(diff_or_text)
        removed_lines: List[str] = []
        for line in patch_text.split("\n"):
            if line.startswith("-") and not line.startswith("---"):
                removed_lines.append(line[1:])
        return removed_lines

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

    def _fuzzy_overlap(self, left: Set[str], right: Set[str]) -> float:
        if not left or not right:
            return 0.0

        total_score = 0.0
        right_lines = list(right)
        for line in left:
            total_score += max(SequenceMatcher(None, line, candidate).ratio() for candidate in right_lines)

        return total_score / len(left)

    def _calculate_match_score(self, added_score: float, context_score: float, has_context: bool) -> float:
        if not has_context:
            return added_score
        return (0.7 * added_score) + (0.3 * context_score)

    @property
    def priority(self) -> int:
        return 2

    @property
    def confidence(self) -> float:
        return 0.95
