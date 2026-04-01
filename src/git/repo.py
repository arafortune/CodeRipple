"""
Git仓库操作封装
"""

from pathlib import Path
from typing import Dict, Iterator, Optional

import git


class GitRepository:
    """Git仓库操作封装"""

    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path).resolve()
        self.repo = git.Repo(self.repo_path)
        self._commit_cache: Dict[str, git.Commit] = {}
        self._file_cache: Dict[str, Optional[str]] = {}

    def get_commit(self, commit_hash: str) -> git.Commit:
        """获取commit对象"""
        if commit_hash not in self._commit_cache:
            self._commit_cache[commit_hash] = self.repo.commit(commit_hash)
        return self._commit_cache[commit_hash]

    def get_file_content(self, commit: git.Commit, file_path: str) -> Optional[str]:
        """获取文件内容"""
        cache_key = f"{commit.hexsha}:{file_path}"
        if cache_key not in self._file_cache:
            try:
                blob = commit.tree / file_path
                self._file_cache[cache_key] = blob.data_stream.read().decode("utf-8")
            except KeyError:
                self._file_cache[cache_key] = None
        return self._file_cache[cache_key]

    def is_ancestor(self, commit_hash: str, target_ref: str) -> bool:
        """检查commit是否是target_ref的祖先"""
        try:
            self.repo.git.merge_base("--is-ancestor", commit_hash, target_ref)
            return True
        except git.exc.GitCommandError:
            return False

    def iter_commits(self, ref: str, max_count: Optional[int] = None) -> Iterator[git.Commit]:
        """迭代commit"""
        return self.repo.iter_commits(ref, max_count=max_count)
