# -*- coding: utf-8 -*-
"""
内容解析器

将不同格式的内容解析为适合各种布局的数据结构
"""

import logging
import re
from typing import Dict, List, Tuple
from utils.config_manager import config

logger = logging.getLogger(__name__)


class ContentParser:
    """内容解析器"""
    
    def __init__(self):
        """初始化解析器"""
        logger.info("初始化内容解析器")
    
    def parse_two_column_content(self, content: Dict) -> Tuple[List[str], List[str], str, str]:
        """
        解析左右对比内容
        
        Args:
            content: 内容字典
        
        Returns:
            (left_content, right_content, left_title, right_title)
        """
        title = content.get("title", "")
        lines = content.get("content", [])
        
        logger.debug(f"解析左右对比内容: {title}")
        
        # 尝试从标题中提取左右标题
        left_title, right_title = self._extract_comparison_titles(title)
        
        # 尝试分割内容
        left_content, right_content = self._split_comparison_content(lines)
        
        logger.info(f"解析结果: 左侧{len(left_content)}项, 右侧{len(right_content)}项")
        return left_content, right_content, left_title, right_title
    
    def parse_three_column_content(self, content: Dict) -> List[Dict[str, str]]:
        """
        解析三列卡片内容
        
        Args:
            content: 内容字典
        
        Returns:
            卡片列表 [{"icon": "1", "title": "标题", "content": "内容"}, ...]
        """
        title = content.get("title", "")
        lines = content.get("content", [])
        
        logger.debug(f"解析三列卡片内容: {title}")
        
        cards = []
        current_card = None
        card_index = 0
        
        for line in lines:
            # 主要点作为卡片标题
            if not line.startswith("  "):
                if current_card:
                    cards.append(current_card)
                card_index += 1
                current_card = {
                    "icon": str(card_index),
                    "title": line.strip("- ").strip(),
                    "content": ""
                }
            # 子要点作为卡片内容
            elif current_card:
                content_line = line.strip("  - ").strip()
                if current_card["content"]:
                    current_card["content"] += "\n" + content_line
                else:
                    current_card["content"] = content_line
        
        # 添加最后一张卡片
        if current_card:
            cards.append(current_card)
        
        # 限制最多3张卡片
        cards = cards[:3]
        
        logger.info(f"解析结果: {len(cards)}张卡片")
        return cards
    
    def parse_flow_diagram_content(self, content: Dict) -> List[Dict[str, str]]:
        """
        解析流程图内容
        
        Args:
            content: 内容字典
        
        Returns:
            步骤列表 [{"title": "步骤名", "description": "说明"}, ...]
        """
        title = content.get("title", "")
        lines = content.get("content", [])
        
        logger.debug(f"解析流程图内容: {title}")
        
        steps = []
        current_step = None
        
        for line in lines:
            # 主要点作为步骤标题
            if not line.startswith("  "):
                if current_step:
                    steps.append(current_step)
                
                # 清理箭头符号
                step_title = line.strip("- ").strip()
                step_title = step_title.replace("→", "").replace("->", "").strip()
                
                current_step = {
                    "title": step_title,
                    "description": ""
                }
            # 子要点作为步骤说明
            elif current_step:
                desc_line = line.strip("  - ").strip()
                if current_step["description"]:
                    current_step["description"] += " " + desc_line
                else:
                    current_step["description"] = desc_line
        
        # 添加最后一个步骤
        if current_step:
            steps.append(current_step)
        
        # 从配置读取最大步骤数
        max_steps = config.get("ppt_generation.layout_types.flow_diagram.max_steps", 6)
        if len(steps) > max_steps:
            logger.warning(f"流程图步骤数({len(steps)})超过最大限制({max_steps})，将截断")
            steps = steps[:max_steps]
        
        logger.info(f"解析结果: {len(steps)}个步骤")
        return steps
    
    def parse_timeline_content(self, content: Dict) -> List[Dict[str, str]]:
        """
        解析时间线内容
        
        Args:
            content: 内容字典
        
        Returns:
            时间线项目列表 [{"title": "标题", "content": "内容"}, ...]
        """
        title = content.get("title", "")
        lines = content.get("content", [])
        
        logger.debug(f"解析时间线内容: {title}")
        
        items = []
        current_item = None
        
        for line in lines:
            # 主要点作为时间线标题
            if not line.startswith("  "):
                if current_item:
                    items.append(current_item)
                current_item = {
                    "title": line.strip("- ").strip(),
                    "content": ""
                }
            # 子要点作为时间线内容
            elif current_item:
                content_line = line.strip("  - ").strip()
                if current_item["content"]:
                    current_item["content"] += " " + content_line
                else:
                    current_item["content"] = content_line
        
        # 添加最后一项
        if current_item:
            items.append(current_item)
        
        # 如果没有解析到项目，尝试将所有行作为独立项目
        if not items:
            logger.warning(f"时间线解析失败，尝试将每行作为独立项目")
            for line in lines:
                clean_line = line.strip("- ").strip()
                if clean_line:
                    items.append({
                        "title": clean_line,
                        "content": ""
                    })
        
        # 从配置读取最大项目数
        max_items = config.get("ppt_generation.layout_types.timeline.max_items")
        if len(items) > max_items:
            logger.warning(f"时间线项目数({len(items)})超过最大限制({max_items})，将截断")
            items = items[:max_items]
        
        logger.info(f"解析结果: {len(items)}个时间线项目")
        return items
    
    def _extract_comparison_titles(self, title: str) -> Tuple[str, str]:
        """从标题中提取左右对比的标题"""
        # 尝试匹配 "A vs B" 或 "A对比B" 格式
        patterns = [
            r"(.+?)\s*vs\s*(.+)",
            r"(.+?)\s*对比\s*(.+)",
            r"(.+?)\s*与\s*(.+)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, title, re.IGNORECASE)
            if match:
                left = match.group(1).strip()
                right = match.group(2).strip()
                logger.debug(f"提取对比标题: '{left}' vs '{right}'")
                return left, right
        
        # 默认标题
        return "传统方式", "AI方式"
    
    def _split_comparison_content(self, lines: List[str]) -> Tuple[List[str], List[str]]:
        """分割左右对比内容"""
        # 从配置读取文本长度限制
        max_text_length = config.get("ppt_generation.layout_types.two_column.max_text_length", 60)
        
        # 提取所有要点（包括主要点和子要点）
        all_points = []
        for line in lines:
            clean_line = line.strip("- ").strip()
            if clean_line:
                # 限制每个要点长度，避免大段文字
                if len(clean_line) > max_text_length:
                    # 尝试在句号处分割
                    sentences = clean_line.split("。")
                    for sent in sentences[:2]:  # 最多取前2句
                        if sent.strip():
                            all_points.append(sent.strip() + "。")
                else:
                    all_points.append(clean_line)
        
        # 平均分配到左右两侧
        mid = len(all_points) // 2
        left_content = all_points[:mid] if mid > 0 else all_points
        right_content = all_points[mid:] if mid > 0 else []
        
        # 确保至少有内容
        if not left_content and not right_content:
            left_content = ["内容待补充"]
            right_content = ["内容待补充"]
        elif not right_content:
            right_content = left_content[-1:]
            left_content = left_content[:-1]
        
        return left_content, right_content
