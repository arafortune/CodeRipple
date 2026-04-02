"""
策略测试
"""

import pytest
import git
from src.core.strategies.commit_chain import CommitChainStrategy
from src.core.strategies.code_block import CodeBlockStrategy
from src.core.result import TraceResult
from src.git.repo import GitRepository


class TestCommitChainStrategy:
    """Commit链策略测试"""
    
    @pytest.fixture
    def strategy(self, test_repo):
        return CommitChainStrategy(GitRepository(test_repo))
    
    def test_trace_found(self, strategy, test_repo):
        """测试追溯成功"""
        git_repo = git.Repo(test_repo)
        
        test_file = test_repo / "test.txt"
        test_file.write_text("commit 1")
        git_repo.index.add(["test.txt"])
        commit1 = git_repo.index.commit("commit 1")
        
        test_file.write_text("commit 2")
        git_repo.index.add(["test.txt"])
        commit2 = git_repo.index.commit("commit 2")
        
        result = strategy.trace(commit1.hexsha, commit2.hexsha)
        
        assert result.found is True
        assert result.commit == commit1.hexsha
        assert result.method == "commit_chain"
        assert result.confidence == 1.0
    
    def test_trace_not_found(self, strategy, test_repo):
        """测试追溯失败"""
        git_repo = git.Repo(test_repo)
        
        git_repo.git.checkout("-b", "feature")
        test_file = test_repo / "feature.txt"
        test_file.write_text("feature")
        git_repo.index.add(["feature.txt"])
        commit1 = git_repo.index.commit("feature commit")
        
        git_repo.git.checkout("master")
        
        result = strategy.trace(commit1.hexsha, "master")
        
        assert result.found is False
    
    def test_priority(self, strategy):
        assert strategy.priority == 1
    
    def test_confidence(self, strategy):
        assert strategy.confidence == 1.0


class TestCodeBlockStrategy:
    """代码块策略测试"""
    
    @pytest.fixture
    def strategy(self, test_repo):
        return CodeBlockStrategy(GitRepository(test_repo))
    
    def test_extract_added_lines(self, strategy):
        """测试提取新增行"""
        diff_text = """@@ -1,3 +1,4 @@
 line 1
-line 2
+line 2 modified
 line 3
+line 4 new"""
        
        lines = strategy._extract_added_lines(diff_text)
        assert 2 in lines
        assert 4 in lines
    
    def test_priority(self, strategy):
        assert strategy.priority == 2
    
    def test_confidence(self, strategy):
        assert strategy.confidence == 0.95
