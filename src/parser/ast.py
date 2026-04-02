"""
AST解析器
"""

import ast
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ASTNode:
    """AST节点"""

    type: str
    children: List["ASTNode"] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ASTParser:
    """AST解析器"""

    def __init__(self, language: str = "python"):
        self.language = language

    def parse(self, code: str) -> Optional[ASTNode]:
        """解析代码为AST"""
        if not code.strip():
            return ASTNode(type="Module", children=[], metadata={})

        try:
            if self.language == "python":
                return self._parse_python(code)
            raise ValueError(f"Unsupported language: {self.language}")
        except SyntaxError as e:
            raise Exception(f"Syntax error: {e}")

    def _parse_python(self, code: str) -> ASTNode:
        """解析Python代码"""
        tree = ast.parse(code)
        return self._convert_ast_node(tree)

    def extract_relevant_snippet(self, code: str, changed_lines: List[int]) -> str:
        """提取包含变更行的最小函数/类代码片段"""
        if self.language != "python" or not code.strip() or not changed_lines:
            return code

        tree = ast.parse(code)
        target_node = self._find_smallest_enclosing_node(tree, changed_lines)
        if target_node is None:
            return code

        snippet = ast.get_source_segment(code, target_node)
        return snippet or code

    def _find_smallest_enclosing_node(
        self, tree: ast.AST, changed_lines: List[int]
    ) -> Optional[ast.AST]:
        """找到包含变更行的最小函数/类节点"""
        relevant_nodes: List[ast.AST] = []

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            start = getattr(node, "lineno", None)
            end = getattr(node, "end_lineno", None)
            if start is None or end is None:
                continue
            if any(start <= line <= end for line in changed_lines):
                relevant_nodes.append(node)

        if not relevant_nodes:
            return None

        return min(
            relevant_nodes,
            key=lambda node: (getattr(node, "end_lineno", 0) - getattr(node, "lineno", 0), getattr(node, "lineno", 0)),
        )

    def _convert_ast_node(self, node: ast.AST) -> ASTNode:
        """将Python AST节点转换为通用AST节点"""
        if node is None:
            return ASTNode(type="none")

        node_type = node.__class__.__name__
        metadata: Dict[str, Any] = {}
        children: List[ASTNode] = []

        if isinstance(node, ast.FunctionDef):
            metadata["name"] = node.name
            metadata["params"] = [arg.arg for arg in node.args.args]
        elif isinstance(node, ast.Name):
            metadata["name"] = node.id
        elif isinstance(node, ast.Constant):
            metadata["value"] = node.value
        elif isinstance(node, ast.Return):
            metadata["has_value"] = node.value is not None
        elif isinstance(node, ast.Assign):
            metadata["targets"] = len(node.targets)
        elif isinstance(node, ast.BinOp):
            metadata["op"] = node.op.__class__.__name__
        elif isinstance(node, ast.If):
            metadata["has_else"] = bool(node.orelse)
        elif isinstance(node, ast.For):
            metadata["has_else"] = bool(node.orelse)
        elif isinstance(node, ast.While):
            metadata["has_else"] = bool(node.orelse)

        for field_name, field_value in ast.iter_fields(node):
            if field_name in ["ctx", "type_comment"]:
                continue

            if isinstance(field_value, list):
                for item in field_value:
                    if isinstance(item, ast.AST):
                        children.append(self._convert_ast_node(item))
            elif isinstance(field_value, ast.AST):
                children.append(self._convert_ast_node(field_value))

        return ASTNode(type=node_type, children=children, metadata=metadata)
