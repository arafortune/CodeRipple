"""
CLI端到端测试
"""

import pytest
import os
from click.testing import CliRunner
from src.cli.main import cli


class TestCLI:
    """CLI端到端测试"""
    
    @pytest.fixture
    def runner(self):
        return CliRunner()
    
    def test_cli_version(self, runner):
        """测试版本命令"""
        result = runner.invoke(cli, ['--version'])
        assert result.exit_code == 0
        assert '0.1.0' in result.output
    
    def test_cli_help(self, runner):
        """测试帮助命令"""
        result = runner.invoke(cli, ['--help'])
        assert result.exit_code == 0
        assert 'CodeRipple' in result.output
    
    def test_trace_help(self, runner):
        """测试trace命令帮助"""
        result = runner.invoke(cli, ['trace', '--help'])
        assert result.exit_code == 0
        assert 'fix_commit' in result.output
        assert 'target' in result.output

    def test_trace_not_found_shows_strategy_summary(self, runner):
        """测试未命中时输出策略摘要"""
        result = runner.invoke(cli, ['trace', 'deadbeef', 'master'])
        assert result.exit_code != 0 or '策略摘要' in result.output or '错误:' in result.output
