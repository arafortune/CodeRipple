"""
AST解析器测试
"""

import pytest
from src.parser.ast import ASTParser


class TestASTParser:
    """AST解析器测试"""
    
    @pytest.fixture
    def parser(self):
        return ASTParser('python')
    
    def test_parse_simple_function(self, parser):
        """测试解析简单函数"""
        code = """
def calculate_sum(a, b):
    result = a + b
    return result
"""
        ast = parser.parse(code)
        
        assert ast is not None
        assert ast.type == 'Module'
    
    def test_parse_with_syntax_error(self, parser):
        """测试解析语法错误"""
        code = "def broken("
        
        with pytest.raises(Exception):
            parser.parse(code)
    
    def test_parse_empty_code(self, parser):
        """测试解析空代码"""
        code = ""
        ast = parser.parse(code)
        
        assert ast is not None
    
    def test_parse_multi_function(self, parser):
        """测试解析多个函数"""
        code = """
def func1():
    return 1

def func2():
    return 2
"""
        ast = parser.parse(code)
        
        assert ast is not None
        assert len(ast.children) >= 2
