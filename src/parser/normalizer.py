"""
AST标准化器
"""

from dataclasses import dataclass
from typing import Dict

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
        self.var_map: Dict[str, str] = {}

    def normalize(self, ast: ASTNode) -> NormalizedAST:
        """标准化AST"""
        self.var_counter = 0
        self.var_map = {}

        normalized_root = self._normalize_node(ast)
        fingerprint = self._generate_fingerprint(normalized_root)

        return NormalizedAST(root=normalized_root, fingerprint=fingerprint, variable_map=self.var_map.copy())

    def _normalize_node(self, node: ASTNode) -> ASTNode:
        """标准化节点"""
        if node is None:
            return ASTNode(type="none")

        metadata = node.metadata.copy()

        if node.type == "Name" and "name" in metadata:
            var_name = str(metadata["name"])
            if var_name not in self.var_map:
                self.var_map[var_name] = f"v{self.var_counter}"
                self.var_counter += 1
            metadata["name"] = self.var_map[var_name]

        if node.type == "FunctionDef" and "name" in metadata:
            func_name = str(metadata["name"])
            if func_name not in self.var_map:
                self.var_map[func_name] = f"f{self.var_counter}"
                self.var_counter += 1
            metadata["name"] = self.var_map[func_name]
        if node.type == "FunctionDef" and "params" in metadata:
            normalized_params = []
            for param_name in metadata["params"]:
                param_name = str(param_name)
                if param_name not in self.var_map:
                    self.var_map[param_name] = f"v{self.var_counter}"
                    self.var_counter += 1
                normalized_params.append(self.var_map[param_name])
            metadata["params"] = normalized_params

        normalized_children = [self._normalize_node(child) for child in node.children]

        return ASTNode(type=node.type, children=normalized_children, metadata=metadata)

    def _generate_fingerprint(self, node: ASTNode) -> str:
        """生成结构指纹"""
        if node is None:
            return "none"

        metadata_items = ",".join(
            f"{key}={repr(node.metadata[key])}" for key in sorted(node.metadata)
        )
        child_fingerprints = [self._generate_fingerprint(child) for child in node.children]
        return f"{node.type}[{metadata_items}]({','.join(child_fingerprints)})"
