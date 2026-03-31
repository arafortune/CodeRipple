"""
AST解析器
"""

import ast
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class ASTNode:
    """AST节点"""
    type: str
    children: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


class ASTParser:
    """AST解析器"""
    
    def __init__(self, language: str = 'python'):
        self.language = language
    
    def parse(self, code: str) -> Optional[ASTNode]:
        """
        解析代码为AST
        
        Args:
            code: 代码字符串
            
        Returns:
            AST根节点
        """
        if not code.strip():
            return ASTNode(type='empty')
        
        try:
            if self.language == 'python':
                return self._parse_python(code)
            else:
                raise ValueError(f"Unsupported language: {self.language}")
        except SyntaxError as e:
            raise Exception(f"Syntax error: {e}")
    
    def _parse_python(self, code: str) -> ASTNode:
        """解析Python代码"""
        tree = ast.parse(code)
        return self._convert_ast_node(tree)
    
    def _convert_ast_node(self, node: ast.AST) -> ASTNode:
        """将Python AST节点转换为通用AST节点"""
        if node is None:
            return ASTNode(type='none')
        
        node_type = node.__class__.__name__
        metadata = {}
        children = []
        
        # 提取元数据
        if isinstance(node, ast.FunctionDef):
            metadata['name'] = node.name
            if node.args:
                metadata['params'] = [arg.arg for arg in node.args.args]
        
        elif isinstance(node, ast.Name):
            metadata['name'] = node.id
        
        elif isinstance(node, ast.Constant):
            metadata['value'] = node.value
        
        elif isinstance(node, ast.Return):
            if node.value:
                metadata['has_value'] = True
        
        elif isinstance(node, ast.Assign):
            if node.targets:
                metadata['targets'] = [self._get_name(t) for t in node.targets]
        
        elif isinstance(node, ast.BinOp):
            metadata['op'] = node.op.__class__.__name__
        
        elif isinstance(node, ast.If):
            metadata['has_else'] = node.orelse != []
        
        elif isinstance(node, ast.For):
            metadata['has_else'] = node.orelse != []
        
        elif isinstance(node, ast.While):
            metadata['has_else'] = node.orelse != []
        
        # 递归处理子节点
        for field_name, field_value in ast.iter_fields(node):
            if field_name in ['ctx', 'type_comment']:
                continue
            
            if isinstance(field_value, list):
                for item in field_value:
                    if isinstance(item, ast.AST):
                        children.append(self._convert_ast_node(item))
            elif isinstance(field_value, ast.AST):
                children.append(self._convert_ast_node(field_value))
        
        return ASTNode(
            type=node_type,
            children=children,
            metadata=metadata
        )
    
    def _get_name(self, node: ast.AST) -> Optional[str]:
        """获取节点名称"""
        if isinstance(node, ast.Name):
            return node.id
        return None
