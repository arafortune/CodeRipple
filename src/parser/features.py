"""
特征提取器
"""

import re
from typing import List
from dataclasses import dataclass, field
from src.parser.ast import ASTParser, ASTNode


@dataclass
class CodeFeatures:
    """代码特征"""
    tokens: List[str] = field(default_factory=list)
    ngrams: List[str] = field(default_factory=list)
    variables: List[str] = field(default_factory=list)
    functions: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    operators: List[str] = field(default_factory=list)


class FeatureExtractor:
    """特征提取器"""
    
    def __init__(self, language: str = 'python'):
        self.language = language
        self.parser = ASTParser(language)
    
    def extract(self, code: str) -> CodeFeatures:
        """
        提取代码特征
        
        Args:
            code: 代码字符串
            
        Returns:
            代码特征
        """
        features = CodeFeatures()
        
        # 提取词法特征
        features.tokens = self._extract_tokens(code)
        features.ngrams = self._extract_ngrams(features.tokens, n=3)
        
        # 提取语义特征
        features.keywords = self._extract_keywords(code)
        features.operators = self._extract_operators(code)
        
        # 提取AST特征
        try:
            ast = self.parser.parse(code)
            features.variables = self._extract_variables(ast)
            features.functions = self._extract_functions(ast)
        except Exception:
            pass
        
        return features
    
    def _extract_tokens(self, code: str) -> List[str]:
        """提取词法token"""
        tokens = []
        token_pattern = r'\w+|[^\w\s]'
        
        for match in re.finditer(token_pattern, code):
            tokens.append(match.group())
        
        return tokens
    
    def _extract_ngrams(self, tokens: List[str], n: int = 3) -> List[str]:
        """提取n-gram"""
        ngrams = []
        
        for i in range(len(tokens) - n + 1):
            ngram = ' '.join(tokens[i:i+n])
            ngrams.append(ngram)
        
        return ngrams
    
    def _extract_keywords(self, code: str) -> List[str]:
        """提取关键字"""
        keywords = set()
        keyword_list = [
            'def', 'class', 'if', 'else', 'elif', 'while', 'for',
            'return', 'import', 'from', 'as', 'try', 'except', 'finally',
            'with', 'lambda', 'yield', 'global', 'nonlocal', 'pass',
            'break', 'continue', 'raise', 'assert', 'del', 'in', 'is'
        ]
        
        for keyword in keyword_list:
            if keyword in code:
                keywords.add(keyword)
        
        return list(keywords)
    
    def _extract_operators(self, code: str) -> List[str]:
        """提取操作符"""
        operators = set()
        operator_list = [
            '+', '-', '*', '/', '//', '%', '**',
            '=', '+=', '-=', '*=', '/=', '%=', '**=',
            '==', '!=', '<', '>', '<=', '>=',
            'and', 'or', 'not', '&', '|', '^', '~',
            '<<', '>>', '->', '=>'
        ]
        
        for op in operator_list:
            if op in code:
                operators.add(op)
        
        return list(operators)
    
    def _extract_variables(self, ast: ASTNode) -> List[str]:
        """提取变量名"""
        variables = set()
        
        def traverse(node):
            if node.type == 'Name' and 'name' in node.metadata:
                variables.add(node.metadata['name'])
            
            for child in node.children:
                traverse(child)
        
        traverse(ast)
        return list(variables)
    
    def _extract_functions(self, ast: ASTNode) -> List[str]:
        """提取函数名"""
        functions = set()
        
        def traverse(node):
            if node.type == 'FunctionDef' and 'name' in node.metadata:
                functions.add(node.metadata['name'])
            
            for child in node.children:
                traverse(child)
        
        traverse(ast)
        return list(functions)
