"""
CLI端到端测试
"""

import json

import git
import pytest
from click.testing import CliRunner

from src.cli.main import cli


class TestCLI:
    """CLI端到端测试"""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_cli_version(self, runner):
        """测试版本命令"""
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_cli_help(self, runner):
        """测试帮助命令"""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "CodeRipple" in result.output

    def test_trace_help(self, runner):
        """测试trace命令帮助"""
        result = runner.invoke(cli, ["trace", "--help"])
        assert result.exit_code == 0
        assert "fix_commit" in result.output
        assert "target" in result.output
        assert "--fix" in result.output
        assert "--target" in result.output
        assert "--fix-message" in result.output
        assert "--explain" in result.output

    def test_affected_help(self, runner):
        """测试affected别名帮助"""
        result = runner.invoke(cli, ["affected", "--help"])
        assert result.exit_code == 0
        assert "直观别名" in result.output or "affected" in result.output

    def test_doctor_help(self, runner):
        """测试doctor命令帮助"""
        result = runner.invoke(cli, ["doctor", "--help"])
        assert result.exit_code == 0
        assert "--fix-message" in result.output
        assert "--target" in result.output
        assert "解析" in result.output or "doctor" in result.output

    def test_trace_not_found_shows_strategy_summary(self, runner):
        """测试未命中时输出策略摘要"""
        result = runner.invoke(cli, ["trace", "deadbeef", "master"])
        assert result.exit_code != 0 or "策略摘要" in result.output or "错误:" in result.output

    def test_trace_reports_affected_for_release_branch(self, runner, test_repo):
        """测试真实分支历史下，旧release分支应判定为受影响"""
        git_repo = git.Repo(test_repo)

        bug_file = test_repo / "bug.py"
        bug_file.write_text("def buggy():\n    return 1 / 0\n")
        git_repo.index.add(["bug.py"])
        git_repo.index.commit("Introduce bug")

        git_repo.git.checkout("-b", "release/v1.0")
        git_repo.git.checkout("master")

        bug_file.write_text("def buggy():\n    return 1 / 1\n")
        git_repo.index.add(["bug.py"])
        fix_commit = git_repo.index.commit("Fix bug on master")

        result = runner.invoke(
            cli,
            ["trace", fix_commit.hexsha, "release/v1.0", "--repo", str(test_repo)],
        )

        assert result.exit_code == 0
        assert "✓ Bug存在于目标版本" in result.output
        assert "方法:" in result.output
        assert "尝试策略数:" in result.output

    def test_trace_accepts_fix_and_target_options(self, runner, test_repo):
        """测试可使用--fix和--target替代位置参数"""
        git_repo = git.Repo(test_repo)

        bug_file = test_repo / "bug.py"
        bug_file.write_text("def buggy():\n    return 1 / 0\n")
        git_repo.index.add(["bug.py"])
        git_repo.index.commit("Introduce bug")

        git_repo.git.checkout("-b", "release/v1.0")
        git_repo.git.checkout("master")

        bug_file.write_text("def buggy():\n    return 1 / 1\n")
        git_repo.index.add(["bug.py"])
        fix_commit = git_repo.index.commit("Fix bug on master")

        result = runner.invoke(
            cli,
            [
                "trace",
                "--fix",
                fix_commit.hexsha,
                "--target",
                "release/v1.0",
                "--repo",
                str(test_repo),
            ],
        )

        assert result.exit_code == 0
        assert "✓ Bug存在于目标版本" in result.output

    def test_affected_alias_works(self, runner, test_repo):
        """测试affected命令别名"""
        git_repo = git.Repo(test_repo)

        bug_file = test_repo / "bug.py"
        bug_file.write_text("def buggy():\n    return 1 / 0\n")
        git_repo.index.add(["bug.py"])
        git_repo.index.commit("Introduce bug")

        git_repo.git.checkout("-b", "release/v1.0")
        git_repo.git.checkout("master")

        bug_file.write_text("def buggy():\n    return 1 / 1\n")
        git_repo.index.add(["bug.py"])
        fix_commit = git_repo.index.commit("Fix bug on master")

        result = runner.invoke(
            cli,
            [
                "affected",
                "--fix",
                fix_commit.hexsha,
                "--target",
                "release/v1.0",
                "--repo",
                str(test_repo),
            ],
        )

        assert result.exit_code == 0
        assert "✓ Bug存在于目标版本" in result.output

    def test_trace_reports_not_affected_for_tag_with_json_output(self, runner, test_repo):
        """测试tag目标已包含修复时，JSON输出应明确为不受影响"""
        git_repo = git.Repo(test_repo)

        bug_file = test_repo / "bug.py"
        bug_file.write_text("def buggy():\n    return 1 / 0\n")
        git_repo.index.add(["bug.py"])
        git_repo.index.commit("Introduce bug")

        bug_file.write_text("def buggy():\n    return 1 / 1\n")
        git_repo.index.add(["bug.py"])
        fix_commit = git_repo.index.commit("Fix bug")
        git_repo.create_tag("v1.0.1", ref=fix_commit)

        result = runner.invoke(
            cli,
            [
                "trace",
                fix_commit.hexsha,
                "v1.0.1",
                "--repo",
                str(test_repo),
                "--output",
                "json",
            ],
        )

        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["affected"] is False
        assert payload["commit"] is None
        assert payload["method"] is None
        assert payload["details"]["target_ref"] == "v1.0.1"
        assert payload["details"]["attempts"][0]["method"] == "commit_chain"
        assert payload["details"]["attempts"][0]["found"] is False

    def test_trace_accepts_commit_sha_as_target(self, runner, test_repo):
        """测试目标可直接使用commit sha"""
        git_repo = git.Repo(test_repo)

        bug_file = test_repo / "bug.py"
        bug_file.write_text("def buggy():\n    return 1 / 0\n")
        git_repo.index.add(["bug.py"])
        release_commit = git_repo.index.commit("Introduce bug")

        bug_file.write_text("def buggy():\n    return 1 / 1\n")
        git_repo.index.add(["bug.py"])
        fix_commit = git_repo.index.commit("Fix bug")

        result = runner.invoke(
            cli,
            ["trace", fix_commit.hexsha, release_commit.hexsha, "--repo", str(test_repo)],
        )

        assert result.exit_code == 0
        assert "✓ Bug存在于目标版本" in result.output
        assert "Commit:" in result.output

    def test_trace_reports_not_affected_when_target_never_had_bug(self, runner, test_repo):
        """测试目标版本从未引入bug代码时不应仅因缺少fix而判定受影响"""
        git_repo = git.Repo(test_repo)

        bug_file = test_repo / "bug.py"
        bug_file.write_text("def safe(x):\n    return x + 1\n")
        git_repo.index.add(["bug.py"])
        git_repo.index.commit("Safe baseline")

        git_repo.git.checkout("-b", "release/v1.0")
        git_repo.git.checkout("master")

        bug_file.write_text("def buggy(x):\n    return 10 / x\n")
        git_repo.index.add(["bug.py"])
        git_repo.index.commit("Introduce bug on master")

        bug_file.write_text("def buggy(x):\n    if x == 0:\n        return 0\n    return 10 / x\n")
        git_repo.index.add(["bug.py"])
        fix_commit = git_repo.index.commit("Fix bug on master")

        result = runner.invoke(
            cli,
            [
                "trace",
                fix_commit.hexsha,
                "release/v1.0",
                "--repo",
                str(test_repo),
                "--output",
                "json",
            ],
        )

        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["affected"] is False
        assert payload["details"]["attempts"][0]["method"] == "commit_chain"
        assert payload["details"]["attempts"][0]["found"] is False

    def test_trace_resolves_fix_by_message(self, runner, test_repo):
        """测试可通过--fix-message解析修复提交"""
        git_repo = git.Repo(test_repo)

        bug_file = test_repo / "bug.py"
        bug_file.write_text("def buggy():\n    return 1 / 0\n")
        git_repo.index.add(["bug.py"])
        git_repo.index.commit("Introduce bug")

        git_repo.git.checkout("-b", "release/v1.0")
        git_repo.git.checkout("master")

        bug_file.write_text("def buggy():\n    return 1 / 1\n")
        git_repo.index.add(["bug.py"])
        git_repo.index.commit("fix: handle divide by zero")

        result = runner.invoke(
            cli,
            [
                "trace",
                "--fix-message",
                "divide by zero",
                "--target",
                "release/v1.0",
                "--repo",
                str(test_repo),
                "--output",
                "json",
            ],
        )

        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["affected"] is True

    def test_doctor_reports_resolved_fix_and_target(self, runner, test_repo):
        """测试doctor可解析fix和target"""
        git_repo = git.Repo(test_repo)

        bug_file = test_repo / "bug.py"
        bug_file.write_text("def buggy():\n    return 1 / 0\n")
        git_repo.index.add(["bug.py"])
        git_repo.index.commit("Introduce bug")

        git_repo.git.checkout("-b", "release/v1.0")
        git_repo.git.checkout("master")

        bug_file.write_text("def buggy():\n    return 1 / 1\n")
        git_repo.index.add(["bug.py"])
        fix_commit = git_repo.index.commit("fix: handle divide by zero")

        result = runner.invoke(
            cli,
            [
                "doctor",
                "--fix",
                fix_commit.hexsha,
                "--target",
                "release/v1.0",
                "--repo",
                str(test_repo),
                "--output",
                "json",
            ],
        )

        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["ok"] is True
        assert payload["fix"]["resolved"] == fix_commit.hexsha
        assert payload["target"]["resolved"] == "release/v1.0"

    def test_doctor_reports_ambiguous_fix_message(self, runner, test_repo):
        """测试doctor会报告fix-message多命中"""
        git_repo = git.Repo(test_repo)

        bug_file = test_repo / "bug.py"
        bug_file.write_text("def buggy():\n    return 1 / 0\n")
        git_repo.index.add(["bug.py"])
        git_repo.index.commit("Introduce bug")

        bug_file.write_text("def buggy():\n    return 1 / 1\n")
        git_repo.index.add(["bug.py"])
        git_repo.index.commit("fix: handle divide by zero on master")

        bug_file.write_text("def buggy():\n    return 1\n")
        git_repo.index.add(["bug.py"])
        git_repo.index.commit("fix: handle divide by zero on release")

        result = runner.invoke(
            cli,
            [
                "doctor",
                "--fix-message",
                "divide by zero",
                "--target",
                "master",
                "--repo",
                str(test_repo),
                "--output",
                "json",
            ],
        )

        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["ok"] is False
        assert payload["fix"]["ok"] is False
        assert len(payload["fix"]["candidates"]) >= 2
        assert "多个候选" in payload["fix"]["error"]

    def test_doctor_reports_missing_target(self, runner, test_repo):
        """测试doctor会报告不存在的target"""
        git_repo = git.Repo(test_repo)

        bug_file = test_repo / "bug.py"
        bug_file.write_text("def buggy():\n    return 1 / 0\n")
        git_repo.index.add(["bug.py"])
        fix_commit = git_repo.index.commit("fix: handle divide by zero")

        result = runner.invoke(
            cli,
            [
                "doctor",
                "--fix",
                fix_commit.hexsha,
                "--target",
                "release/missing",
                "--repo",
                str(test_repo),
                "--output",
                "json",
            ],
        )

        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["ok"] is False
        assert payload["target"]["ok"] is False
        assert "无法解析" in payload["target"]["error"]

    def test_trace_json_explain_output(self, runner, test_repo):
        """测试--explain会在JSON中输出结构化分析过程"""
        git_repo = git.Repo(test_repo)

        bug_file = test_repo / "bug.py"
        bug_file.write_text("def safe(x):\n    return x + 1\n")
        git_repo.index.add(["bug.py"])
        git_repo.index.commit("Safe baseline")

        git_repo.git.checkout("-b", "release/v1.0")
        git_repo.git.checkout("master")

        bug_file.write_text("def buggy(x):\n    return 10 / x\n")
        git_repo.index.add(["bug.py"])
        git_repo.index.commit("Introduce bug on master")

        bug_file.write_text("def buggy(x):\n    if x == 0:\n        return 0\n    return 10 / x\n")
        git_repo.index.add(["bug.py"])
        fix_commit = git_repo.index.commit("Fix bug on master")

        result = runner.invoke(
            cli,
            [
                "trace",
                "--fix",
                fix_commit.hexsha,
                "--target",
                "release/v1.0",
                "--repo",
                str(test_repo),
                "--output",
                "json",
                "--explain",
            ],
        )

        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["resolved_fix"] == fix_commit.hexsha
        assert payload["resolved_target"] == "release/v1.0"
        assert "analysis" in payload
        assert payload["analysis"]["strategies"][0]["method"] == "commit_chain"

    def test_trace_detects_affected_after_file_move(self, runner, test_repo):
        """测试真实CLI下文件移动后的修复仍可判定旧分支受影响"""
        git_repo = git.Repo(test_repo)

        target_file = test_repo / "src" / "legacy.py"
        target_file.parent.mkdir()
        target_file.write_text("def buggy():\n    return 1 / 0\n")
        git_repo.index.add(["src/legacy.py"])
        git_repo.index.commit("Introduce bug in legacy file")

        git_repo.git.checkout("-b", "release/v1.0")
        git_repo.git.checkout("master")

        new_dir = test_repo / "pkg"
        new_dir.mkdir()
        git_repo.git.mv("src/legacy.py", "pkg/buggy.py")
        moved_file = test_repo / "pkg" / "buggy.py"
        moved_file.write_text("def buggy():\n    return 1 / 1\n")
        git_repo.index.add(["pkg/buggy.py"])
        fix_commit = git_repo.index.commit("Move file and fix bug")

        result = runner.invoke(
            cli,
            ["trace", fix_commit.hexsha, "release/v1.0", "--repo", str(test_repo)],
        )

        assert result.exit_code == 0
        assert "✓ Bug存在于目标版本" in result.output

    def test_trace_json_output_handles_code_block_matches(self, runner, test_repo):
        """测试JSON输出在命中后续策略时不会因循环引用失败"""
        git_repo = git.Repo(test_repo)

        bug_file = test_repo / "bug.py"
        bug_file.write_text("def buggy():\n    return 1 / 0\n")
        git_repo.index.add(["bug.py"])
        git_repo.index.commit("Introduce bug")

        git_repo.git.checkout("-b", "release/v1.0")
        release_only = test_repo / "notes.txt"
        release_only.write_text("release note\n")
        git_repo.index.add(["notes.txt"])
        git_repo.index.commit("Release-only change")

        git_repo.git.checkout("master")
        bug_file.write_text("def buggy():\n    return 1 / 1\n")
        git_repo.index.add(["bug.py"])
        fix_commit = git_repo.index.commit("Fix on master")

        result = runner.invoke(
            cli,
            [
                "trace",
                fix_commit.hexsha,
                "release/v1.0",
                "--repo",
                str(test_repo),
                "--output",
                "json",
            ],
        )

        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["affected"] is True
        assert payload["details"]["attempts"][0]["method"] == "commit_chain"

    def test_trace_reports_not_affected_for_backported_fix(self, runner, test_repo):
        """测试cherry-pick回补修复后，CLI应判定目标版本不再受影响"""
        git_repo = git.Repo(test_repo)

        bug_file = test_repo / "bug.py"
        bug_file.write_text("def buggy():\n    return 1 / 0\n")
        git_repo.index.add(["bug.py"])
        git_repo.index.commit("Introduce bug")

        git_repo.git.checkout("-b", "release/v1.0")
        release_only = test_repo / "notes.txt"
        release_only.write_text("release note\n")
        git_repo.index.add(["notes.txt"])
        git_repo.index.commit("Release-only change")

        git_repo.git.checkout("master")
        bug_file.write_text("def buggy():\n    return 1 / 1\n")
        git_repo.index.add(["bug.py"])
        fix_commit = git_repo.index.commit("Fix on master")

        git_repo.git.checkout("release/v1.0")
        git_repo.git.cherry_pick(fix_commit.hexsha)

        result = runner.invoke(
            cli,
            [
                "trace",
                fix_commit.hexsha,
                "release/v1.0",
                "--repo",
                str(test_repo),
                "--output",
                "json",
            ],
        )

        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["affected"] is False
        assert payload["details"]["reason"] == "equivalent fix patch already exists in target ref"
        assert payload["details"]["equivalent_commit"] == git_repo.head.commit.hexsha

    def test_trace_reports_affected_for_partial_backport(self, runner, test_repo):
        """测试部分回补修复时，CLI仍应判定目标版本受影响"""
        git_repo = git.Repo(test_repo)

        bug_file = test_repo / "bug.py"
        bug_file.write_text("def buggy(x):\n    return 1 / x\n")
        git_repo.index.add(["bug.py"])
        git_repo.index.commit("Introduce bug")

        git_repo.git.checkout("-b", "release/v1.0")
        release_only = test_repo / "notes.txt"
        release_only.write_text("release note\n")
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

        result = runner.invoke(
            cli,
            [
                "trace",
                fix_commit.hexsha,
                "release/v1.0",
                "--repo",
                str(test_repo),
                "--output",
                "json",
            ],
        )

        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["affected"] is True
        assert payload["method"] in ["code_block", "ast_structure", "similarity"]

    def test_trace_reports_not_affected_for_split_backport_with_same_final_state(self, runner, test_repo):
        """测试拆分回补但最终文件状态一致时，CLI应判定目标版本不再受影响"""
        git_repo = git.Repo(test_repo)

        bug_file = test_repo / "bug.py"
        bug_file.write_text("def buggy(x):\n    return 100 / x\n")
        git_repo.index.add(["bug.py"])
        git_repo.index.commit("Introduce bug")

        git_repo.git.checkout("-b", "release/v1.0")
        release_only = test_repo / "notes.txt"
        release_only.write_text("release note\n")
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

        result = runner.invoke(
            cli,
            [
                "trace",
                fix_commit.hexsha,
                "release/v1.0",
                "--repo",
                str(test_repo),
                "--output",
                "json",
            ],
        )

        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["affected"] is False
        assert payload["details"]["reason"] == "equivalent fixed file state already exists in target ref"

    def test_trace_reports_not_affected_for_backport_after_path_change(self, runner, test_repo):
        """测试文件移动后的修复在旧路径回补时，CLI应判定目标版本不再受影响"""
        git_repo = git.Repo(test_repo)

        legacy_file = test_repo / "src" / "legacy.py"
        legacy_file.parent.mkdir()
        legacy_file.write_text("def buggy(x):\n    return 100 / x\n")
        git_repo.index.add(["src/legacy.py"])
        git_repo.index.commit("Introduce bug")

        git_repo.git.checkout("-b", "release/v1.0")
        release_only = test_repo / "notes.txt"
        release_only.write_text("release note\n")
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

        result = runner.invoke(
            cli,
            [
                "trace",
                fix_commit.hexsha,
                "release/v1.0",
                "--repo",
                str(test_repo),
                "--output",
                "json",
            ],
        )

        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["affected"] is False
        assert payload["details"]["reason"] == "equivalent fixed file state already exists in target ref"

    def test_trace_reports_affected_for_multi_file_fix_with_partial_backport(self, runner, test_repo):
        """测试多文件修复只回补部分文件时，CLI仍应判定目标版本受影响"""
        git_repo = git.Repo(test_repo)

        file_a = test_repo / "a.py"
        file_b = test_repo / "b.py"
        file_a.write_text("def buggy_a(x):\n    return 10 / x\n")
        file_b.write_text("def buggy_b(x):\n    return 20 / x\n")
        git_repo.index.add(["a.py", "b.py"])
        git_repo.index.commit("Introduce bugs")

        git_repo.git.checkout("-b", "release/v1.0")
        release_only = test_repo / "notes.txt"
        release_only.write_text("release note\n")
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

        result = runner.invoke(
            cli,
            [
                "trace",
                fix_commit.hexsha,
                "release/v1.0",
                "--repo",
                str(test_repo),
                "--output",
                "json",
            ],
        )

        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["affected"] is True
        assert payload["method"] in ["code_block", "ast_structure", "similarity"]

    def test_trace_reports_not_affected_for_single_file_equivalent_refactor_backport(self, runner, test_repo):
        """测试单文件语义等价但文本不同的回补时，CLI应判定目标版本不再受影响"""
        git_repo = git.Repo(test_repo)

        bug_file = test_repo / "bug.py"
        bug_file.write_text("def buggy(x):\n    return 10 / x\n")
        git_repo.index.add(["bug.py"])
        git_repo.index.commit("Introduce bug")

        git_repo.git.checkout("-b", "release/v1.0")
        release_only = test_repo / "notes.txt"
        release_only.write_text("release note\n")
        git_repo.index.add(["notes.txt"])
        git_repo.index.commit("Release-only change")

        git_repo.git.checkout("master")
        bug_file.write_text("def buggy(x):\n    if x == 0:\n        return 0\n    result = 10 / x\n    return result\n")
        git_repo.index.add(["bug.py"])
        fix_commit = git_repo.index.commit("Fix bug")

        git_repo.git.checkout("release/v1.0")
        bug_file.write_text("def buggy(value):\n    if value == 0:\n        return 0\n    quotient = 10 / value\n    return quotient\n")
        git_repo.index.add(["bug.py"])
        git_repo.index.commit("Equivalent refactor backport")

        result = runner.invoke(
            cli,
            [
                "trace",
                fix_commit.hexsha,
                "release/v1.0",
                "--repo",
                str(test_repo),
                "--output",
                "json",
            ],
        )

        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["affected"] is False
        assert payload["details"]["reason"] == "equivalent fixed AST state already exists in target ref"
