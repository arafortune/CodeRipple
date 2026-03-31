"""
代码块追溯策略
"""

from typing import Optional
from dataclasses import dataclass
import git
from src.core.strategies.base import TraceStrategy
from src.core.result import TraceResult
from src.git.repo import GitRepository


@dataclass
class CodeBlock:
    """代码块"""
    file_path: str
    start_line: int
    end_line: int
    content: str
    lines: list


@dataclass
class BlameInfo:
    """Blame信息"""
    commit_hash: str
    author: str
    line: int
    content: str


class CodeBlockStrategy(TraceStrategy):
    """代码块追溯策略"""
    
    def trace(self, fix_commit: str, target_repo: GitRepository,
              target_ref: str) -> TraceResult:
        """执行追溯"""
        code_block = self._extract_fix_code_block(fix_commit)
        if not code_block:
            return TraceResult.not_found()
        
        blame_infos = self._blame_code_block(fix_commit, code_block)
        if not blame_infos:
            return TraceResult.not_found()
        
        latest_commit = self._find_latest_commit(blame_infos)
        
        if target_repo.is_ancestor(latest_commit, target_ref):
            return TraceResult(
                found=True,
                commit=latest_commit,
                method='code_block',
                confidence=0.95,
                details={
                    'file': code_block.file_path,
                    'lines': [code_block.start_line, code_block.end_line],
                    'original_commit': latest_commit
                }
            )
        
        return TraceResult.not_found()
    
    def _extract_fix_code_block(self, commit_hash: str) -> Optional[CodeBlock]:
        """提取修复commit修改的代码块"""
        commit = self.repo.get_commit(commit_hash)
        
        if not commit.parents:
            return None
        
        for diff in commit.parents[0].diff(commit):
            if diff.change_type == 'M':
                diff_text = diff.diff.decode('utf-8')
                added_lines = self._extract_added_lines(diff_text)
                
                if added_lines:
                    return CodeBlock(
                        file_path=diff.a_path,
                        start_line=min(added_lines),
                        end_line=max(added_lines),
                        content=self._get_code_at_lines(commit, diff.a_path, added_lines),
                        lines=self._get_lines_at_lines(commit, diff.a_path, added_lines)
                    )
        
        return None
    
    def _extract_added_lines(self, diff_text: str) -> list:
        """从diff中提取新增的行号"""
        added_lines = []
        current_line = 0
        
        for line in diff_text.split('\n'):
            if line.startswith('@@'):
                parts = line.split()
                for part in parts:
                    if part.startswith('+'):
                        current_line = int(part[1:].split(',')[0])
            elif line.startswith('+') and not line.startswith('++'):
                added_lines.append(current_line)
                current_line += 1
        
        return added_lines
    
    def _get_code_at_lines(self, commit: git.Commit, file_path: str, 
                           lines: list) -> str:
        """获取指定行的代码"""
        content = self.repo.get_file_content(commit, file_path)
        if not content:
            return ""
        
        all_lines = content.split('\n')
        return '\n'.join(all_lines[min(lines)-1:max(lines)])
    
    def _get_lines_at_lines(self, commit: git.Commit, file_path: str,
                            lines: list) -> list:
        """获取指定行的内容"""
        content = self.repo.get_file_content(commit, file_path)
        if not content:
            return []
        
        all_lines = content.split('\n')
        return [all_lines[i-1] for i in lines]
    
    def _blame_code_block(self, commit_hash: str, 
                          code_block: CodeBlock) -> list:
        """使用git blame追溯代码块"""
        blame_infos = []
        
        try:
            blame_output = self.repo.repo.git.blame(
                f'-L{code_block.start_line},{code_block.end_line}',
                commit_hash,
                '--',
                code_block.file_path
            )
            
            for line in blame_output.split('\n'):
                blame_info = self._parse_blame_line(line)
                if blame_info:
                    blame_infos.append(blame_info)
        except git.exc.GitCommandError:
            pass
        
        return blame_infos
    
    def _parse_blame_line(self, line: str) -> Optional[BlameInfo]:
        """解析blame输出行"""
        if not line.strip():
            return None
        
        try:
            parts = line.split(' ', 1)
            commit_hash = parts[0]
            
            meta_end = parts[1].index(')')
            meta = parts[1][1:meta_end]
            meta_parts = meta.split()
            
            author = ' '.join(meta_parts[:-2])
            line_num = int(meta_parts[-1])
            
            content = parts[1][meta_end + 2:]
            
            return BlameInfo(
                commit_hash=commit_hash,
                author=author,
                line=line_num,
                content=content
            )
        except (ValueError, IndexError):
            return None
    
    def _find_latest_commit(self, blame_infos: list) -> str:
        """找到最晚的commit"""
        return blame_infos[0].commit_hash
    
    @property
    def priority(self) -> int:
        return 2
    
    @property
    def confidence(self) -> float:
        return 0.95
