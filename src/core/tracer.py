"""
Bug追溯器
"""

from src.core.result import TraceResult
from src.core.strategies.commit_chain import CommitChainStrategy
from src.core.strategies.code_block import CodeBlockStrategy
from src.core.strategies.ast_structure import ASTStructureStrategy
from src.core.strategies.similarity import SimilarityStrategy
from src.git.repo import GitRepository
from src.config import Config


class BugTracer:
    """Bug追溯主引擎"""
    
    def __init__(self, config: Config, repo_path: str = '.'):
        self.config = config
        self.repo = GitRepository(repo_path)
        self.strategies = self._load_strategies()
    
    def _load_strategies(self) -> list:
        """加载追溯策略"""
        return [
            CommitChainStrategy(self.repo),
            CodeBlockStrategy(self.repo),
            ASTStructureStrategy(self.repo),
            SimilarityStrategy(self.repo, self.config.get_similarity_threshold())
        ]
    
    def trace(self, fix_commit: str, target_repo: GitRepository,
              target_ref: str) -> TraceResult:
        """追溯bug影响"""
        for strategy in self.strategies:
            result = strategy.trace(fix_commit, target_repo, target_ref)
            if result.found:
                return result
        
        return TraceResult.not_found()
