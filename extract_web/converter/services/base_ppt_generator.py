# -*- coding: utf-8 -*-
"""
PPT生成器基类

提供通用的PPT生成功能，避免代码重复
"""

import logging
from typing import List, Dict, Tuple
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.dml.color import RGBColor
from utils.config_manager import config

logger = logging.getLogger(__name__)


class BasePPTGenerator:
    """PPT生成器基类"""
    
    def __init__(self):
        """初始化基类"""
        self.prs = Presentation()
        self.prs.slide_width = Inches(13.33)
        self.prs.slide_height = Inches(7.5)
    
    def _clean_markdown_text(self, text: str) -> Tuple[str, bool]:
        """
        清理Markdown标记
        
        Args:
            text: 原始文本
            
        Returns:
            (清理后的文本, 是否加粗)
        """
        is_bold = False
        
        # 处理加粗标记
        if text.startswith("**") and text.endswith("**") and len(text) > 4:
            text = text[2:-2]
            is_bold = True
        
        # 移除其他Markdown标记
        text = text.replace("*", "").replace("_", "")
        
        return text, is_bold
    
    def _add_bullet_content(self, text_frame, content_lines: List[str], font_sizes: Dict[int, int], text_color: RGBColor):
        """
        统一添加带bullet的内容（避免重复代码）
        
        Args:
            text_frame: 文本框对象
            content_lines: 内容行列表
            font_sizes: 字体大小映射 {indent_level: font_size}
            text_color: 文字颜色
        """
        # 从配置读取bullet符号
        bullet_symbols = {
            0: config.get("text_formatting.bullet_level_0", "●"),
            1: config.get("text_formatting.bullet_level_1", "○"),
            2: config.get("text_formatting.bullet_level_2", "▪")
        }
        
        # 清空第一个默认段落，但不使用它
        # PowerPoint的第一个默认段落有无法修改的缩进
        if text_frame.paragraphs:
            first_para = text_frame.paragraphs[0]
            first_para.text = ""  # 清空但保留
        
        logger.debug(f"[缩进修复] 开始添加{len(content_lines)}行内容")
        
        # 处理内容行 - 所有段落都用add_paragraph创建（跳过第一个默认段落）
        for i, line in enumerate(content_lines):
            # 所有段落都通过add_paragraph创建，避免使用默认段落
            para = text_frame.add_paragraph()
            
            # 检测缩进层级
            indent_level = 0
            clean_line = line
            if line.startswith("  - "):
                indent_level = 1
                clean_line = line[4:]
            elif line.startswith("- "):
                indent_level = 0
                clean_line = line[2:]
            elif line.startswith("• "):
                indent_level = 0
                clean_line = line[2:]
            
            # 清理Markdown标记
            clean_line, is_bold = self._clean_markdown_text(clean_line)
            
            # 添加bullet符号（不添加空格，让PowerPoint的默认缩进作为左边距）
            bullet = bullet_symbols.get(indent_level, "●")
            # 1级缩进使用4个空格
            indent_spaces = "    " if indent_level == 1 else ""
            para.text = f"{indent_spaces}{bullet} {clean_line}"
            
            if i == 0:
                logger.debug(f"[缩进修复] 第一行文本: '{para.text[:30]}...'")
            
            # 设置字体（必须在设置text之后）
            font_size = font_sizes.get(indent_level, 18)
            para.font.size = Pt(font_size)
            para.font.color.rgb = text_color
            if is_bold:
                para.font.bold = True
            
            # 不设置para.level！它会自动添加缩进
            # 如果需要缩进，通过在文本前添加空格实现
            # （因为paragraph_format不可用）
    
    def _setup_text_frame_margins(self, text_frame):
        """
        统一设置文本框边距
        
        Args:
            text_frame: 文本框对象
        """
        text_frame.word_wrap = True
        text_frame.margin_left = Inches(0)  # 完全去除左边距
        text_frame.margin_right = Inches(0.2)
        text_frame.margin_top = Inches(0.2)
        text_frame.margin_bottom = Inches(0.2)
        logger.debug(f"[缩进修复] 文本框边距设置: left=0, right=0.2, top=0.2")
    
    def _get_three_column_config(self) -> Dict:
        """获取三列卡片配置"""
        return {
            "max_cards": config.get("ppt_generation.layout_types.three_column.max_cards"),
            "card_width": config.get("ppt_generation.layout_types.three_column.card_width"),
            "card_gap": config.get("ppt_generation.layout_types.three_column.card_gap"),
            "card_title_font_size": config.get("ppt_generation.layout_types.three_column.card_title_font_size"),
            "card_content_font_size": config.get("ppt_generation.layout_types.three_column.card_content_font_size"),
            "card_content_max_chars": config.get("ppt_generation.layout_types.three_column.card_content_max_chars")
        }
    
    def _get_timeline_config(self) -> Dict:
        """获取时间线配置"""
        return {
            "max_items": config.get("ppt_generation.layout_types.timeline.max_items"),
            "base_item_height": config.get("ppt_generation.layout_types.timeline.base_item_height"),
            "min_item_height": config.get("ppt_generation.layout_types.timeline.min_item_height"),
            "available_height": config.get("ppt_generation.layout_types.timeline.available_height"),
            "start_y": config.get("ppt_generation.layout_types.timeline.start_y"),
            "title_font_size": config.get("ppt_generation.layout_types.timeline.title_font_size"),
            "content_font_size": config.get("ppt_generation.layout_types.timeline.content_font_size"),
            "content_max_chars": config.get("ppt_generation.layout_types.timeline.content_max_chars")
        }
    
    def _truncate_text_smart(self, text: str, max_chars: int) -> str:
        """智能截断文本：优先在标点符号处截断"""
        if len(text) <= max_chars:
            return text
        
        truncate_pos = int(max_chars * 0.9)
        for j in range(truncate_pos, max(truncate_pos - 10, 0), -1):
            if j < len(text) and text[j] in '。，、；':
                return text[:j+1]
        
        return text[:truncate_pos] + "..."
    
    def _calculate_timeline_layout(self, item_count: int, cfg: Dict) -> Tuple[float, int, int, int]:
        """计算时间线动态布局参数
        
        Returns:
            (item_height, title_font_size, content_font_size, content_max_chars)
        """
        if item_count > 0:
            calculated_height = cfg["available_height"] / item_count
            item_height = max(cfg["min_item_height"], min(calculated_height, cfg["base_item_height"]))
        else:
            item_height = cfg["base_item_height"]
        
        title_font_size = cfg["title_font_size"]
        content_font_size = cfg["content_font_size"]
        content_max_chars = cfg["content_max_chars"]
        
        # 根据高度调整字体大小
        if item_height < 1.0:
            title_font_size = int(title_font_size * 0.85)
            content_font_size = int(content_font_size * 0.85)
            content_max_chars = int(content_max_chars * 0.8)
        
        return item_height, title_font_size, content_font_size, content_max_chars
    
    def save(self, output_path: str):
        """保存PPT"""
        self.prs.save(output_path)
        logger.info(f"PPT已保存: {output_path}")
