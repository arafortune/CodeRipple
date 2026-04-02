"""
追溯器集成测试
"""

import pytest
import git
from src.core.tracer import BugTracer
from src.config import Config


class TestTracerFlow:
    """追溯器集成测试"""
    
    @pytest.fixture
    def tracer(self, test_repo):
        config = Config.default()
        return BugTracer(config, test_repo)
    
    def test_full_trace_flow(self, tracer, test_repo):
        """测试完整追溯流程"""
        git_repo = git.Repo(test_repo)
        
        git_repo.git.checkout("-b", "release/v1.0")
        
        bug_file = test_repo / "bug.py"
        bug_file.write_text("def buggy():\n    return 1 / 0\n")
        git_repo.index.add(["bug.py"])
        bug_commit = git_repo.index.commit("Introduce bug")
        
        git_repo.git.checkout("master")
        git_repo.git.merge("release/v1.0")
        
        bug_file.write_text("def buggy():\n    return 1 / 1\n")
        git_repo.index.add(["bug.py"])
        fix_commit = git_repo.index.commit("Fix bug")
        
        result = tracer.trace(fix_commit.hexsha, "release/v1.0")
        
        assert result.found is True
        assert result.confidence >= 0.9
    
    def test_strategy_chain(self, tracer, test_repo):
        """测试策略链"""
        git_repo = git.Repo(test_repo)
        
        test_file = test_repo / "test.txt"
        test_file.write_text("v1")
        git_repo.index.add(["test.txt"])
        commit1 = git_repo.index.commit("v1")
        
        test_file.write_text("v2")
        git_repo.index.add(["test.txt"])
        commit2 = git_repo.index.commit("v2")
        
        result = tracer.trace(commit1.hexsha, commit2.hexsha)
        
        assert result.found is True
        assert result.method in ["commit_chain", "code_block"]
