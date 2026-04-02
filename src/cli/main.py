"""
CLI主入口
"""

import json

import click

from src.config import Config
from src.core.tracer import BugTracer


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """CodeRipple - Git历史分析工具"""
    return None


@cli.command()
@click.argument("fix_commit", metavar="fix_commit")
@click.argument("target", metavar="target")
@click.option("--repo", "-r", default=".")
@click.option("--config", "-c", default="config/coderipple.yaml")
@click.option("--output", "-o", default="table", type=click.Choice(["table", "json"]))
def trace(fix_commit, target, repo, config, output):
    """追溯bug是否影响目标版本"""
    try:
        config_obj = Config.from_file(config)
        tracer = BugTracer(config_obj, repo)
        result = tracer.trace(fix_commit, target)

        if output == "json":
            click.echo(
                json.dumps(
                    {
                        "found": result.found,
                        "commit": result.commit,
                        "method": result.method,
                        "confidence": result.confidence,
                        "details": result.details,
                    },
                    indent=2,
                    ensure_ascii=False,
                )
            )
        else:
            if result.found:
                click.echo("✓ Bug存在于目标版本")
                click.echo(f"  Commit: {result.commit}")
                click.echo(f"  方法: {result.method}")
                click.echo(f"  置信度: {result.confidence:.2%}")
            else:
                click.echo("✗ Bug不存在于目标版本")

    except Exception as e:
        click.echo(f"错误: {e}", err=True)
        raise click.Abort()


if __name__ == "__main__":
    cli()
