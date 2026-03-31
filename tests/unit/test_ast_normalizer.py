"""
AST标准化器测试
"""

import pytest
from src.parser.ast import ASTParser, ASTNode
from src.parser.normalizer import ASTNormalizer


class TestASTNormalizer:
    """AST标准化器测试"""
    
    @pytest.fixture
    def parser(self):
        return ASTParser('python')
    
    @pytest.fixture
    def normalizer(self):
        return ASTNormalizer()
    
    def test_normalize_variable_names(self, parser, normalizer):
        """测试标准化变量名"""
        code = """
def calculate_sum(a, b):
    result = a + b
    return result
"""
        ast = parser.parse(code)
        normalized = normalizer.normalize(ast)
        
        # 检查变量名被替换
        assert 'a' not in str(normalized.fingerprint)
        assert 'b' not in str(normalized.fingerprint)
        assert 'result' not in str(normalized.fingerprint)
    
    def test_fingerprint_generation(self, parser, normalizer):
        """测试指纹生成"""
        code = """
def func1():
    x = 1
    return x
"""
        ast = parser.parse(code)
        normalized = normalizer.normalize(ast)
        
        assert normalized.fingerprint is not None
        assert len(normalized.fingerprint) > 0
    
    def test_same_structure_same_fingerprint(self, parser, normalizer):
        """测试相同结构产生相同指纹"""
        code1 = """
def func1(a):
    x = a
    return x
"""
        code2 = """
def func2(b):
    y = b
    return y
"""
        ast1 = parser.parse(code1)
        ast2 = parser.parse(code2)
        
        norm1 = normalizer.normalize(ast1)
        norm2 = normalizer.normalize(ast2)
        
        assert norm1.fingerprint == norm2.fingerprint
