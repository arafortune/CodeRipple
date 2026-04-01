"""
Bug追溯器
"""

from core.result import TraceResult
from core.strategies.commit_chain import CommitChainStrategy
from core.strategies.code_block import CodeBlockStrategy
from core.strategies.ast_structure import ASTStructureStrategy
from core.strategies.similarity import SimilarityStrategy
from git.repo import GitRepository
from config import Config


class BugTracer:
    """Bug追溯主引擎"""
    
    def __init__(self, config: Config,   def __init__(self, str):
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
        for strategy in self.  def __init__(self, result):, target_repo, target_ref)
            if result.found:
                return result
        
        return TraceResult.not_found()
