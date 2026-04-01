"""
相似度计算器
"""

from typing import List, Set

from src.parser.features import CodeFeatures


class SimilarityCalculator:
    """相似度计算器"""
    
    def calculate(self, features1: CodeFeatures, 
                  features2: CodeFeatures) -> float:
        """
        计算综合相似度
        
        使用加权平均
        """
        # 1. 字符串相似度
        token_sim = self._jaccard_similarity(
            set(features1.tokens),
            set(features2.tokens)
        )
        
        ngram_sim = self._jaccard_similarity(
            set(features1.ngrams),
            set(features2.ngrams)
        )
        
        # 2. 语义相似度
        var_sim = self._jaccard_similarity(
            set(features1.variables),
            set(features2.variables)
        )
        
        func_sim = self._jaccard_similarity(
            set(features1.functions),
            set(features2.functions)
        )
        
        keyword_sim = self._jaccard_similarity(
            set(features1.keywords),
            set(features2.keywords)
        )
        
        operator_sim = self._jaccard_similarity(
            set(features1.operators),
            set(features2.operators)
        )
        
        # 加权平均
        weights = {
            'token': 0.20,
            'ngram': 0.20,
            'variable': 0.15,
            'function': 0.15,
            'keyword': 0.15,
            'operator': 0.15
        }
        
        total_sim = (
            weights['token'] * token_sim +
            weights['ngram'] * ngram_sim +
            weights['variable'] * var_sim +
            weights['function'] * func_sim +
            weights['keyword'] * keyword_sim +
            weights['operator'] * operator_sim
        )
        
        return total_sim
    
    def _jaccard_similarity(self, set1: Set, set2: Set) -> float:
        """
        Jaccard相似度
        
        J(A,B) = |A∩B| / |A∪B|
        """
        if not set1 and not set2:
            return 1.0
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        return intersection / union if union > 0 else 0.0
    
    def _edit_distance(self, s1: str, s2: str) -> int:
        """
        编辑距离（Levenshtein距离）
        """
        m, n = len(s1), len(s2)
        
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        
        for i in range(m + 1):
            dp[i][0] = i
        for j in range(n + 1):
            dp[0][j] = j
        
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if s1[i-1] == s2[j-1]:
                    dp[i][j] = dp[i-1][j-1]
                else:
                    dp[i][j] = min(
                        dp[i-1][j] + 1,
                        dp[i][j-1] + 1,
                        dp[i-1][j-1] + 1
                    )
        
        return dp[m][n]
    
    def _longest_common_subsequence(self, seq1: List[str], 
                                    seq2: List[str]) -> List[str]:
        """
        最长公共子序列
        """
        m, n = len(seq1), len(seq2)
        
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if seq1[i-1] == seq2[j-1]:
                    dp[i][j] = dp[i-1][j-1] + 1
                else:
                    dp[i][j] = max(dp[i-1][j], dp[i][j-1])
        
        lcs = []
        i, j = m, n
        while i > 0 and j > 0:
            if seq1[i-1] == seq2[j-1]:
                lcs.append(seq1[i-1])
                i -= 1
                j -= 1
            elif dp[i-1][j] > dp[i][j-1]:
                i -= 1
            else:
                j -= 1
        
        return lcs[::-1]
