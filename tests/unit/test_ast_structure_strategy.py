"""
AST结构追溯策略测试
"""

import pytest
import git
from src.core.strategies.ast_structure import ASTStructureStrategy
from src.core.result import TraceResult
from src.git.repo import GitRepository


class TestASTStructureStrategy:
    """AST结构追溯策略测试"""
    
    @pytest.fixture
    def strategy(self, test_repo):
        return ASTStructureStrategy(GitRepository(test_repo))
    
    def test_extract_code_snippet(self, strategy, test_repo):
        """测试提取代码片段"""
        git_repo = git.Repo(test_repo)
        
        test_file = test_repo / "test.py"
        test_file.write_text(
            "def func1():\n    return 1\n\n"
            "def func2():\n    value = 2\n    return value\n"
        )
        git_repo.index.add(["test.py"])
        git_repo.index.commit("Add functions")

        test_file.write_text(
            "def func1():\n    return 1\n\n"
            "def func2():\n    value = 3\n    return value\n"
        )
        git_repo.index.add(["test.py"])
        commit = git_repo.index.commit("Update function")
        
        snippet = strategy._extract_code_snippet(commit.hexsha)
        
        assert snippet is not None
        assert "def func2" in snippet
        assert "def func1" not in snippet

    def test_extract_candidate_paths(self, strategy, test_repo):
        """测试提取候选路径"""
        git_repo = git.Repo(test_repo)

        test_file = test_repo / "pkg" / "test.py"
        test_file.parent.mkdir()
        test_file.write_text("def func(): return 1")
        git_repo.index.add(["pkg/test.py"])
        commit = git_repo.index.commit("Add function")

        paths = strategy._extract_candidate_paths(commit.hexsha)

        assert "pkg/test.py" in paths

    def test_is_candidate_file_matches_basename(self, strategy):
        """测试按文件名过滤候选"""
        assert strategy._is_candidate_file("other/test.py", {"pkg/test.py"}) is True
        assert strategy._is_candidate_file("other/demo.py", {"pkg/test.py"}) is False
    
    def test_priority(self, strategy):
        assert strategy.priority == 3
    
    def test_confidence(self, strategy):
        assert strategy.confidence == 0.90
