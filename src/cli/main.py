"""
CLI主入口
"""

import click
import json
from pathlib import Path
from src.core.tracer import BugTracer
from src.config import Config
from src.git.repo import GitRepository


@click.group()
@click.version_option(version='0.1.0')
def cli():
    """CodeRipple - Git历史分析工具"""
    pass


@cli.command()
@click.argument('fix_commit')
@click.argument('target')
@click.option('--repo', '-r', default='.', help='仓库路径')
@click.option('--config', '-c', default='config/coderipple.yaml', help='配置文件')
@click.option('--output', '-o', default='table', type=click.Choice(['table', 'json']), help='输出格式')
def trace(fix_commit, target, repo, config, output):
    """
    追溯bug是否影响目标版本
    
    示例:
        coderipple trace abc123 v1.0.0
        coderipple trace abc123 commercial:release/v1.0
    """
    try:
        config_obj = Config.from_file(config)
        tracer = BugTracer(config_obj, repo)
        
        target_repo = GitRepository(repo)
        result = tracer.trace(fix_commit, target_repo, target)
        
        if output == 'json':
            click.echo(json.dumps({
                'found': result.found,
                'commit': result.commit,
                'method': result.method,
                'confidence': result.confidence,
                'details': result.details
            }, indent=2))
        else:
            if result.found:
                click.echo(f"✓ Bug存在于目标版本")
                click.echo(f"  Commit: {result.commit}")
                click.echo(f"  方法: {result.method}")
                click.echo(f"  置信度: {result.confidence:.2%}")
            else:
                click.echo("✗ Bug不存在于目标版本")
    
    except Exception as e:
        click.echo(f"错误: {e}", err=True)
        raise click.Abort()


if __name__ == '__main__':
    cli()
