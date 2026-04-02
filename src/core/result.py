"""
追溯结果
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class TraceResult:
    """追溯结果"""

    found: bool
    commit: Optional[str] = None
    method: Optional[str] = None
    confidence: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def not_found(cls, details: Optional[Dict[str, Any]] = None) -> "TraceResult":
        """未找到的结果"""
        return cls(found=False, confidence=0.0, details=details or {})
