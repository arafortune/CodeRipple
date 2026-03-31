"""
测试基类和fixtures
"""

import pytest
import git
import tempfile
import shutil
from pathlib import Path


@pytest.fixture
def test_repo():
    """创建测试仓库"""
    tmp_path = Path(tempfile.mkdtemp())
    repo = git.Repo.init(tmp_path)
    
    readme = tmp_path / "README.md"
    readme.write_text("# Test Repo")
    repo.index.add(["README.md"])
    repo.index.commit("Initial commit")
    
    yield tmp_path
    
    shutil.rmtree(tmp_path)


@pytest.fixture
def sample_code():
    """示例代码"""
    return """
def calculate_sum(a, b):
    result = a + b
    return result
"""


def create_commit(repo_path: Path, message: str, branch: str = "master") -> git.Commit:
    """创建测试commit"""
    repo = git.Repo(repo_path)
    
    if branch != "master" and branch not in repo.heads:
        repo.git.checkout("-b", branch)
    
    test_file = repo_path / "test.txt"
    test_file.write_text(message)
    repo.index.add(["test.txt"])
    commit = repo.index.commit(message)
    
    return commit
