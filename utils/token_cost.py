# -*- coding: utf-8 -*-
"""
Token费用计算工具

通用的Token使用费用计算工具，支持多种AI模型
从配置文件读取模型定价，避免硬编码
"""

import logging
from typing import Optional

from .config_manager import config

logger = logging.getLogger(__name__)


class TokenCostCalculator:
    """
    Token费用计算器
    
    从配置文件读取模型定价，计算Token使用费用
    """
    
    @staticmethod
    def get_model_pricing(model: str) -> Optional[dict]:
        """
        从配置文件获取模型定价
        
        Args:
            model: 模型名称（如 qwen-max）
            
        Returns:
            定价字典 {"input": 0.006, "output": 0.024}，如果未配置返回None
        """
        pricing_config = config.get("ai_document_analysis.pricing", {})
        
        if model in pricing_config:
            return pricing_config[model]
        
        # 如果没有找到精确匹配，尝试模糊匹配（如 qwen-max-0301 匹配 qwen-max）
        for config_model, pricing in pricing_config.items():
            if model.startswith(config_model):
                logger.debug(f"模型 {model} 使用 {config_model} 的定价")
                return pricing
        
        logger.warning(f"未找到模型 {model} 的定价配置")
        return None
    
    @staticmethod
    def calculate_cost(
        input_tokens: int, 
        output_tokens: int, 
        model: Optional[str] = None
    ) -> float:
        """
        计算Token使用费用
        
        Args:
            input_tokens: 输入Token数量
            output_tokens: 输出Token数量
            model: 模型名称，如果为None则从配置读取当前模型
            
        Returns:
            费用（元），保留4位小数
        """
        # 如果没有指定模型，从配置读取当前使用的模型
        if model is None:
            model = config.get("ai_document_analysis.model", "qwen-max")
        
        # 获取模型定价
        pricing = TokenCostCalculator.get_model_pricing(model)
        
        if pricing is None:
            logger.error(f"无法计算费用：模型 {model} 未配置定价")
            return 0.0
        
        # 计算费用（Token数 / 1000 * 单价）
        input_cost = (input_tokens / 1000) * pricing["input"]
        output_cost = (output_tokens / 1000) * pricing["output"]
        total_cost = input_cost + output_cost
        
        return round(total_cost, 4)
    
    @staticmethod
    def format_cost(cost: float) -> str:
        """
        格式化费用显示
        
        Args:
            cost: 费用（元）
            
        Returns:
            格式化的费用字符串
        """
        if cost == 0:
            return "0元"
        elif cost < 0.01:
            # 小于1分，显示为"<0.01元"
            return "<0.01元"
        else:
            # 显示2位小数
            return f"{cost:.2f}元"
    
    @staticmethod
    def calculate_and_format(
        input_tokens: int, 
        output_tokens: int, 
        model: Optional[str] = None
    ) -> str:
        """
        计算并格式化费用
        
        Args:
            input_tokens: 输入Token数量
            output_tokens: 输出Token数量
            model: 模型名称，如果为None则从配置读取
            
        Returns:
            格式化的费用字符串
        """
        cost = TokenCostCalculator.calculate_cost(input_tokens, output_tokens, model)
        return TokenCostCalculator.format_cost(cost)
    
    @staticmethod
    def get_current_model() -> str:
        """
        获取当前配置的模型名称
        
        Returns:
            模型名称
        """
        return config.get("ai_document_analysis.model", "qwen-max")
    
    @staticmethod
    def get_all_models() -> list:
        """
        获取所有已配置定价的模型列表
        
        Returns:
            模型名称列表
        """
        pricing_config = config.get("ai_document_analysis.pricing", {})
        return list(pricing_config.keys())
    
    @staticmethod
    def get_pricing_info(model: Optional[str] = None) -> str:
        """
        获取模型定价信息的可读字符串
        
        Args:
            model: 模型名称，如果为None则使用当前模型
            
        Returns:
            定价信息字符串
        """
        if model is None:
            model = TokenCostCalculator.get_current_model()
        
        pricing = TokenCostCalculator.get_model_pricing(model)
        
        if pricing is None:
            return f"模型 {model} 未配置定价"
        
        return f"模型 {model} 定价: 输入={pricing['input']}元/千Token, 输出={pricing['output']}元/千Token"
