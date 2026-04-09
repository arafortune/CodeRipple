"""
CLI主入口
"""

import json
from pathlib import Path
from typing import Optional

import click
import git

from src.config import Config
from src.core.tracer import BugTracer
from src.git.repo import GitRepository


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """CodeRipple - Git历史分析工具。

    提供三类核心能力：
    1. `trace` / `affected`：分析目标版本是否仍受Bug影响
    2. `find-fix`：先搜索候选修复提交
    3. `doctor`：先诊断 fix、target、config 是否可解析
    """
    return None


def _build_analysis(result) -> dict:
    status = _infer_result_status(result)
    attempts = result.details.get("attempts", [])
    analysis = {
        "summary": {
            "status": status,
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


def _infer_result_status(result) -> str:
    if result.found:
        return "affected"

    attempts = result.details.get("attempts", [])
    for attempt in attempts:
        details = attempt.get("details", {})
        if any(
            details.get(flag)
            for flag in (
                "contains_fix_commit",
                "equivalent_commit",
                "equivalent_state",
                "equivalent_ast_state",
            )
        ):
            return "not_affected"
    return "unknown"


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
    fix_index: int,
    list_fix_candidates: bool,
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
        matched_commits = git_repo.rank_commits_for_fix_message(
            git_repo.find_commits_by_message(fix_message),
            fix_message,
            resolved_target,
        )
        if not matched_commits:
            raise click.UsageError(f"未找到提交信息包含 {fix_message!r} 的commit")
        if list_fix_candidates:
            raise click.ClickException(_format_fix_candidates_message(fix_message, matched_commits))
        if fix_index != 0 and (fix_index < 1 or fix_index > len(matched_commits)):
            raise click.UsageError(
                f"--fix-index 必须落在 1 到 {len(matched_commits)} 之间，当前为 {fix_index}"
            )
        if len(matched_commits) > 1 and fix_index == 0:
            candidates = ", ".join(
                f"{idx}:{commit.hexsha[:8]}"
                for idx, commit in enumerate(matched_commits[:3], start=1)
            )
            raise click.UsageError(
                f"--fix-message {fix_message!r} 命中多个commit，请用 --fix-index 选择。候选: {candidates}"
            )
        selected_index = 1 if fix_index == 0 else fix_index
        resolved_fix = matched_commits[selected_index - 1].hexsha
        resolved_from_message = fix_message
    else:
        resolved_fix = fix_option or fix_commit
        try:
            resolved_fix = git_repo.get_commit(resolved_fix).hexsha
        except Exception:
            raise click.UsageError(f"修复提交 {resolved_fix!r} 不存在或无法解析") from None

    return resolved_fix, resolved_target, resolved_from_message


def _format_fix_candidates_message(fix_message: str, matched_commits: list[git.Commit]) -> str:
    lines = [f"fix-message {fix_message!r} 的候选提交:"]
    for idx, commit in enumerate(matched_commits[:10], start=1):
        lines.append(f"{idx}. {commit.hexsha[:8]} {commit.summary}")
    if len(matched_commits) > 10:
        lines.append(f"... 其余 {len(matched_commits) - 10} 个候选未显示")
    lines.append("使用 --fix-index <n> 选择候选，或改用 --fix 直接指定 commit。")
    return "\n".join(lines)


def _build_fix_candidates(
    git_repo: GitRepository,
    query: str,
    target_ref: Optional[str],
    limit: int,
    path: Optional[str] = None,
    since_days: Optional[int] = None,
) -> list[dict]:
    ranked_commits = git_repo.filter_commits(
        git_repo.rank_commits_for_fix_message(
            git_repo.find_commits_by_message(query, max_count=max(limit * 5, 50)),
            query,
            target_ref,
        ),
        path=path,
        since_days=since_days,
    )
    candidates = []
    for index, commit in enumerate(ranked_commits[:limit], start=1):
        reachable = git_repo.is_ancestor(commit.hexsha, target_ref) if target_ref else False
        candidates.append(
            {
                "index": index,
                "commit": commit.hexsha,
                "summary": commit.summary,
                "path_filter": path,
                "since_days": since_days,
                "reachable_from_target": reachable,
                "reason": "message match ranked by summary match, recency, and target reachability",
            }
        )
    return candidates


def _find_fix_command(
    message: str,
    target: Optional[str],
    repo: str,
    limit: int,
    output: str,
    path: Optional[str],
    since_days: Optional[int],
) -> None:
    git_repo = GitRepository(repo)
    if target and not git_repo.ref_exists(target):
        raise click.UsageError(f"目标版本 {target!r} 不存在或无法解析")

    candidates = _build_fix_candidates(git_repo, message, target, limit, path=path, since_days=since_days)
    payload = {
        "query": message,
        "target": target,
        "path": path,
        "since_days": since_days,
        "repo": str(git_repo.repo_path),
        "candidates": candidates,
    }

    if output == "json":
        click.echo(json.dumps(payload, indent=2, ensure_ascii=False))
        return

    click.echo(f"Query: {message}")
    if target:
        click.echo(f"Target: {target}")
    if path:
        click.echo(f"Path: {path}")
    if since_days is not None:
        click.echo(f"Since days: {since_days}")
    click.echo(f"Repository: {git_repo.repo_path}")
    if not candidates:
        click.echo("No candidates found.")
        return
    for candidate in candidates:
        reachability = "reachable" if candidate["reachable_from_target"] else "not-reachable"
        click.echo(
            f"{candidate['index']}. {candidate['commit'][:8]} {candidate['summary']} [{reachability}]"
        )


def _resolve_targets(
    repo: str,
    target: Optional[str],
    target_options: tuple[str, ...],
    targets_file: Optional[str],
) -> list[str]:
    git_repo = GitRepository(repo)
    resolved_targets: list[str] = []

    if target:
        resolved_targets.append(target)

    resolved_targets.extend([value for value in target_options if value])

    if targets_file:
        file_path = Path(targets_file)
        for line in file_path.read_text(encoding="utf-8").splitlines():
            value = line.strip()
            if value and not value.startswith("#"):
                resolved_targets.append(value)

    if not resolved_targets:
        raise click.UsageError("需要提供目标版本，使用位置参数 <target>、--target 或 --targets-file")

    normalized_targets: list[str] = []
    seen_targets = set()
    for candidate in resolved_targets:
        if candidate in seen_targets:
            continue
        if not git_repo.ref_exists(candidate):
            raise click.UsageError(f"目标版本 {candidate!r} 不存在或无法解析")
        seen_targets.add(candidate)
        normalized_targets.append(candidate)
    return normalized_targets


def _doctor_command(
    fix_commit: Optional[str],
    target: Optional[str],
    fix_option: Optional[str],
    target_options: tuple[str, ...],
    targets_file: Optional[str],
    fix_message: Optional[str],
    repo: str,
    config: str,
    output: str,
    fix_index: int,
) -> None:
    git_repo = GitRepository(repo)
    repo_path = str(git_repo.repo_path)
    config_diagnostics = {"path": config, "ok": True}
    try:
        Config.from_file(config)
    except Exception as exc:
        config_diagnostics = {"path": config, "ok": False, "error": str(exc)}

    diagnostics: dict = {
        "repo": {"path": repo_path, "ok": True},
        "config": config_diagnostics,
        "fix": {"ok": False},
        "targets": [],
    }

    try:
        resolved_targets = _resolve_targets(repo, target, target_options, targets_file)
        for raw_target in resolved_targets:
            diagnostics["targets"].append(
                {
                    "input": raw_target,
                    "ok": True,
                    "resolved": raw_target,
                    "commit": git_repo.get_commit(raw_target).hexsha,
                }
            )
    except click.UsageError as exc:
        diagnostics["targets"].append({"ok": False, "error": exc.message})
        resolved_targets = []

    raw_fix = fix_option or fix_commit
    if fix_message:
        diagnostics["fix"]["input"] = fix_message
        diagnostics["fix"]["mode"] = "message"
        matches = git_repo.rank_commits_for_fix_message(
            git_repo.find_commits_by_message(fix_message),
            fix_message,
            resolved_targets[0] if resolved_targets else None,
        )
        diagnostics["fix"]["candidates"] = [
            {"commit": commit.hexsha, "summary": commit.summary} for commit in matches[:5]
        ]
        if len(matches) == 1:
            diagnostics["fix"].update({"ok": True, "resolved": matches[0].hexsha})
        elif len(matches) > 1:
            if 1 <= fix_index <= len(matches):
                diagnostics["fix"].update({"ok": True, "resolved": matches[fix_index - 1].hexsha})
            else:
                diagnostics["fix"]["error"] = "提交信息命中多个候选，请使用 --fix-index 选择"
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

    diagnostics["ok"] = (
        diagnostics["repo"]["ok"]
        and diagnostics["config"]["ok"]
        and diagnostics["fix"]["ok"]
        and bool(diagnostics["targets"])
        and all(target_item["ok"] for target_item in diagnostics["targets"])
    )

    if output == "json":
        click.echo(json.dumps(diagnostics, indent=2, ensure_ascii=False))
        return

    click.echo(f"Repository: {repo_path}")
    click.echo(f"  status: {'ok' if diagnostics['repo']['ok'] else 'error'}")
    click.echo("Config:")
    click.echo(f"  status: {'ok' if diagnostics['config']['ok'] else 'error'}")
    click.echo(f"  path: {diagnostics['config']['path']}")
    if not diagnostics["config"]["ok"]:
        click.echo(f"  error: {diagnostics['config']['error']}")
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

    click.echo("Targets:")
    for target_item in diagnostics["targets"]:
        click.echo(f"  - status: {'ok' if target_item['ok'] else 'error'}")
        if "input" in target_item:
            click.echo(f"    input: {target_item['input']}")
        if target_item["ok"]:
            click.echo(f"    resolved: {target_item['resolved']}")
            click.echo(f"    commit: {target_item['commit']}")
        else:
            click.echo(f"    error: {target_item['error']}")

    click.echo(f"Overall: {'ok' if diagnostics['ok'] else 'error'}")


def _render_table(result, explain: bool, resolved_fix: str, resolved_target: str, resolved_from_message: Optional[str]) -> None:
    status = _infer_result_status(result)
    if status == "affected":
        click.echo("✓ Bug存在于目标版本")
        click.echo(f"  状态: {status}")
        click.echo(f"  Commit: {result.commit}")
        click.echo(f"  方法: {result.method}")
        click.echo(f"  置信度: {result.confidence:.2%}")
        attempts = result.details.get("attempts", [])
        if attempts:
            click.echo(f"  尝试策略数: {len(attempts)}")
    else:
        label = "✗ Bug不存在于目标版本" if status == "not_affected" else "? 无法确认目标版本是否受影响"
        click.echo(label)
        click.echo(f"  状态: {status}")
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
    target_options: tuple[str, ...],
    targets_file: Optional[str],
    fix_message: Optional[str],
    repo: str,
    config: str,
    output: str,
    explain: bool,
    fix_index: int,
    list_fix_candidates: bool,
) -> None:
    resolved_targets = _resolve_targets(repo, target, target_options, targets_file)
    resolved_fix, _, resolved_from_message = _resolve_fix_and_target(
        repo,
        fix_commit,
        resolved_targets[0],
        fix_option,
        resolved_targets[0],
        fix_message,
        fix_index,
        list_fix_candidates,
    )
    config_obj = Config.from_file(config)
    tracer = BugTracer(config_obj, repo)
    results = []
    for resolved_target in resolved_targets:
        result = tracer.trace(resolved_fix, resolved_target)
        entry = {
            "result": result,
            "target": resolved_target,
            "status": _infer_result_status(result),
            "affected": result.found,
            "commit": result.commit,
            "method": result.method,
            "confidence": result.confidence,
            "details": result.details,
        }
        if explain:
            entry["analysis"] = _build_analysis(result)
            entry["resolved_fix"] = resolved_fix
            entry["resolved_target"] = resolved_target
            if resolved_from_message:
                entry["fix_message"] = resolved_from_message
        results.append(entry)

    if output == "json" and len(results) > 1:
        serialized_results = [{key: value for key, value in entry.items() if key != "result"} for entry in results]
        payload = {
            "resolved_fix": resolved_fix,
            "targets": serialized_results,
        }
        if resolved_from_message:
            payload["fix_message"] = resolved_from_message
        click.echo(json.dumps(payload, indent=2, ensure_ascii=False))
        return

    if output == "json" and len(results) == 1:
        payload = {
            "status": results[0]["status"],
            "affected": results[0]["affected"],
            "commit": results[0]["commit"],
            "method": results[0]["method"],
            "confidence": results[0]["confidence"],
            "details": results[0]["details"],
        }
        if explain:
            payload["analysis"] = results[0]["analysis"]
            payload["resolved_fix"] = resolved_fix
            payload["resolved_target"] = results[0]["resolved_target"]
            if resolved_from_message:
                payload["fix_message"] = resolved_from_message
        click.echo(json.dumps(payload, indent=2, ensure_ascii=False))
        return

    if len(results) == 1:
        _render_table(results[0]["result"], explain, resolved_fix, resolved_targets[0], resolved_from_message)
        return

    for entry in results:
        click.echo(f"Target: {entry['target']}")
        _render_table(
            entry["result"],
            explain,
            resolved_fix,
            entry["target"],
            resolved_from_message,
        )
        click.echo()


@cli.command(name="trace")
@click.argument("fix_commit", metavar="fix_commit", required=False)
@click.argument("target", metavar="target", required=False)
@click.option("--fix", "fix_option", help="显式指定修复commit，可替代位置参数 <fix_commit>")
@click.option("--fix-message", help="按提交信息搜索修复commit，例如 --fix-message 'divide by zero'")
@click.option("--fix-index", default=0, type=int, help="当 --fix-message 命中多个候选时，选择第几个候选")
@click.option("--list-fix-candidates", is_flag=True, help="仅列出 --fix-message 命中的候选提交，不执行trace")
@click.option("--target", "target_options", multiple=True, help="目标分支、tag或commit，可重复传入以批量分析")
@click.option("--targets-file", help="从文件读取多个目标版本，每行一个ref，支持#注释")
@click.option("--repo", "-r", default=".", help="目标Git仓库路径，默认当前目录")
@click.option("--config", "-c", default="config/coderipple.yaml", help="配置文件路径")
@click.option("--output", "-o", default="table", type=click.Choice(["table", "json"]), help="输出格式；json 会包含 status，--explain 时会附带 analysis")
@click.option("--explain", is_flag=True, help="输出结构化分析过程，包括各策略的 status / summary / evidence")
def trace(
    fix_commit,
    target,
    fix_option,
    fix_message,
    fix_index,
    list_fix_candidates,
    target_options,
    targets_file,
    repo,
    config,
    output,
    explain,
):
    """追溯目标版本是否仍受某个修复提交对应的Bug影响。

    支持旧用法：
      coderipple trace <fix_commit> <target>

    也支持显式参数：
      coderipple trace --fix <fix_commit> --target <target>
      coderipple trace --fix-message "<message>" --target <target>
      coderipple trace --fix <fix_commit> --target <target1> --target <target2>

    输出状态：
      affected: 目标版本仍受影响
      not_affected: 目标版本已包含修复或等价修复
      unknown: 当前策略无法确认目标版本是否受影响
    """
    try:
        _trace_command(
            fix_commit,
            target,
            fix_option,
            target_options,
            targets_file,
            fix_message,
            repo,
            config,
            output,
            explain,
            fix_index,
            list_fix_candidates,
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
@click.option("--fix-index", default=0, type=int, help="当 --fix-message 命中多个候选时，选择第几个候选")
@click.option("--list-fix-candidates", is_flag=True, help="仅列出 --fix-message 命中的候选提交，不执行trace")
@click.option("--target", "target_options", multiple=True, help="目标分支、tag或commit，可重复传入以批量分析")
@click.option("--targets-file", help="从文件读取多个目标版本，每行一个ref，支持#注释")
@click.option("--repo", "-r", default=".", help="目标Git仓库路径，默认当前目录")
@click.option("--config", "-c", default="config/coderipple.yaml", help="配置文件路径")
@click.option("--output", "-o", default="table", type=click.Choice(["table", "json"]), help="输出格式；json 会包含 status，--explain 时会附带 analysis")
@click.option("--explain", is_flag=True, help="输出结构化分析过程，包括各策略的 status / summary / evidence")
def affected(
    fix_commit,
    target,
    fix_option,
    fix_message,
    fix_index,
    list_fix_candidates,
    target_options,
    targets_file,
    repo,
    config,
    output,
    explain,
):
    """`trace` 的直观别名，直接表达目标版本是否受影响。"""
    try:
        _trace_command(
            fix_commit,
            target,
            fix_option,
            target_options,
            targets_file,
            fix_message,
            repo,
            config,
            output,
            explain,
            fix_index,
            list_fix_candidates,
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
@click.option("--fix-index", default=0, type=int, help="当 --fix-message 命中多个候选时，选择第几个候选")
@click.option("--target", "target_options", multiple=True, help="目标分支、tag或commit，可重复传入以批量诊断")
@click.option("--targets-file", help="从文件读取多个目标版本，每行一个ref，支持#注释")
@click.option("--repo", "-r", default=".", help="目标Git仓库路径，默认当前目录")
@click.option("--config", "-c", default="config/coderipple.yaml", help="配置文件路径；doctor 会提前校验是否可解析")
@click.option("--output", "-o", default="table", type=click.Choice(["table", "json"]), help="输出格式；json 会返回 repo / config / fix / targets 的诊断结果")
def doctor(fix_commit, target, fix_option, fix_message, fix_index, target_options, targets_file, repo, config, output):
    """检查仓库、fix、targets 和 config 是否都能被正确解析，提前暴露歧义和输入错误。"""
    try:
        _doctor_command(
            fix_commit,
            target,
            fix_option,
            target_options,
            targets_file,
            fix_message,
            repo,
            config,
            output,
            fix_index,
        )
    except click.ClickException:
        raise
    except git.exc.InvalidGitRepositoryError:
        raise click.ClickException(f"{repo!r} 不是有效的Git仓库")
    except Exception as e:
        click.echo(f"错误: {e}", err=True)
        raise click.Abort()


@cli.command(name="find-fix")
@click.option("--message", required=True, help="按提交信息搜索候选修复提交")
@click.option("--target", help="可选目标版本；排序时会降低已在目标中可达的候选优先级")
@click.option("--path", help="仅返回直接修改过该路径的候选提交")
@click.option("--since-days", type=int, help="仅返回最近 N 天内的候选提交")
@click.option("--repo", "-r", default=".", help="目标Git仓库路径，默认当前目录")
@click.option("--limit", default=10, show_default=True, type=int, help="最多返回多少个候选提交")
@click.option("--output", "-o", default="table", type=click.Choice(["table", "json"]), help="输出格式；json 会返回候选列表和排序上下文")
def find_fix(message, target, path, since_days, repo, limit, output):
    """根据提交信息搜索候选修复提交，供后续 trace/affected 使用。

    候选默认按摘要匹配度、提交时间、以及相对 target 的可达性综合排序。
    """
    try:
        _find_fix_command(message, target, repo, limit, output, path, since_days)
    except click.ClickException:
        raise
    except git.exc.InvalidGitRepositoryError:
        raise click.ClickException(f"{repo!r} 不是有效的Git仓库")
    except Exception as e:
        click.echo(f"错误: {e}", err=True)
        raise click.Abort()


if __name__ == "__main__":
    cli()
