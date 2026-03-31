"""
相似度搜索策略测试
"""

import pytest
import git
from src.core.strategies.similarity import SimilarityStrategy
from src.core.result import TraceResult
from src.git.repo import GitRepository


class TestSimilarityStrategy:
    """相似度搜索策略测试"""
    
    @pytest.fixture
    def strategy(self, test_repo):
        return SimilarityStrategy(GitRepository(test_repo), threshold=0.85)
    
    def test_extract_code_snippet(self, strategy, test_repo):
        """测试提取代码片段"""
        git_repo = git.Repo(test_repo)
        
        test_file = test_repo / "test.py"
        test_file.write_text("def func(): return 1")
        git_repo.index.add(["test.py"])
        commit = git_repo.index.commit("Add function")
        
        snippet = strategy._extract_code_snippet(commit.hexsha)
        
        assert snippet is not None
        assert "def func" in snippet
    
    def test_priority(self, strategy):
        assert strategy.priority == 4
    
    def test_confidence(self, strategy):
        assert strategy.confidence == 0.85
