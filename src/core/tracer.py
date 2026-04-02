"""
Bug追溯器
"""

from typing import List

from src.config import Config
from src.core.result import TraceResult
from src.core.strategies.ast_structure import ASTStructureStrategy
from src.core.strategies.code_block import CodeBlockStrategy
from src.core.strategies.commit_chain import CommitChainStrategy
from src.core.strategies.similarity import SimilarityStrategy
from src.git.repo import GitRepository

class BugTracer:
    """Bug追溯主引擎"""

    def __init__(self, config: Config, repo_path: str):
        self.config = config
        self.repo = GitRepository(repo_path)
        self.strategies = self._load_strategies()

    def _load_strategies(self) -> List:
        """加载追溯策略"""
        strategies = [
            CommitChainStrategy(self.repo),
            CodeBlockStrategy(self.repo),
            ASTStructureStrategy(self.repo),
            SimilarityStrategy(self.repo, self.config.get_similarity_threshold()),
        ]
        return sorted(strategies, key=lambda item: item.priority)

    def trace(self, fix_commit: str, target_ref: str) -> TraceResult:
        """追溯bug影响"""
        for strategy in self.strategies:
            result = strategy.trace(fix_commit, target_ref)
            if result.found:
                return result

        return TraceResult.not_found()
