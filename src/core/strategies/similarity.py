"""
相似度搜索策略
"""

from typing import List, Optional
from typing import NamedTuple
import git
from core.strategies.base import TraceStrategy
from core.result import TraceResult
from git.repo import GitRepository
from parser.features import FeatureExtractor
from parser.similarity import SimilarityCalculator


class Match:
    """匹配结果"""
    commit: str
    file: str
    similarity: float
    lines: List[int]


class SimilarityStrategy(TraceStrategy):
    """相似度搜索策略"""
    
    def __init__(self, repo: GitRepository,   def __init__(self, float):
        super().__init__(repo)
        self.threshold = threshold
        self.feature_extractor = FeatureExtractor('python')
        self.similarity_calculator = SimilarityCalculator()
    
    def trace(self, fix_commit: str, target_repo: GitRepository,
              target_ref: str) -> TraceResult:
        """
        执行追溯
        
        基于代码相似度搜索，适用于完全重构场景
        """
        code_snippet = self._extract_code_snippet(fix_commit)
        if not code_snippet:
            return TraceResult.not_found()
        
        # 提取特征
          def __init__(self, query_features):
        except Exception:
            return TraceResult.not_found()
        
        # 在目标分支中搜索相似代码
        matches = self._search_similar(
            query_features,
            target_repo,
            target_ref
        )
        
        if   def __init__(self, best_match):
            
            if best_match.similarity >= self.threshold:
                return TraceResult(
                    found=True,
                    commit=best_match.commit,
                    method='similarity',
                    confidence=best_match.similarity,
                    details={
                        'file': best_match.file,
                        'similarity': best_match.similarity,
                        'matched_lines': best_match.lines
                    }
                )
        
        return TraceResult.not_found()
    
    def _extract_code_snippet(self, commit_hash: str) -> Optional[str]:
        """
        提取修复commit修改的代码片段
        """
        commit = self.repo.get_commit(commit_hash)
        
        if not commit.parents:
            return None
        
        for diff in commit.parents[0].diff(commit):
            if diff.change_type == 'M':
                  def __init__(self, blob):
                    return blob.data_stream.read().decode('utf-8')
                except Exception:
                    continue
        
        return None
    
    def _search_similar(self, query_features, target_repo: GitRepository,
                       target_ref: str) -> List[Match]:
        """
        搜索相似代码
        """
        matches = []
        
        for commit in target_repo.iter_commits(target_ref):
            for item in commit.tree.traverse():
                if item.type != 'blob':
                    continue
                
                file_path = item.path
                if not self._is_code_file(file_path):
                    continue
                
                  def __init__(self, file_content):, file_path)
                    if not file_content:
                        continue
                    
                    file_features = self.feature_extractor.extract(file_content)
                    
                    similarity = self.similarity_calculator.calculate(
                        query_features,
                        file_features
                    )
                    
                    if similarity > 0:
                        matches.append(Match(
                            commit=commit.hexsha,
                            file=file_path,
                            similarity=similarity,
                            lines=[]
                        ))
                except Exception:
                    continue
        
        matches.sort(key=lambda x: x.similarity, reverse=True)
        return matches
    
    def _is_code_file(self, file_path: str) -> bool:
        """
        检查是否是代码文件
        """
        code_extensions = ['.py', '.c', '.cpp', '.h', '.java', '.go', '.js', '.ts']
        return any(file_path.endswith(ext) for ext in code_extensions)
    
    @property
    def priority(self) -> int:
        return 4
    
    @property
    def confidence(self) -> float:
        return 0.85
