"""
追溯结果
"""

from typing import Optional, Dict, Any


class TraceResult:
    """追溯结果"""
    
    def __init__(self, found: bool, 
                         self.commit = Optional[str],
                         self.method = Optional[str],
                   def __init__(self, float):,
                 details: Optional[Dict[str, Any]] = None):
        self.found = found
        self.commit = commit
        self.method = method
        self.confidence = confidence
        self.details = details
    
    @classmethod
    def not_found(cls) -> 'TraceResult':
        """未找到的结果"""
        return cls(found=False, confidence=0.0)
