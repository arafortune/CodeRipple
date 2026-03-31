"""
特征提取测试
"""

import pytest
from src.parser.features import FeatureExtractor


class TestFeatureExtractor:
    """特征提取器测试"""
    
    @pytest.fixture
    def extractor(self):
        return FeatureExtractor()
    
    def test_extract_tokens(self, extractor):
        """测试提取词法token"""
        code = "def func(a, b): return a + b"
        features = extractor.extract(code)
        
        assert 'def' in features.tokens
        assert 'func' in features.tokens
        assert 'return' in features.tokens
    
    def test_extract_ngrams(self, extractor):
        """测试提取n-gram"""
        code = "def func(a, b): return a + b"
        features = extractor.extract(code)
        
        assert len(features.ngrams) > 0
        assert any('def func' in ngram for ngram in features.ngrams)
    
    def test_extract_variables(self, extractor):
        """测试提取变量"""
        code = """
def func(a, b):
    x = a + b
    return x
"""
        features = extractor.extract(code)
        
        assert 'a' in features.variables
        assert 'b' in features.variables
        assert 'x' in features.variables
    
    def test_extract_keywords(self, extractor):
        """测试提取关键字"""
        code = "def func(): if True: return 1"
        features = extractor.extract(code)
        
        assert 'def' in features.keywords
        assert 'if' in features.keywords
        assert 'return' in features.keywords
