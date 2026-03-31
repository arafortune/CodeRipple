"""
AST结构追溯策略
"""

from src.core.strategies.base import TraceStrategy
from src.core.result import TraceResult
from src.git.repo import GitRepository


class ASTStructureStrategy(TraceStrategy):
    """AST结构追溯策略"""
    
    def trace(self, fix_commit: str, target_repo: GitRepository,
              target_ref: str) -> TraceResult:
        """执行追溯"""
        code_snippet = self._extract_code_snippet(fix_commit)
        if not code_snippet:
            return TraceResult.not_found()
        
        return TraceResult.not_found()
    
    def _extract_code_snippet(self, commit_hash: str) -> str:
        """提取代码片段"""
        return ""
    
    @property
    def priority(self) -> int:
        return 3
    
    @property
    def confidence(self) -> float:
        return 0.90
