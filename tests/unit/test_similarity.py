"""
相似度计算测试
"""

import pytest
from src.parser.similarity import SimilarityCalculator


class TestSimilarityCalculator:
    """相似度计算器测试"""
    
    @pytest.fixture
    def calculator(self):
        return SimilarityCalculator()
    
    def test_jaccard_similarity(self, calculator):
        """测试Jaccard相似度"""
        set1 = {'a', 'b', 'c'}
        set2 = {'b', 'c', 'd'}
        
        sim = calculator._jaccard_similarity(set1, set2)
        
        assert 0 < sim < 1
        assert sim == 2/3
    
    def test_jaccard_identical(self, calculator):
        """测试相同集合"""
        set1 = {'a', 'b', 'c'}
        set2 = {'a', 'b', 'c'}
        
        sim = calculator._jaccard_similarity(set1, set2)
        
        assert sim == 1.0
    
    def test_jaccard_disjoint(self, calculator):
        """测试不相交集合"""
        set1 = {'a', 'b'}
        set2 = {'c', 'd'}
        
        sim = calculator._jaccard_similarity(set1, set2)
        
        assert sim == 0.0
    
    def test_edit_distance(self, calculator):
        """测试编辑距离"""
        s1 = "kitten"
        s2 = "sitting"
        
        distance = calculator._edit_distance(s1, s2)
        
        assert distance == 3
    
    def test_edit_distance_identical(self, calculator):
        """测试相同字符串"""
        s1 = "hello"
        s2 = "hello"
        
        distance = calculator._edit_distance(s1, s2)
        
        assert distance == 0
    
    def test_lcs(self, calculator):
        """测试最长公共子序列"""
        seq1 = ['a', 'b', 'c', 'd']
        seq2 = ['b', 'd', 'e']
        
        lcs = calculator._longest_common_subsequence(seq1, seq2)
        
        assert lcs == ['b', 'd']
