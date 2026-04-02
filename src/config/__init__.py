"""
配置管理模块
"""

from pathlib import Path
from typing import Any, Dict, Optional

import yaml


class Config:
    """配置管理"""

    def __init__(self, config_dict: Optional[Dict[str, Any]] = None):
        self.config = config_dict or {}

    @classmethod
    def from_file(cls, config_path: str) -> "Config":
        """从文件加载配置"""
        path = Path(config_path)
        if not path.exists():
            return cls.default()

        with open(path, "r", encoding="utf-8") as f:
            config_dict = yaml.safe_load(f) or {}

        return cls(config_dict)

    @classmethod
    def default(cls) -> "Config":
        """默认配置"""
        return cls(
            {
                "cache_path": "~/.coderipple/cache",
                "similarity_threshold": 0.85,
                "log_level": "INFO",
            }
        )

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项"""
        keys = key.split(".")
        value = self.config

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default

        return value if value is not None else default

    def get_cache_path(self) -> Path:
        """获取缓存路径"""
        cache_path = self.get("cache_path", "~/.coderipple/cache")
        return Path(cache_path).expanduser()

    def get_similarity_threshold(self) -> float:
        """获取相似度阈值"""
        return float(self.get("similarity_threshold", 0.85))
