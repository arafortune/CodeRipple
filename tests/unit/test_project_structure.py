"""
项目结构测试
"""

import pytest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class TestProjectStructure:
    """项目结构测试"""

    def test_src_directory_exists(self):
        """测试src目录存在"""
        src_path = ROOT / "src"
        assert src_path.exists()
        assert src_path.is_dir()

    def test_tests_directory_exists(self):
        """测试tests目录存在"""
        tests_path = ROOT / "tests"
        assert tests_path.exists()
        assert tests_path.is_dir()

    def test_config_directory_exists(self):
        """测试config目录存在"""
        config_path = ROOT / "config"
        assert config_path.exists()
        assert config_path.is_dir()

    def test_doc_directory_exists(self):
        """测试doc目录存在"""
        doc_path = ROOT / "doc"
        assert doc_path.exists()
        assert doc_path.is_dir()

    def test_core_module_exists(self):
        """测试core模块存在"""
        core_path = ROOT / "src" / "core"
        assert core_path.exists()
        assert core_path.is_dir()

    def test_git_module_exists(self):
        """测试git模块存在"""
        git_path = ROOT / "src" / "git"
        assert git_path.exists()
        assert git_path.is_dir()

    def test_parser_module_exists(self):
        """测试parser模块存在"""
        parser_path = ROOT / "src" / "parser"
        assert parser_path.exists()
        assert parser_path.is_dir()

    def test_cli_module_exists(self):
        """测试cli模块存在"""
        cli_path = ROOT / "src" / "cli"
        assert cli_path.exists()
        assert cli_path.is_dir()
