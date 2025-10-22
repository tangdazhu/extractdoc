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
        
        # 处理内容行
        for i, line in enumerate(content_lines):
            if i > 0:
                text_frame.add_paragraph()
            
            para = text_frame.paragraphs[i]
            
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
            
            # 添加bullet符号
            bullet = bullet_symbols.get(indent_level, "●")
            para.text = f"{bullet} {clean_line}"
            
            # 设置字体（必须在设置text之后）
            font_size = font_sizes.get(indent_level, 18)
            para.font.size = Pt(font_size)
            para.font.color.rgb = text_color
            if is_bold:
                para.font.bold = True
            
            # 设置段落格式（缩进、行距）
            try:
                pf = para.paragraph_format
                pf.left_indent = Inches(0.3 * indent_level)
                pf.first_line_indent = Inches(0)
                pf.space_before = Pt(0)
                pf.space_after = Pt(6)
                pf.line_spacing = 1.2
            except (AttributeError, TypeError) as e:
                # 某些段落对象可能不支持paragraph_format
                logger.debug(f"段落格式设置失败（可能是特殊段落类型）: {e}")
    
    def _setup_text_frame_margins(self, text_frame):
        """
        统一设置文本框边距
        
        Args:
            text_frame: 文本框对象
        """
        text_frame.word_wrap = True
        text_frame.margin_left = Inches(0.3)
        text_frame.margin_right = Inches(0.3)
        text_frame.margin_top = Inches(0.3)
        
        # 清除第一个段落的默认缩进
        if text_frame.paragraphs:
            try:
                first_para = text_frame.paragraphs[0]
                first_para.space_before = Pt(0)
                first_para.space_after = Pt(0)
            except (AttributeError, TypeError) as e:
                logger.debug(f"第一个段落格式设置失败: {e}")
    
    def save(self, output_path: str):
        """保存PPT"""
        self.prs.save(output_path)
        logger.info(f"PPT已保存: {output_path}")
