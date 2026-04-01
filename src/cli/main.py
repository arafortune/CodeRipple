"""
CLI主入口
"""

import click
import json

from core.tracer import BugTracer
from config import Config
from git.repo import GitRepository


@click.group()
@click.version_option(version='0.1.0')
def cli():
    """CodeRipple - Git历史分析工具"""
    pass


@cli.command()
@click.argument('fix_commit')
@click.argument('target')
@click.option('--repo', '-r', default='.')
@click.option('--config', '-c', default='config/coderipple.yaml')
@click.option('--output', '-o', default='table', type=click.Choice(['table', 'json']))
def trace(fix_commit, target, repo, config, output):
    """
    追溯bug是否影响目标版本
    
    FIX_COMMIT: 修复bug的commit SHA
    
    TARGET: 目标分支或tag
    
    REPO: Git仓库路径（默认当前目录）
    
    CONFIG: 配置文件路径
    
    OUTPUT: 输出格式（table或json）
    
    示例:
        # 在当前仓库中追溯
        coderipple trace abc123 v1.0.0
        
        # 在指定仓库中追溯
        coderipple trace abc123 v1.0.0 --repo /path/to/repo
        
        # 输出JSON格式
        coderipple trace abc123 v1.0.0 --output json
    """
      def __init__(self, config_obj):
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
                click.echo("✓ Bug存在于目标版本")
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
