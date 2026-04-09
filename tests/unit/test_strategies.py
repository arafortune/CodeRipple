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
        """测试目标版本已包含修复时不受影响"""
        git_repo = git.Repo(test_repo)
        
        test_file = test_repo / "test.txt"
        test_file.write_text("commit 1")
        git_repo.index.add(["test.txt"])
        commit1 = git_repo.index.commit("commit 1")
        
        test_file.write_text("commit 2")
        git_repo.index.add(["test.txt"])
        commit2 = git_repo.index.commit("commit 2")
        
        result = strategy.trace(commit1.hexsha, commit2.hexsha)

        assert result.found is False
        assert result.details["reason"] == "fix commit is already contained in target ref"

    def test_trace_not_found_when_fix_not_in_target(self, strategy, test_repo):
        """测试目标版本未包含修复commit时commit链策略只能返回未确定"""
        git_repo = git.Repo(test_repo)

        git_repo.git.checkout("-b", "release/v1.0")
        test_file = test_repo / "test.txt"
        test_file.write_text("buggy")
        git_repo.index.add(["test.txt"])
        git_repo.index.commit("buggy release")

        git_repo.git.checkout("master")
        test_file.write_text("fixed")
        git_repo.index.add(["test.txt"])
        fix_commit = git_repo.index.commit("fix on master")

        result = strategy.trace(fix_commit.hexsha, "release/v1.0")

        assert result.found is False
        assert result.commit is None
        assert result.method is None
        assert result.confidence == 0.0
        assert result.details["reason"] == "fix commit is not reachable from target ref"

    def test_trace_not_found(self, strategy, test_repo):
        """测试目标版本已包含修复时不受影响"""
        git_repo = git.Repo(test_repo)

        test_file = test_repo / "test.txt"
        test_file.write_text("commit 1")
        git_repo.index.add(["test.txt"])
        commit1 = git_repo.index.commit("commit 1")

        test_file.write_text("commit 2")
        git_repo.index.add(["test.txt"])
        commit2 = git_repo.index.commit("commit 2")

        result = strategy.trace(commit1.hexsha, commit2.hexsha)

        assert result.found is False
        assert result.commit is None
        assert result.method is None
        assert result.confidence == 0.0
        assert result.details["reason"] == "fix commit is already contained in target ref"

    def test_trace_reports_not_found_for_diverged_branch(self, strategy, test_repo):
        """测试分叉分支未包含修复时commit链策略返回未确定"""
        git_repo = git.Repo(test_repo)

        git_repo.git.checkout("-b", "feature")
        test_file = test_repo / "feature.txt"
        test_file.write_text("feature bug")
        git_repo.index.add(["feature.txt"])
        git_repo.index.commit("feature bug")

        git_repo.git.checkout("master")
        test_file = test_repo / "main.txt"
        test_file.write_text("fix")
        git_repo.index.add(["main.txt"])
        fix_commit = git_repo.index.commit("main fix")

        result = strategy.trace(fix_commit.hexsha, "feature")

        assert result.found is False
        assert result.details["reason"] == "fix commit is not reachable from target ref"
    
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

    def test_extract_removed_lines(self, strategy):
        """测试提取删除行"""
        diff_text = "@@ -2,3 +2,1 @@\n keep context\n-line 2 removed\n-line 3 removed\n+line 2 new"

        lines = strategy._extract_removed_lines(diff_text)
        assert 3 in lines
        assert 4 in lines

    def test_extract_patch_content(self, strategy):
        """测试提取新增行和上下文行"""
        diff_text = """@@ -1,3 +1,4 @@
 line 1
-line 2
+line 2 modified
 line 3
+line 4 new"""

        added, context = strategy._extract_patch_content(diff_text)

        assert added == ["line 2 modified", "line 4 new"]
        assert context == ["line 1", "line 3"]

    def test_calculate_match_score_with_context(self, strategy):
        """测试上下文加权得分"""
        score = strategy._calculate_match_score(0.8, 0.5, True)
        assert score == pytest.approx(0.71)

    def test_pair_move_candidates(self, strategy):
        """测试删除/新增配对为移动候选"""
        class DiffStub:
            def __init__(self, a_path, b_path, diff):
                self.a_path = a_path
                self.b_path = b_path
                self.diff = diff.encode()

        deleted = DiffStub(
            "src/old.py",
            None,
            "@@ -1,2 +0,0 @@\n-def buggy():\n-    return 1\n",
        )
        added = DiffStub(
            None,
            "app/new.py",
            "@@ -0,0 +1,2 @@\n+def buggy():\n+    return 2\n",
        )

        candidates = strategy._pair_move_candidates([deleted], [added])

        assert len(candidates) == 1
        assert candidates[0].file_path == "app/new.py"
        assert candidates[0].source == "paired_move"

    def test_trace_found_after_file_move(self, strategy, test_repo):
        """测试文件移动后仍可追溯"""
        git_repo = git.Repo(test_repo)

        target_file = test_repo / "src" / "legacy.py"
        target_file.parent.mkdir()
        target_file.write_text("def buggy():\n    return 1 / 0\n")
        git_repo.index.add(["src/legacy.py"])
        git_repo.index.commit("Introduce bug on release")

        git_repo.git.checkout("-b", "release/v1.0")
        git_repo.git.checkout("master")

        new_dir = test_repo / "pkg"
        new_dir.mkdir()
        git_repo.git.mv("src/legacy.py", "pkg/buggy.py")
        moved_file = test_repo / "pkg" / "buggy.py"
        moved_file.write_text("def buggy():\n    return 1 / 1\n")
        git_repo.index.add(["pkg/buggy.py"])
        fix_commit = git_repo.index.commit("Move file and fix bug")

        result = strategy.trace(fix_commit.hexsha, "release/v1.0")

        assert result.found is True
        assert result.details["file"] == "src/legacy.py"

    def test_trace_found_for_deletion_only_fix(self, strategy, test_repo):
        """测试仅通过删除buggy代码修复时，code_block仍可追溯"""
        git_repo = git.Repo(test_repo)

        bug_file = test_repo / "bug.py"
        bug_file.write_text("def buggy():\n    return 1 / 0\n")
        git_repo.index.add(["bug.py"])
        git_repo.index.commit("Baseline")

        bug_file.write_text("def buggy():\n    print('debug')\n    return 1 / 0\n")
        git_repo.index.add(["bug.py"])
        git_repo.index.commit("Introduce debug line bug")

        git_repo.git.checkout("-b", "release/v1.0")
        git_repo.git.checkout("master")

        bug_file.write_text("def buggy():\n    return 1 / 0\n")
        git_repo.index.add(["bug.py"])
        fix_commit = git_repo.index.commit("Remove debug line")

        result = strategy.trace(fix_commit.hexsha, "release/v1.0")

        assert result.found is True
        assert result.method == "code_block"
    
    def test_priority(self, strategy):
        assert strategy.priority == 2
    
    def test_confidence(self, strategy):
        assert strategy.confidence == 0.95
