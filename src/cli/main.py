"""
CLI主入口
"""

import json
from typing import Optional

import click

from src.config import Config
from src.core.tracer import BugTracer
from src.git.repo import GitRepository


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """CodeRipple - Git历史分析工具"""
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
        details = attempt.get("details", {})
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
        analysis["strategies"].append(
            {
                "method": attempt.get("method"),
                "status": status,
                "confidence": attempt.get("confidence", 0.0),
                "details": details,
            }
        )
    return analysis


def _resolve_fix_and_target(
    repo: str,
    fix_commit: Optional[str],
    target: Optional[str],
    fix_option: Optional[str],
    target_option: Optional[str],
    fix_message: Optional[str],
) -> tuple[str, str, Optional[str]]:
    resolved_target = target_option or target
    if not resolved_target:
        raise click.UsageError("需要提供目标版本，使用位置参数 <target> 或 --target")

    fix_inputs = [value for value in (fix_commit, fix_option, fix_message) if value]
    if len(fix_inputs) == 0:
        raise click.UsageError("需要提供修复提交，使用位置参数 <fix_commit>、--fix 或 --fix-message")
    if sum(bool(value) for value in (fix_commit, fix_option, fix_message)) > 1:
        raise click.UsageError("fix_commit、--fix 和 --fix-message 只能提供一种")

    resolved_from_message = None
    if fix_message:
        git_repo = GitRepository(repo)
        matched_commit = git_repo.find_commit_by_message(fix_message)
        if matched_commit is None:
            raise click.UsageError(f"未找到提交信息包含 {fix_message!r} 的commit")
        resolved_fix = matched_commit.hexsha
        resolved_from_message = fix_message
    else:
        resolved_fix = fix_option or fix_commit

    return resolved_fix, resolved_target, resolved_from_message


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
        click.echo("  分析过程:")
        click.echo(f"    - resolved_fix: {resolved_fix}")
        if resolved_from_message:
            click.echo(f"    - fix_message: {resolved_from_message}")
        click.echo(f"    - resolved_target: {resolved_target}")
        for strategy in _build_analysis(result)["strategies"]:
            reason = strategy["details"].get("reason")
            reason_text = f", reason={reason}" if reason else ""
            click.echo(
                f"    - {strategy['method']}: status={strategy['status']}, confidence={strategy['confidence']:.2%}{reason_text}"
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
@click.option("--fix", "fix_option")
@click.option("--fix-message")
@click.option("--target", "target_option")
@click.option("--repo", "-r", default=".")
@click.option("--config", "-c", default="config/coderipple.yaml")
@click.option("--output", "-o", default="table", type=click.Choice(["table", "json"]))
@click.option("--explain", is_flag=True, help="输出结构化分析过程")
def trace(fix_commit, target, fix_option, fix_message, target_option, repo, config, output, explain):
    """追溯bug是否影响目标版本"""
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
@click.option("--fix", "fix_option")
@click.option("--fix-message")
@click.option("--target", "target_option")
@click.option("--repo", "-r", default=".")
@click.option("--config", "-c", default="config/coderipple.yaml")
@click.option("--output", "-o", default="table", type=click.Choice(["table", "json"]))
@click.option("--explain", is_flag=True, help="输出结构化分析过程")
def affected(fix_commit, target, fix_option, fix_message, target_option, repo, config, output, explain):
    """`trace` 的直观别名，直接表达目标版本是否受影响"""
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


if __name__ == "__main__":
    cli()
