"""
追溯结果
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class TraceResult:
    """追溯结果"""
    found: bool
    commit: Optional[str] = None
    method: Optional[str] = None
    confidence: float = 0.0
    details: Optional[Dict[str, Any]] = None
    
    @classmethod
    def not_found(cls) -> 'TraceResult':
        """未找到的结果"""
        return cls(found=False, confidence=0.0)
