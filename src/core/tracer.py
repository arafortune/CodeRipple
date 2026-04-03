"""
Bug追溯器
"""

import copy
import re
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
        attempts = []
        for strategy in self.strategies:
            result = strategy.trace(fix_commit, target_ref)
            attempt = {
                "method": result.method or self._strategy_name(strategy),
                "found": result.found,
                "confidence": result.confidence,
                "details": copy.deepcopy(result.details),
            }
            attempts.append(attempt)
            if result.found:
                result.details.setdefault("target_ref", target_ref)
                result.details.setdefault("fix_commit", fix_commit)
                result.details["attempts"] = copy.deepcopy(attempts)
                return result
            if (
                result.details.get("contains_fix_commit")
                or result.details.get("equivalent_commit")
                or result.details.get("equivalent_state")
                or result.details.get("equivalent_ast_state")
            ):
                return TraceResult.not_found(
                    {
                        "target_ref": target_ref,
                        "fix_commit": fix_commit,
                        "attempts": copy.deepcopy(attempts),
                        "reason": result.details["reason"],
                        "equivalent_commit": result.details.get("equivalent_commit"),
                        "equivalent_state": result.details.get("equivalent_state"),
                        "equivalent_ast_state": result.details.get("equivalent_ast_state"),
                    }
                )

        return TraceResult.not_found(
            {
                "target_ref": target_ref,
                "fix_commit": fix_commit,
                "attempts": copy.deepcopy(attempts),
            }
        )

    def _strategy_name(self, strategy) -> str:
        """将策略类名转换为稳定的snake_case标识"""
        name = strategy.__class__.__name__.replace("Strategy", "")
        return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()
