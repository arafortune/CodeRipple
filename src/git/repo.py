"""
Git仓库操作封装
"""

from collections import defaultdict
from pathlib import Path
import subprocess
from typing import Dict, Iterator, Optional

import git


class GitRepository:
    """Git仓库操作封装"""

    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path).resolve()
        self.repo = git.Repo(self.repo_path)
        self._commit_cache: Dict[str, git.Commit] = {}
        self._file_cache: Dict[str, Optional[str]] = {}
        self._patch_id_cache: Dict[str, Optional[str]] = {}

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

    def get_changed_file_states(self, commit_hash: str) -> Dict[str, Optional[str]]:
        """获取commit直接修改的文件在该commit中的最终内容"""
        commit = self.get_commit(commit_hash)
        if not commit.parents:
            return {}

        states: Dict[str, Optional[str]] = {}
        for diff in commit.parents[0].diff(commit):
            path = diff.b_path or diff.a_path
            if not path:
                continue
            content = self.get_file_content(commit, path)
            if content is not None:
                states[path] = content
        return states

    def get_patch_id(self, commit_hash: str) -> Optional[str]:
        """获取commit的稳定patch-id，用于识别cherry-pick/backport等价修复"""
        if commit_hash in self._patch_id_cache:
            return self._patch_id_cache[commit_hash]

        commit = self.get_commit(commit_hash)
        if not commit.parents:
            self._patch_id_cache[commit_hash] = None
            return None

        try:
            patch_text = self.repo.git.show(
                commit.hexsha,
                format="",
                no_ext_diff=True,
            )
            output = subprocess.check_output(
                ["git", "patch-id", "--stable"],
                cwd=self.repo_path,
                text=True,
                input=patch_text,
            ).strip()
            patch_id = output.split()[0] if output else None
        except (git.exc.GitCommandError, subprocess.CalledProcessError, IndexError):
            patch_id = None

        self._patch_id_cache[commit_hash] = patch_id
        return patch_id

    def find_equivalent_commit(self, commit_hash: str, target_ref: str, max_count: int = 500) -> Optional[str]:
        """在目标历史中查找与给定commit具有相同patch-id的提交"""
        patch_id = self.get_patch_id(commit_hash)
        if not patch_id:
            return None

        for commit in self.iter_commits(target_ref, max_count=max_count):
            if commit.hexsha == commit_hash:
                return commit.hexsha
            candidate_patch_id = self.get_patch_id(commit.hexsha)
            if candidate_patch_id and candidate_patch_id == patch_id:
                return commit.hexsha
        return None

    def has_equivalent_file_state(self, commit_hash: str, target_ref: str) -> bool:
        """检查目标ref在被修复文件上的最终状态是否与fix commit一致"""
        expected_states = self.get_changed_file_states(commit_hash)
        if not expected_states:
            return False

        target_commit = self.get_commit(target_ref)
        target_paths_by_name = self._group_blob_paths_by_name(target_commit)
        for path, expected_content in expected_states.items():
            actual_content = self.get_file_content(target_commit, path)
            if actual_content == expected_content:
                continue

            if actual_content is not None:
                return False

            basename = Path(path).name
            candidate_paths = target_paths_by_name.get(basename, [])
            if not candidate_paths:
                return False
            if not any(self.get_file_content(target_commit, candidate_path) == expected_content for candidate_path in candidate_paths):
                return False
        return True

    def _group_blob_paths_by_name(self, commit: git.Commit) -> Dict[str, list[str]]:
        """按文件名聚合提交树中的blob路径，用于路径迁移后的内容比对"""
        grouped: Dict[str, list[str]] = defaultdict(list)
        for item in commit.tree.traverse():
            if item.type == "blob":
                grouped[Path(item.path).name].append(item.path)
        return dict(grouped)
