# -*- coding: utf-8 -*-
"""
布局检测器

根据内容特征自动选择最合适的PPT布局类型
"""

import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


class LayoutDetector:
    """布局类型检测器"""
    
    # 关键词定义
    COMPARISON_KEYWORDS = [
        "vs", "对比", "比较", "传统", "AI", "新旧", "前后",
        "优势", "劣势", "差异", "区别", "对照"
    ]
    
    THREE_ELEMENT_KEYWORDS = [
        "三大", "三个", "三种", "三项", "三方面",
        "三要素", "三点", "三步"
    ]
    
    FLOW_KEYWORDS = [
        "流程", "步骤", "阶段", "过程", "环节",
        "→", "->", "然后", "接着", "最后",
        "第一步", "第二步", "第三步", "第四步"
    ]
    
    TIMELINE_KEYWORDS = [
        "趋势", "未来", "发展", "演进", "历程",
        "路线图", "历史", "变迁", "进程", "阶段性"
    ]
    
    def __init__(self):
        """初始化检测器"""
        logger.info("初始化布局检测器")
    
    def detect_layout_type(self, content: Dict) -> str:
        """
        根据内容特征自动选择布局类型
        
        Args:
            content: 内容字典，包含:
                - title: 标题
                - content: 内容列表
                - type: 内容类型提示（可选）
        
        Returns:
            布局类型: "two_column", "three_column", "flow_diagram", 
                     "timeline", "bullet_list"
        """
        title = content.get("title", "")
        content_lines = content.get("content", [])
        content_type = content.get("type", "")
        
        # 合并所有文本用于分析
        all_text = title + " " + " ".join(content_lines) + " " + content_type
        
        logger.debug(f"检测布局类型: title='{title}', lines={len(content_lines)}")
        
        # 1. 检测对比关系（优先级最高）
        if self._has_comparison(all_text, content_lines):
            logger.info(f"检测到对比布局: {title}")
            return "two_column"
        
        # 2. 检测三要素
        if self._has_three_elements(title, content_lines):
            logger.info(f"检测到三列卡片布局: {title}")
            return "three_column"
        
        # 3. 检测流程
        if self._has_flow(all_text, content_lines):
            logger.info(f"检测到流程图布局: {title}")
            return "flow_diagram"
        
        # 4. 检测时间线
        if self._has_timeline(title, all_text):
            logger.info(f"检测到时间线布局: {title}")
            return "timeline"
        
        # 5. 默认：bullet list
        logger.debug(f"使用默认bullet list布局: {title}")
        return "bullet_list"
    
    def _has_comparison(self, text: str, lines: List[str]) -> bool:
        """检测是否包含对比关系"""
        # 检查关键词
        if any(kw in text for kw in self.COMPARISON_KEYWORDS):
            return True
        
        # 检查是否有明显的左右结构（如包含"vs"或"对比"）
        if "vs" in text.lower() or "对比" in text:
            return True
        
        return False
    
    def _has_three_elements(self, title: str, lines: List[str]) -> bool:
        """检测是否为三要素结构"""
        # 检查标题中的三要素关键词
        if any(kw in title for kw in self.THREE_ELEMENT_KEYWORDS):
            return True
        
        # 检查是否恰好有3个主要要点
        main_points = [line for line in lines if not line.startswith("  ")]
        if len(main_points) == 3:
            return True
        
        return False
    
    def _has_flow(self, text: str, lines: List[str]) -> bool:
        """检测是否为流程结构"""
        # 检查流程关键词
        if any(kw in text for kw in self.FLOW_KEYWORDS):
            return True
        
        # 检查是否有箭头符号
        if "→" in text or "->" in text:
            return True
        
        # 检查是否有步骤编号
        step_patterns = ["第一", "第二", "第三", "第四", "步骤1", "步骤2"]
        if any(pattern in text for pattern in step_patterns):
            return True
        
        return False
    
    def _has_timeline(self, title: str, text: str) -> bool:
        """检测是否为时间线结构"""
        # 检查时间线关键词（主要在标题中）
        if any(kw in title for kw in self.TIMELINE_KEYWORDS):
            return True
        
        # 检查是否包含时间相关词汇
        time_words = ["过去", "现在", "未来", "早期", "中期", "后期"]
        if any(word in text for word in time_words):
            return True
        
        return False
