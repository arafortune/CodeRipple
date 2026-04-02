"""
Commit链追溯策略
"""

from src.core.result import TraceResult
from src.core.strategies.base import TraceStrategy


class CommitChainStrategy(TraceStrategy):
    """Commit链追溯策略"""

    def trace(self, fix_commit: str, target_ref: str) -> TraceResult:
        """执行追溯"""
        fix_commit_obj = self.repo.get_commit(fix_commit)

        is_ancestor = self.repo.is_ancestor(fix_commit_obj.hexsha, target_ref)

        if is_ancestor:
            return TraceResult(
                found=True,
                commit=fix_commit_obj.hexsha,
                method="commit_chain",
                confidence=1.0,
                details={"reason": "commit is ancestor of target branch"},
            )

        return TraceResult.not_found()

    @property
    def priority(self) -> int:
        return 1

    @property
    def confidence(self) -> float:
        return 1.0
