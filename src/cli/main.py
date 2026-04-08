"""
CLI主入口
"""

import json
from typing import Optional

import click
import git

from src.config import Config
from src.core.tracer import BugTracer
from src.git.repo import GitRepository


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """CodeRipple - Git历史分析工具。分析目标版本是否仍受某个修复提交对应的Bug影响。"""
    return None


def _build_analysis(result) -> dict:
    attempts = result.details.get("attempts", [])
    analysis = {
        "summary": {
            "affected": result.found,
            "method": result.method,
            "confidence": result.confidence,
        },
        "strategies": [],
    }
    for attempt in attempts:
        analysis["strategies"].append(_build_strategy_analysis(attempt))
    return analysis


def _build_strategy_analysis(attempt: dict) -> dict:
    details = attempt.get("details", {})
    method = attempt.get("method")
    confidence = attempt.get("confidence", 0.0)

    evidence = {
        "reason": details.get("reason"),
        "file": details.get("file"),
        "lines": details.get("lines"),
        "matched_lines": details.get("matched_lines"),
        "match_score": details.get("match_score"),
        "added_score": details.get("added_score"),
        "similarity": details.get("similarity"),
        "matched_nodes": details.get("matched_nodes"),
        "candidate_source": details.get("candidate_source"),
        "contains_fix_commit": details.get("contains_fix_commit", False),
        "equivalent_commit": details.get("equivalent_commit"),
        "equivalent_state": details.get("equivalent_state", False),
        "equivalent_ast_state": details.get("equivalent_ast_state", False),
    }
    evidence = {key: value for key, value in evidence.items() if value not in (None, False, [], {})}

    status = "affected" if attempt.get("found") else "unknown"
    if any(
        details.get(flag)
        for flag in (
            "contains_fix_commit",
            "equivalent_commit",
            "equivalent_state",
            "equivalent_ast_state",
        )
    ):
        status = "not_affected"

    summary = _summarize_strategy(method, status, evidence)
    return {
        "method": method,
        "status": status,
        "confidence": confidence,
        "summary": summary,
        "evidence": evidence,
    }


def _summarize_strategy(method: Optional[str], status: str, evidence: dict) -> str:
    if method == "commit_chain":
        if status == "not_affected":
            return evidence.get("reason", "target already contains an equivalent fix")
        if status == "unknown":
            return evidence.get("reason", "target does not contain the fix commit or an equivalent fix")
    if status == "affected":
        if evidence.get("file"):
            return f"matched bug evidence in {evidence['file']}"
        return "matched bug evidence in target history"
    return evidence.get("reason", "no decisive evidence found")


def _resolve_fix_and_target(
    repo: str,
    fix_commit: Optional[str],
    target: Optional[str],
    fix_option: Optional[str],
    target_option: Optional[str],
    fix_message: Optional[str],
) -> tuple[str, str, Optional[str]]:
    git_repo = GitRepository(repo)
    resolved_target = target_option or target
    if not resolved_target:
        raise click.UsageError("需要提供目标版本，使用位置参数 <target> 或 --target")
    if not git_repo.ref_exists(resolved_target):
        raise click.UsageError(f"目标版本 {resolved_target!r} 不存在或无法解析")

    fix_inputs = [value for value in (fix_commit, fix_option, fix_message) if value]
    if len(fix_inputs) == 0:
        raise click.UsageError("需要提供修复提交，使用位置参数 <fix_commit>、--fix 或 --fix-message")
    if sum(bool(value) for value in (fix_commit, fix_option, fix_message)) > 1:
        raise click.UsageError("fix_commit、--fix 和 --fix-message 只能提供一种")

    resolved_from_message = None
    if fix_message:
        matched_commits = git_repo.find_commits_by_message(fix_message)
        if not matched_commits:
            raise click.UsageError(f"未找到提交信息包含 {fix_message!r} 的commit")
        if len(matched_commits) > 1:
            candidates = ", ".join(commit.hexsha[:8] for commit in matched_commits[:3])
            raise click.UsageError(
                f"--fix-message {fix_message!r} 命中多个commit，请改用 --fix 指定。候选: {candidates}"
            )
        resolved_fix = matched_commits[0].hexsha
        resolved_from_message = fix_message
    else:
        resolved_fix = fix_option or fix_commit
        try:
            resolved_fix = git_repo.get_commit(resolved_fix).hexsha
        except Exception:
            raise click.UsageError(f"修复提交 {resolved_fix!r} 不存在或无法解析") from None

    return resolved_fix, resolved_target, resolved_from_message


def _doctor_command(
    fix_commit: Optional[str],
    target: Optional[str],
    fix_option: Optional[str],
    target_option: Optional[str],
    fix_message: Optional[str],
    repo: str,
    output: str,
) -> None:
    git_repo = GitRepository(repo)
    repo_path = str(git_repo.repo_path)
    diagnostics: dict = {
        "repo": {"path": repo_path, "ok": True},
        "fix": {"ok": False},
        "target": {"ok": False},
    }

    raw_target = target_option or target
    if raw_target:
        diagnostics["target"]["input"] = raw_target
        if git_repo.ref_exists(raw_target):
            resolved_target = git_repo.get_commit(raw_target).hexsha
            diagnostics["target"].update(
                {"ok": True, "resolved": raw_target, "commit": resolved_target}
            )
        else:
            diagnostics["target"]["error"] = "目标版本不存在或无法解析"
    else:
        diagnostics["target"]["error"] = "缺少目标版本"

    raw_fix = fix_option or fix_commit
    if fix_message:
        diagnostics["fix"]["input"] = fix_message
        diagnostics["fix"]["mode"] = "message"
        matches = git_repo.find_commits_by_message(fix_message)
        diagnostics["fix"]["candidates"] = [
            {"commit": commit.hexsha, "summary": commit.summary} for commit in matches[:5]
        ]
        if len(matches) == 1:
            diagnostics["fix"].update({"ok": True, "resolved": matches[0].hexsha})
        elif len(matches) > 1:
            diagnostics["fix"]["error"] = "提交信息命中多个候选，请改用 --fix"
        else:
            diagnostics["fix"]["error"] = "未找到匹配的修复提交"
    elif raw_fix:
        diagnostics["fix"]["input"] = raw_fix
        diagnostics["fix"]["mode"] = "commit"
        try:
            diagnostics["fix"].update(
                {"ok": True, "resolved": git_repo.get_commit(raw_fix).hexsha}
            )
        except Exception:
            diagnostics["fix"]["error"] = "修复提交不存在或无法解析"
    else:
        diagnostics["fix"]["error"] = "缺少修复提交"

    diagnostics["ok"] = all(section["ok"] for key, section in diagnostics.items() if key in {"repo", "fix", "target"})

    if output == "json":
        click.echo(json.dumps(diagnostics, indent=2, ensure_ascii=False))
        return

    click.echo(f"Repository: {repo_path}")
    click.echo(f"  status: {'ok' if diagnostics['repo']['ok'] else 'error'}")
    click.echo("Fix:")
    click.echo(f"  status: {'ok' if diagnostics['fix']['ok'] else 'error'}")
    if "mode" in diagnostics["fix"]:
        click.echo(f"  mode: {diagnostics['fix']['mode']}")
    if "input" in diagnostics["fix"]:
        click.echo(f"  input: {diagnostics['fix']['input']}")
    if diagnostics["fix"]["ok"]:
        click.echo(f"  resolved: {diagnostics['fix']['resolved']}")
    else:
        click.echo(f"  error: {diagnostics['fix']['error']}")
    candidates = diagnostics["fix"].get("candidates", [])
    if candidates:
        click.echo("  candidates:")
        for candidate in candidates:
            click.echo(f"    - {candidate['commit'][:8]} {candidate['summary']}")

    click.echo("Target:")
    click.echo(f"  status: {'ok' if diagnostics['target']['ok'] else 'error'}")
    if "input" in diagnostics["target"]:
        click.echo(f"  input: {diagnostics['target']['input']}")
    if diagnostics["target"]["ok"]:
        click.echo(f"  resolved: {diagnostics['target']['resolved']}")
        click.echo(f"  commit: {diagnostics['target']['commit']}")
    else:
        click.echo(f"  error: {diagnostics['target']['error']}")

    click.echo(f"Overall: {'ok' if diagnostics['ok'] else 'error'}")


def _render_table(result, explain: bool, resolved_fix: str, resolved_target: str, resolved_from_message: Optional[str]) -> None:
    if result.found:
        click.echo("✓ Bug存在于目标版本")
        click.echo(f"  Commit: {result.commit}")
        click.echo(f"  方法: {result.method}")
        click.echo(f"  置信度: {result.confidence:.2%}")
        attempts = result.details.get("attempts", [])
        if attempts:
            click.echo(f"  尝试策略数: {len(attempts)}")
    else:
        click.echo("✗ Bug不存在于目标版本")
        attempts = result.details.get("attempts", [])
        if attempts:
            click.echo("  策略摘要:")
            for attempt in attempts:
                click.echo(
                    f"    - {attempt['method']}: affected={attempt['found']}, confidence={attempt['confidence']:.2%}"
                )

    if explain:
        analysis = _build_analysis(result)
        click.echo("  分析过程:")
        click.echo(f"    - resolved_fix: {resolved_fix}")
        if resolved_from_message:
            click.echo(f"    - fix_message: {resolved_from_message}")
        click.echo(f"    - resolved_target: {resolved_target}")
        for strategy in analysis["strategies"]:
            click.echo(
                f"    - {strategy['method']}: status={strategy['status']}, confidence={strategy['confidence']:.2%}, summary={strategy['summary']}"
            )


def _trace_command(
    fix_commit: Optional[str],
    target: Optional[str],
    fix_option: Optional[str],
    target_option: Optional[str],
    fix_message: Optional[str],
    repo: str,
    config: str,
    output: str,
    explain: bool,
) -> None:
    resolved_fix, resolved_target, resolved_from_message = _resolve_fix_and_target(
        repo, fix_commit, target, fix_option, target_option, fix_message
    )
    config_obj = Config.from_file(config)
    tracer = BugTracer(config_obj, repo)
    result = tracer.trace(resolved_fix, resolved_target)
    if output == "json":
        payload = {
            "affected": result.found,
            "commit": result.commit,
            "method": result.method,
            "confidence": result.confidence,
            "details": result.details,
        }
        if explain:
            payload["analysis"] = _build_analysis(result)
            payload["resolved_fix"] = resolved_fix
            payload["resolved_target"] = resolved_target
            if resolved_from_message:
                payload["fix_message"] = resolved_from_message
        click.echo(json.dumps(payload, indent=2, ensure_ascii=False))
        return

    _render_table(result, explain, resolved_fix, resolved_target, resolved_from_message)


@cli.command(name="trace")
@click.argument("fix_commit", metavar="fix_commit", required=False)
@click.argument("target", metavar="target", required=False)
@click.option("--fix", "fix_option", help="显式指定修复commit，可替代位置参数 <fix_commit>")
@click.option("--fix-message", help="按提交信息搜索修复commit，例如 --fix-message 'divide by zero'")
@click.option("--target", "target_option", help="目标分支、tag或commit，可替代位置参数 <target>")
@click.option("--repo", "-r", default=".", help="目标Git仓库路径，默认当前目录")
@click.option("--config", "-c", default="config/coderipple.yaml", help="配置文件路径")
@click.option("--output", "-o", default="table", type=click.Choice(["table", "json"]), help="输出格式")
@click.option("--explain", is_flag=True, help="输出结构化分析过程")
def trace(fix_commit, target, fix_option, fix_message, target_option, repo, config, output, explain):
    """追溯目标版本是否仍受某个修复提交对应的Bug影响。

    支持旧用法：
      coderipple trace <fix_commit> <target>

    也支持显式参数：
      coderipple trace --fix <fix_commit> --target <target>
      coderipple trace --fix-message "<message>" --target <target>
    """
    try:
        _trace_command(
            fix_commit,
            target,
            fix_option,
            target_option,
            fix_message,
            repo,
            config,
            output,
            explain,
        )
    except click.ClickException:
        raise
    except Exception as e:
        click.echo(f"错误: {e}", err=True)
        raise click.Abort()


@cli.command(name="affected")
@click.argument("fix_commit", metavar="fix_commit", required=False)
@click.argument("target", metavar="target", required=False)
@click.option("--fix", "fix_option", help="显式指定修复commit，可替代位置参数 <fix_commit>")
@click.option("--fix-message", help="按提交信息搜索修复commit，例如 --fix-message 'divide by zero'")
@click.option("--target", "target_option", help="目标分支、tag或commit，可替代位置参数 <target>")
@click.option("--repo", "-r", default=".", help="目标Git仓库路径，默认当前目录")
@click.option("--config", "-c", default="config/coderipple.yaml", help="配置文件路径")
@click.option("--output", "-o", default="table", type=click.Choice(["table", "json"]), help="输出格式")
@click.option("--explain", is_flag=True, help="输出结构化分析过程")
def affected(fix_commit, target, fix_option, fix_message, target_option, repo, config, output, explain):
    """`trace` 的直观别名，直接表达目标版本是否受影响。"""
    try:
        _trace_command(
            fix_commit,
            target,
            fix_option,
            target_option,
            fix_message,
            repo,
            config,
            output,
            explain,
        )
    except click.ClickException:
        raise
    except Exception as e:
        click.echo(f"错误: {e}", err=True)
        raise click.Abort()


@cli.command(name="doctor")
@click.argument("fix_commit", metavar="fix_commit", required=False)
@click.argument("target", metavar="target", required=False)
@click.option("--fix", "fix_option", help="显式指定修复commit，可替代位置参数 <fix_commit>")
@click.option("--fix-message", help="按提交信息搜索修复commit，并检测是否存在多候选")
@click.option("--target", "target_option", help="目标分支、tag或commit，可替代位置参数 <target>")
@click.option("--repo", "-r", default=".", help="目标Git仓库路径，默认当前目录")
@click.option("--output", "-o", default="table", type=click.Choice(["table", "json"]), help="输出格式")
def doctor(fix_commit, target, fix_option, fix_message, target_option, repo, output):
    """检查仓库、fix 和 target 是否都能被正确解析，提前暴露歧义和输入错误。"""
    try:
        _doctor_command(
            fix_commit,
            target,
            fix_option,
            target_option,
            fix_message,
            repo,
            output,
        )
    except click.ClickException:
        raise
    except git.exc.InvalidGitRepositoryError:
        raise click.ClickException(f"{repo!r} 不是有效的Git仓库")
    except Exception as e:
        click.echo(f"错误: {e}", err=True)
        raise click.Abort()


if __name__ == "__main__":
    cli()
