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
        assert result.details["target_ref"] == "release/v1.0"
        assert result.details["fix_commit"] == fix_commit.hexsha
        assert len(result.details["attempts"]) >= 1
    
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

        assert result.found is False
        assert result.details["attempts"][0]["method"] == "commit_chain"
        assert result.details["attempts"][0]["found"] is False

    def test_not_found_contains_attempts(self, tracer, test_repo):
        """测试未包含修复时返回策略摘要"""
        git_repo = git.Repo(test_repo)

        git_repo.git.checkout("-b", "feature")
        feature_file = test_repo / "feature.py"
        feature_file.write_text("def buggy():\n    return 1 / 0\n")
        git_repo.index.add(["feature.py"])
        git_repo.index.commit("Buggy feature state")

        git_repo.git.checkout("master")
        feature_file = test_repo / "feature.py"
        feature_file.write_text("def buggy():\n    return 1 / 1\n")
        git_repo.index.add(["feature.py"])
        fix_commit = git_repo.index.commit("Fix on master")

        result = tracer.trace(fix_commit.hexsha, "feature")

        assert result.found is True
        assert result.details["target_ref"] == "feature"
        assert result.details["fix_commit"] == fix_commit.hexsha
        assert len(result.details["attempts"]) >= 1

    def test_fix_missing_from_target_reports_affected(self, tracer, test_repo):
        """测试目标版本未包含修复commit时判定为受影响"""
        git_repo = git.Repo(test_repo)

        bug_file = test_repo / "bug.py"
        bug_file.write_text("def buggy():\n    return 1 / 0\n")
        git_repo.index.add(["bug.py"])
        git_repo.index.commit("Introduce bug")

        git_repo.git.checkout("-b", "release/test")
        git_repo.git.checkout("master")

        bug_file.write_text("def buggy():\n    return 1 / 1\n")
        git_repo.index.add(["bug.py"])
        fix_commit = git_repo.index.commit("Fix on master")

        result = tracer.trace(fix_commit.hexsha, "release/test")

        assert result.found is True
        assert result.method == "commit_chain"

    def test_backported_fix_is_not_reported_as_affected(self, tracer, test_repo):
        """测试目标版本通过cherry-pick回补等价修复时不应判定为受影响"""
        git_repo = git.Repo(test_repo)

        bug_file = test_repo / "bug.py"
        bug_file.write_text("def buggy():\n    return 1 / 0\n")
        git_repo.index.add(["bug.py"])
        git_repo.index.commit("Introduce bug")

        git_repo.git.checkout("-b", "release/v1.0")
        release_note = test_repo / "notes.txt"
        release_note.write_text("release note\n")
        git_repo.index.add(["notes.txt"])
        git_repo.index.commit("Release-only change")

        git_repo.git.checkout("master")
        bug_file.write_text("def buggy():\n    return 1 / 1\n")
        git_repo.index.add(["bug.py"])
        fix_commit = git_repo.index.commit("Fix on master")

        git_repo.git.checkout("release/v1.0")
        git_repo.git.cherry_pick(fix_commit.hexsha)
        backport_commit = git_repo.head.commit.hexsha

        result = tracer.trace(fix_commit.hexsha, "release/v1.0")

        assert result.found is False
        assert result.details["reason"] == "equivalent fix patch already exists in target ref"
        assert result.details["equivalent_commit"] == backport_commit
        assert result.details["attempts"][0]["method"] == "commit_chain"

    def test_partial_backport_still_reports_affected(self, tracer, test_repo):
        """测试部分修复不应被当作等价回补"""
        git_repo = git.Repo(test_repo)

        bug_file = test_repo / "bug.py"
        bug_file.write_text("def buggy(x):\n    return 1 / x\n")
        git_repo.index.add(["bug.py"])
        git_repo.index.commit("Introduce bug")

        git_repo.git.checkout("-b", "release/v1.0")
        release_note = test_repo / "notes.txt"
        release_note.write_text("release note\n")
        git_repo.index.add(["notes.txt"])
        git_repo.index.commit("Release-only change")

        git_repo.git.checkout("master")
        bug_file.write_text("def buggy(x):\n    if x == 0:\n        return 0\n    return 1 / x\n")
        git_repo.index.add(["bug.py"])
        fix_commit = git_repo.index.commit("Fix on master")

        git_repo.git.checkout("release/v1.0")
        bug_file.write_text("def buggy(x):\n    if x < 0:\n        return 0\n    return 1 / x\n")
        git_repo.index.add(["bug.py"])
        git_repo.index.commit("Partial backport")

        result = tracer.trace(fix_commit.hexsha, "release/v1.0")

        assert result.found is True
        assert result.method == "commit_chain"
        assert result.details["reason"] == "fix commit is not reachable from target ref"

    def test_split_backport_with_same_final_state_is_not_reported_as_affected(self, tracer, test_repo):
        """测试拆分成多个commit回补但最终状态一致时不应判定为受影响"""
        git_repo = git.Repo(test_repo)

        bug_file = test_repo / "bug.py"
        bug_file.write_text("def buggy(x):\n    return 100 / x\n")
        git_repo.index.add(["bug.py"])
        git_repo.index.commit("Introduce bug")

        git_repo.git.checkout("-b", "release/v1.0")
        release_note = test_repo / "notes.txt"
        release_note.write_text("release note\n")
        git_repo.index.add(["notes.txt"])
        git_repo.index.commit("Release-only change")

        git_repo.git.checkout("master")
        bug_file.write_text("def buggy(x):\n    if x == 0:\n        return 0\n    result = 100 / x\n    return result\n")
        git_repo.index.add(["bug.py"])
        fix_commit = git_repo.index.commit("Fix on master")

        git_repo.git.checkout("release/v1.0")
        bug_file.write_text("def buggy(x):\n    if x == 0:\n        return 0\n    return 100 / x\n")
        git_repo.index.add(["bug.py"])
        git_repo.index.commit("Backport part 1")
        bug_file.write_text("def buggy(x):\n    if x == 0:\n        return 0\n    result = 100 / x\n    return result\n")
        git_repo.index.add(["bug.py"])
        git_repo.index.commit("Backport part 2")

        result = tracer.trace(fix_commit.hexsha, "release/v1.0")

        assert result.found is False
        assert result.details["reason"] == "equivalent fixed file state already exists in target ref"
        assert result.details["attempts"][0]["method"] == "commit_chain"

    def test_backport_after_path_change_is_not_reported_as_affected(self, tracer, test_repo):
        """测试主线移动文件后修复，目标版本在旧路径回补时也不应判定为受影响"""
        git_repo = git.Repo(test_repo)

        legacy_file = test_repo / "src" / "legacy.py"
        legacy_file.parent.mkdir()
        legacy_file.write_text("def buggy(x):\n    return 100 / x\n")
        git_repo.index.add(["src/legacy.py"])
        git_repo.index.commit("Introduce bug")

        git_repo.git.checkout("-b", "release/v1.0")
        release_note = test_repo / "notes.txt"
        release_note.write_text("release note\n")
        git_repo.index.add(["notes.txt"])
        git_repo.index.commit("Release-only change")

        git_repo.git.checkout("master")
        new_dir = test_repo / "pkg"
        new_dir.mkdir()
        git_repo.git.mv("src/legacy.py", "pkg/legacy.py")
        moved_file = test_repo / "pkg" / "legacy.py"
        moved_file.write_text("def buggy(x):\n    if x == 0:\n        return 0\n    result = 100 / x\n    return result\n")
        git_repo.index.add(["pkg/legacy.py"])
        fix_commit = git_repo.index.commit("Move file and fix bug")

        git_repo.git.checkout("release/v1.0")
        legacy_file = test_repo / "src" / "legacy.py"
        legacy_file.write_text("def buggy(x):\n    if x == 0:\n        return 0\n    result = 100 / x\n    return result\n")
        git_repo.index.add(["src/legacy.py"])
        git_repo.index.commit("Backport fix without moving file")

        result = tracer.trace(fix_commit.hexsha, "release/v1.0")

        assert result.found is False
        assert result.details["reason"] == "equivalent fixed file state already exists in target ref"

    def test_multi_file_fix_with_partial_backport_still_reports_affected(self, tracer, test_repo):
        """测试多文件修复只回补部分文件时仍应判定为受影响"""
        git_repo = git.Repo(test_repo)

        file_a = test_repo / "a.py"
        file_b = test_repo / "b.py"
        file_a.write_text("def buggy_a(x):\n    return 10 / x\n")
        file_b.write_text("def buggy_b(x):\n    return 20 / x\n")
        git_repo.index.add(["a.py", "b.py"])
        git_repo.index.commit("Introduce bugs")

        git_repo.git.checkout("-b", "release/v1.0")
        release_note = test_repo / "notes.txt"
        release_note.write_text("release note\n")
        git_repo.index.add(["notes.txt"])
        git_repo.index.commit("Release-only change")

        git_repo.git.checkout("master")
        file_a.write_text("def buggy_a(x):\n    if x == 0:\n        return 0\n    return 10 / x\n")
        file_b.write_text("def buggy_b(x):\n    if x == 0:\n        return 0\n    return 20 / x\n")
        git_repo.index.add(["a.py", "b.py"])
        fix_commit = git_repo.index.commit("Fix both files")

        git_repo.git.checkout("release/v1.0")
        file_a.write_text("def buggy_a(x):\n    if x == 0:\n        return 0\n    return 10 / x\n")
        git_repo.index.add(["a.py"])
        git_repo.index.commit("Backport only a.py")

        result = tracer.trace(fix_commit.hexsha, "release/v1.0")

        assert result.found is True
        assert result.method == "commit_chain"
        assert result.details["reason"] == "fix commit is not reachable from target ref"
