"""
相似度搜索策略
"""

from src.core.strategies.base import TraceStrategy
from src.core.result import TraceResult
from src.git.repo import GitRepository


class SimilarityStrategy(TraceStrategy):
    """相似度搜索策略"""
    
    def __init__(self, repo: GitRepository, threshold: float = 0.85):
        super().__init__(repo)
        self.threshold = threshold
    
    def trace(self, fix_commit: str, target_repo: GitRepository,
              target_ref: str) -> TraceResult:
        """执行追溯"""
        return TraceResult.not_found()
    
    @property
    def priority(self) -> int:
        return 4
    
    @property
    def confidence(self) -> float:
        return 0.85
