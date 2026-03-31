"""
追溯策略基类
"""

from abc import ABC, abstractmethod
from src.core.result import TraceResult
from src.git.repo import GitRepository


class TraceStrategy(ABC):
    """追溯策略抽象基类"""
    
    def __init__(self, repo: GitRepository):
        self.repo = repo
    
    @abstractmethod
    def trace(self, fix_commit: str, target_repo: GitRepository, 
              target_ref: str) -> TraceResult:
        """执行追溯"""
        pass
    
    @property
    @abstractmethod
    def priority(self) -> int:
        """策略优先级"""
        pass
    
    @property
    @abstractmethod
    def confidence(self) -> float:
        """策略置信度"""
        pass
