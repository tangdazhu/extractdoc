# -*- coding: utf-8 -*-
"""
统一配置管理器

负责加载和管理所有应用配置，提供统一的配置访问接口。
"""

import yaml
import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class ConfigManager:
    """
    统一配置管理器（单例模式）
    
    用法:
        from utils.config_manager import config
        
        # 获取配置值
        model = config.get("ai_document_analysis.model")
        
        # 获取配置节
        word_config = config.get_section("word_generation")
    """
    
    _instance = None
    _config = None
    
    def __new__(cls):
        """单例模式：确保全局只有一个配置管理器实例"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """初始化配置管理器"""
        if self._config is None:
            self.load_config()
    
    def load_config(self, config_path: Optional[str] = None):
        """
        加载配置文件
        
        Args:
            config_path: 配置文件路径，默认为 config/application.yaml
        """
        if config_path is None:
            # 默认配置文件路径
            base_dir = Path(__file__).parent.parent
            config_path = base_dir / "config" / "application.yaml"
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f)
            logger.info("配置文件加载成功: %s", config_path)
        except FileNotFoundError:
            logger.error("配置文件不存在: %s", config_path)
            self._config = {}
            raise
        except Exception as e:
            logger.error("配置文件加载失败: %s", e)
            self._config = {}
            raise
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        获取配置值（支持点号路径）
        
        Args:
            key_path: 配置键路径，如 "ai_document_analysis.model"
            default: 默认值
        
        Returns:
            配置值，如果不存在则返回默认值
        
        Examples:
            >>> config = ConfigManager()
            >>> config.get("ai_document_analysis.model")
            'qwen-max'
            >>> config.get("word_generation.font_sizes.title")
            24
            >>> config.get("non_existent.key", "default_value")
            'default_value'
        """
        if self._config is None:
            logger.warning("配置未加载，返回默认值")
            return default
        
        keys = key_path.split('.')
        value = self._config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """
        获取配置节
        
        Args:
            section: 配置节名称，如 "word_generation"
        
        Returns:
            配置节字典，如果不存在则返回空字典
        
        Examples:
            >>> config = ConfigManager()
            >>> word_config = config.get_section("word_generation")
            >>> word_config["font_sizes"]["title"]
            24
        """
        return self.get(section, {})
    
    def reload(self):
        """重新加载配置文件"""
        self._config = None
        self.load_config()
    
    def get_all(self) -> Dict[str, Any]:
        """
        获取所有配置
        
        Returns:
            完整的配置字典
        """
        return self._config or {}
    
    def exists(self, key_path: str) -> bool:
        """
        检查配置键是否存在
        
        Args:
            key_path: 配置键路径
        
        Returns:
            如果配置键存在返回True，否则返回False
        """
        if self._config is None:
            return False
        
        keys = key_path.split('.')
        value = self._config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return False
        
        return True


# 全局配置实例（单例）
config = ConfigManager()


# 便捷函数
def get_config(key_path: str, default: Any = None) -> Any:
    """
    获取配置值的便捷函数
    
    Args:
        key_path: 配置键路径
        default: 默认值
    
    Returns:
        配置值
    """
    return config.get(key_path, default)


def get_config_section(section: str) -> Dict[str, Any]:
    """
    获取配置节的便捷函数
    
    Args:
        section: 配置节名称
    
    Returns:
        配置节字典
    """
    return config.get_section(section)
