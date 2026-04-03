"""
Git仓库单元测试
"""

import pytest
import git
from src.git.repo import GitRepository


class TestGitRepository:
    """Git仓库单元测试"""
    
    def test_init_repo(self, test_repo):
        """测试仓库初始化"""
        repo = GitRepository(test_repo)
        assert repo.repo is not None
    
    def test_get_commit(self, test_repo):
        """测试获取commit"""
        repo = GitRepository(test_repo)
        commit = repo.get_commit("HEAD")
        assert commit is not None
        assert commit.message == "Initial commit"
    
    def test_is_ancestor_true(self, test_repo):
        """测试祖先检查-是祖先"""
        repo = GitRepository(test_repo)
        
        git_repo = git.Repo(test_repo)
        test_file = test_repo / "test.txt"
        test_file.write_text("hello world")
        git_repo.index.add(["test.txt"])
        second_commit = git_repo.index.commit("Second commit")
        
        first_commit = git_repo.commit("HEAD~1")
        assert repo.is_ancestor(first_commit.hexsha, second_commit.hexsha)
    
    def test_is_ancestor_false(self, test_repo):
        """测试祖先检查-不是祖先"""
        repo = GitRepository(test_repo)
        
        git_repo = git.Repo(test_repo)
        git_repo.git.checkout("-b", "feature")
        
        test_file = test_repo / "feature.txt"
        test_file.write_text("feature")
        git_repo.index.add(["feature.txt"])
        feature_commit = git_repo.index.commit("Feature commit")
        
        git_repo.git.checkout("master")
        
        assert not repo.is_ancestor(feature_commit.hexsha, "master")
    
    def test_get_file_content(self, test_repo):
        """测试获取文件内容"""
        repo = GitRepository(test_repo)
        commit = repo.get_commit("HEAD")
        
        content = repo.get_file_content(commit, "README.md")
        assert content == "# Test Repo"
    
    def test_file_content_cache(self, test_repo):
        """测试文件内容缓存"""
        repo = GitRepository(test_repo)
        commit = repo.get_commit("HEAD")

        content1 = repo.get_file_content(commit, "README.md")
        content2 = repo.get_file_content(commit, "README.md")

        assert content1 == content2
        assert f"{commit.hexsha}:README.md" in repo._file_cache

    def test_get_changed_file_states(self, test_repo):
        """测试提取commit修改文件的最终内容"""
        repo = GitRepository(test_repo)
        git_repo = git.Repo(test_repo)

        test_file = test_repo / "bug.py"
        test_file.write_text("def buggy():\n    return 1 / 0\n")
        git_repo.index.add(["bug.py"])
        git_repo.index.commit("Introduce bug")

        test_file.write_text("def buggy():\n    return 1 / 1\n")
        git_repo.index.add(["bug.py"])
        fix_commit = git_repo.index.commit("Fix bug")

        states = repo.get_changed_file_states(fix_commit.hexsha)

        assert states["bug.py"] == "def buggy():\n    return 1 / 1\n"

    def test_has_equivalent_file_state(self, test_repo):
        """测试检测目标ref是否已有相同文件最终状态"""
        repo = GitRepository(test_repo)
        git_repo = git.Repo(test_repo)

        bug_file = test_repo / "bug.py"
        bug_file.write_text("def buggy(x):\n    return 1 / x\n")
        git_repo.index.add(["bug.py"])
        git_repo.index.commit("Introduce bug")

        git_repo.git.checkout("-b", "release/v1.0")
        release_file = test_repo / "notes.txt"
        release_file.write_text("release note\n")
        git_repo.index.add(["notes.txt"])
        git_repo.index.commit("Release-only change")

        git_repo.git.checkout("master")
        bug_file.write_text("def buggy(x):\n    if x == 0:\n        return 0\n    result = 1 / x\n    return result\n")
        git_repo.index.add(["bug.py"])
        fix_commit = git_repo.index.commit("Fix bug")

        git_repo.git.checkout("release/v1.0")
        bug_file.write_text("def buggy(x):\n    if x == 0:\n        return 0\n    return 1 / x\n")
        git_repo.index.add(["bug.py"])
        git_repo.index.commit("Backport part 1")
        bug_file.write_text("def buggy(x):\n    if x == 0:\n        return 0\n    result = 1 / x\n    return result\n")
        git_repo.index.add(["bug.py"])
        git_repo.index.commit("Backport part 2")

        assert repo.has_equivalent_file_state(fix_commit.hexsha, "release/v1.0") is True
