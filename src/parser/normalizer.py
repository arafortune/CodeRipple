"""
AST标准化器
"""

from typing import Dict
from dataclasses import dataclass
from src.parser.ast import ASTNode


@dataclass
class NormalizedAST:
    """标准化后的AST"""
    root: ASTNode
    fingerprint: str
    variable_map: Dict[str, str]


class ASTNormalizer:
    """AST标准化器"""
    
    def __init__(self):
        self.var_counter = 0
        self.var_map = {}
    
    def normalize(self, ast: ASTNode) -> NormalizedAST:
        """
        标准化AST
        
        Args:
            ast: AST节点
            
        Returns:
            标准化后的AST
        """
        self.var_counter = 0
        self.var_map = {}
        
        normalized_root = self._normalize_node(ast)
        fingerprint = self._generate_fingerprint(normalized_root)
        
        return NormalizedAST(
            root=normalized_root,
            fingerprint=fingerprint,
            variable_map=self.var_map.copy()
        )
    
    def _normalize_node(self, node: ASTNode) -> ASTNode:
        """
        标准化节点
        
        替换变量名为v1, v2...
        """
        if node is None:
            return ASTNode(type='none')
        
        metadata = node.metadata.copy()
        
        # 标准化变量名
        if node.type == 'Name' and 'name' in metadata:
            var_name = metadata['name']
            if var_name not in self.var_map:
                self.var_map[var_name] = f'v{self.var_counter}'
                self.var_counter += 1
            metadata['name'] = self.var_map[var_name]
        
        # 标准化函数名
        elif node.type == 'FunctionDef' and 'name' in metadata:
            func_name = metadata['name']
            if func_name not in self.var_map:
                self.var_map[func_name] = f'f{self.var_counter}'
                self.var_counter += 1
            metadata['name'] = self.var_map[func_name]
        
        # 递归标准化子节点
        normalized_children = [
            self._normalize_node(child)
            for child in node.children
        ]
        
        return ASTNode(
            type=node.type,
            children=normalized_children,
            metadata=metadata
        )
    
    def _generate_fingerprint(self, node: ASTNode) -> str:
        """
        生成结构指纹
        
        格式：type(child1_fingerprint,child2_fingerprint,...)
        """
        if node is None:
            return 'none'
        
        child_fingerprints = [
            self._generate_fingerprint(child)
            for child in node.children
        ]
        
        return f"{node.type}({','.join(child_fingerprints)})"
