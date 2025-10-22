# -*- coding: utf-8 -*-
"""
商务风格PPT生成器

专业的商务设计风格，动态生成精美的PPT页面
蓝色配色方案，适合商务汇报、产品介绍
"""
import logging
from typing import List, Dict, Any, Optional
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from utils.config_manager import config

logger = logging.getLogger(__name__)


class BusinessStylePPTGenerator:
    """
    商务风格PPT生成器
    
    设计特点:
    - 蓝色渐变背景
    - 白色内容区域
    - 圆角装饰元素
    - 清晰的视觉层次
    """
    
    # 配色方案
    COLOR_PRIMARY_DARK = RGBColor(1, 93, 187)  # 深蓝
    COLOR_PRIMARY_LIGHT = RGBColor(100, 180, 255)  # 浅蓝
    COLOR_WHITE = RGBColor(255, 255, 255)
    COLOR_TEXT_DARK = RGBColor(50, 50, 50)
    COLOR_TEXT_LIGHT = RGBColor(200, 200, 200)
    
    def __init__(self):
        """初始化生成器"""
        self.prs = Presentation()
        self.prs.slide_width = Inches(13.33)  # 16:9
        self.prs.slide_height = Inches(7.5)
        logger.info("初始化商务风格PPT生成器")
    
    def _clean_markdown_text(self, text: str) -> tuple:
        """
        清理Markdown格式标记
        
        Args:
            text: 原始文本（可能包含**加粗**标记）
        
        Returns:
            (清理后的文本, 是否加粗)
        """
        import re
        
        # 检测是否有加粗标记
        is_bold = '**' in text
        
        # 移除加粗标记 **文本**
        cleaned_text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
        
        # 移除单个星号 *文本*
        cleaned_text = re.sub(r'\*(.+?)\*', r'\1', cleaned_text)
        
        return cleaned_text, is_bold
    
    def _add_gradient_background(self, slide, angle=135.0):
        """添加渐变背景"""
        background = slide.background
        fill = background.fill
        fill.gradient()
        fill.gradient_angle = angle
        fill.gradient_stops[0].color.rgb = self.COLOR_PRIMARY_DARK
        fill.gradient_stops[1].color.rgb = self.COLOR_PRIMARY_LIGHT
    
    def _add_decorative_dots(self, slide, x=11, y=0.5, rows=6, cols=6):
        """添加装饰圆点"""
        for i in range(cols):
            for j in range(rows):
                dot = slide.shapes.add_shape(
                    MSO_SHAPE.OVAL,
                    Inches(x + i*0.15), Inches(y + j*0.15),
                    Inches(0.08), Inches(0.08)
                )
                dot.fill.solid()
                dot.fill.fore_color.rgb = self.COLOR_WHITE
                dot.fill.fore_color.brightness = -0.5
                dot.line.fill.background()
    
    def create_cover_slide(self, title: str, subtitle: str = "", 
                          reporter: str = "", date: str = ""):
        """
        创建封面页
        
        Args:
            title: 主标题
            subtitle: 副标题
            reporter: 汇报人
            date: 日期
        """
        slide = self.prs.slides.add_slide(self.prs.slide_layouts[6])  # 空白布局
        self._add_gradient_background(slide)
        self._add_decorative_dots(slide)
        
        # 主标题
        title_box = slide.shapes.add_textbox(
            Inches(1.5), Inches(2.5),
            Inches(10), Inches(1.5)
        )
        title_frame = title_box.text_frame
        title_frame.text = title
        title_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
        title_frame.paragraphs[0].font.size = Pt(66)
        title_frame.paragraphs[0].font.bold = True
        title_frame.paragraphs[0].font.color.rgb = self.COLOR_WHITE
        
        # 副标题
        if subtitle:
            subtitle_box = slide.shapes.add_textbox(
                Inches(2), Inches(4.2),
                Inches(9.33), Inches(0.6)
            )
            subtitle_frame = subtitle_box.text_frame
            subtitle_frame.text = subtitle
            subtitle_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
            subtitle_frame.paragraphs[0].font.size = Pt(24)
            subtitle_frame.paragraphs[0].font.color.rgb = self.COLOR_WHITE
        
        # 汇报人信息框
        if reporter:
            reporter_shape = slide.shapes.add_shape(
                MSO_SHAPE.ROUNDED_RECTANGLE,
                Inches(2.5), Inches(6),
                Inches(3), Inches(0.4)
            )
            reporter_shape.fill.solid()
            reporter_shape.fill.fore_color.rgb = self.COLOR_WHITE
            reporter_shape.fill.fore_color.brightness = -0.3
            reporter_shape.line.fill.background()
            
            reporter_text = reporter_shape.text_frame
            reporter_text.text = f"汇报人: {reporter}"
            reporter_text.paragraphs[0].alignment = PP_ALIGN.CENTER
            reporter_text.paragraphs[0].font.size = Pt(18)
            reporter_text.paragraphs[0].font.color.rgb = self.COLOR_WHITE
        
        # 日期信息框
        if date:
            date_shape = slide.shapes.add_shape(
                MSO_SHAPE.ROUNDED_RECTANGLE,
                Inches(7.5), Inches(6),
                Inches(3), Inches(0.4)
            )
            date_shape.fill.solid()
            date_shape.fill.fore_color.rgb = self.COLOR_WHITE
            date_shape.fill.fore_color.brightness = -0.3
            date_shape.line.fill.background()
            
            date_text = date_shape.text_frame
            date_text.text = f"日期: {date}"
            date_text.paragraphs[0].alignment = PP_ALIGN.CENTER
            date_text.paragraphs[0].font.size = Pt(18)
            date_text.paragraphs[0].font.color.rgb = self.COLOR_WHITE
        
        logger.info(f"创建封面页: {title}")
    
    def create_content_slide(self, title: str, content_lines: List[str]):
        """
        创建内容页
        
        Args:
            title: 页面标题
            content_lines: 内容行列表
        """
        slide = self.prs.slides.add_slide(self.prs.slide_layouts[6])
        self._add_gradient_background(slide)
        
        # 标题栏（白色背景）
        title_bar = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE,
            0, 0,
            Inches(13.33), Inches(1.2)
        )
        title_bar.fill.solid()
        title_bar.fill.fore_color.rgb = self.COLOR_WHITE
        title_bar.line.fill.background()
        
        # 标题文字
        title_text = title_bar.text_frame
        title_text.text = title
        title_text.paragraphs[0].font.size = Pt(36)
        title_text.paragraphs[0].font.bold = True
        title_text.paragraphs[0].font.color.rgb = self.COLOR_PRIMARY_DARK
        title_text.vertical_anchor = MSO_ANCHOR.MIDDLE
        title_text.margin_left = Inches(0.5)
        
        # 内容区域（白色背景）
        content_box = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE,
            Inches(0.8), Inches(1.8),
            Inches(11.73), Inches(5)
        )
        content_box.fill.solid()
        content_box.fill.fore_color.rgb = self.COLOR_WHITE
        content_box.line.fill.background()
        
        # 内容文字
        content_text = content_box.text_frame
        content_text.word_wrap = True
        content_text.margin_left = Inches(0.5)
        content_text.margin_right = Inches(0.5)
        content_text.margin_top = Inches(0.3)
        
        # 处理内容行
        for i, line in enumerate(content_lines):
            if i > 0:
                content_text.add_paragraph()
            
            para = content_text.paragraphs[i]
            
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
            
            para.text = clean_line
            para.level = indent_level
            para.font.size = Pt(20 if indent_level == 0 else 18)
            para.font.color.rgb = self.COLOR_TEXT_DARK
            
            # 加粗处理
            if is_bold:
                para.font.bold = True
        
        logger.debug(f"创建内容页: {title} ({len(content_lines)}行)")
    
    def create_section_slide(self, number: str, title: str):
        """
        创建章节分隔页
        
        Args:
            number: 章节编号（如 "01"）
            title: 章节标题
        """
        slide = self.prs.slides.add_slide(self.prs.slide_layouts[6])
        self._add_gradient_background(slide)
        self._add_decorative_dots(slide, x=1, y=1)
        
        # 大号数字
        number_box = slide.shapes.add_textbox(
            Inches(3), Inches(2),
            Inches(7.33), Inches(2)
        )
        number_frame = number_box.text_frame
        number_frame.text = number
        number_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
        number_frame.paragraphs[0].font.size = Pt(120)
        number_frame.paragraphs[0].font.bold = True
        number_frame.paragraphs[0].font.color.rgb = self.COLOR_WHITE
        
        # 章节标题
        section_title = slide.shapes.add_textbox(
            Inches(3), Inches(4.2),
            Inches(7.33), Inches(1)
        )
        section_frame = section_title.text_frame
        section_frame.text = title
        section_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
        section_frame.paragraphs[0].font.size = Pt(48)
        section_frame.paragraphs[0].font.bold = True
        section_frame.paragraphs[0].font.color.rgb = self.COLOR_WHITE
        
        logger.debug(f"创建章节页: {number} - {title}")
    
    def create_catalog_slide(self, catalog_items: List[Dict[str, str]]):
        """
        创建目录页
        
        Args:
            catalog_items: 目录项列表，每项包含 {"number": "01", "title": "标题"}
        """
        slide = self.prs.slides.add_slide(self.prs.slide_layouts[6])
        self._add_gradient_background(slide)
        self._add_decorative_dots(slide, x=10.5, y=0.3)
        self._add_decorative_dots(slide, x=10.5, y=5.5)
        
        # 左侧标题区域
        title_box = slide.shapes.add_textbox(
            Inches(0.8), Inches(0.7),
            Inches(2.5), Inches(1.2)
        )
        title_frame = title_box.text_frame
        title_frame.text = "目录"
        title_frame.paragraphs[0].font.size = Pt(54)
        title_frame.paragraphs[0].font.bold = True
        title_frame.paragraphs[0].font.color.rgb = self.COLOR_PRIMARY_DARK
        
        # "CONTENTS" 副标题
        subtitle_box = slide.shapes.add_textbox(
            Inches(2.8), Inches(1.1),
            Inches(3), Inches(0.5)
        )
        subtitle_frame = subtitle_box.text_frame
        subtitle_frame.text = "CONTENTS"
        subtitle_frame.paragraphs[0].font.size = Pt(28)
        subtitle_frame.paragraphs[0].font.color.rgb = self.COLOR_TEXT_LIGHT
        
        # 右侧配图（圆形）
        pic_circle = slide.shapes.add_shape(
            MSO_SHAPE.OVAL,
            Inches(7.5), Inches(1),
            Inches(4), Inches(4)
        )
        pic_circle.fill.solid()
        pic_circle.fill.fore_color.rgb = self.COLOR_WHITE
        pic_circle.fill.fore_color.brightness = -0.2
        pic_circle.line.color.rgb = self.COLOR_PRIMARY_DARK
        pic_circle.line.width = Pt(3)
        
        # 目录项（从配置读取最大显示数量）
        max_items = config.get("ppt_generation.generation_preferences.max_catalog_items", 15)
        start_y = 2.0
        item_height = 0.7
        
        for i, item in enumerate(catalog_items[:max_items]):
            number = item.get("number", f"{i+1:02d}")
            title = item.get("title", "")
            
            y_pos = start_y + i * item_height
            
            # 编号框（蓝色圆角矩形）
            number_shape = slide.shapes.add_shape(
                MSO_SHAPE.ROUNDED_RECTANGLE,
                Inches(0.95), Inches(y_pos),
                Inches(0.7), Inches(0.45)
            )
            number_shape.fill.solid()
            number_shape.fill.fore_color.rgb = self.COLOR_PRIMARY_DARK
            number_shape.line.fill.background()
            
            number_text = number_shape.text_frame
            number_text.text = number
            number_text.paragraphs[0].alignment = PP_ALIGN.CENTER
            number_text.paragraphs[0].font.size = Pt(24)
            number_text.paragraphs[0].font.bold = True
            number_text.paragraphs[0].font.color.rgb = self.COLOR_WHITE
            number_text.vertical_anchor = MSO_ANCHOR.MIDDLE
            
            # 标题框（白色圆角矩形）
            title_shape = slide.shapes.add_shape(
                MSO_SHAPE.ROUNDED_RECTANGLE,
                Inches(1.75), Inches(y_pos),
                Inches(5.3), Inches(0.45)
            )
            title_shape.fill.solid()
            title_shape.fill.fore_color.rgb = self.COLOR_WHITE
            title_shape.line.color.rgb = self.COLOR_PRIMARY_DARK
            title_shape.line.width = Pt(1)
            
            title_text = title_shape.text_frame
            title_text.text = title
            title_text.paragraphs[0].font.size = Pt(20)
            title_text.paragraphs[0].font.color.rgb = self.COLOR_TEXT_DARK
            title_text.vertical_anchor = MSO_ANCHOR.MIDDLE
            title_text.margin_left = Inches(0.2)
        
        logger.info(f"创建目录页: {len(catalog_items)}项")
    
    def create_picture_slide(self, title: str, image_path: str, caption: str = ""):
        """
        创建图片页（左右布局：左侧图片，右侧文字说明）
        
        Args:
            title: 页面标题
            image_path: 图片路径
            caption: 图片说明（文字内容）
        """
        slide = self.prs.slides.add_slide(self.prs.slide_layouts[6])
        self._add_gradient_background(slide)
        
        # 标题栏
        title_bar = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE,
            0, 0,
            Inches(13.33), Inches(1.2)
        )
        title_bar.fill.solid()
        title_bar.fill.fore_color.rgb = self.COLOR_WHITE
        title_bar.line.fill.background()
        
        title_text = title_bar.text_frame
        title_text.text = title
        title_text.paragraphs[0].font.size = Pt(36)
        title_text.paragraphs[0].font.bold = True
        title_text.paragraphs[0].font.color.rgb = self.COLOR_PRIMARY_DARK
        title_text.vertical_anchor = MSO_ANCHOR.MIDDLE
        title_text.margin_left = Inches(0.5)
        
        # 左侧：图片容器
        pic_container = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE,
            Inches(0.8), Inches(1.8),
            Inches(6.5), Inches(5.2)
        )
        pic_container.fill.solid()
        pic_container.fill.fore_color.rgb = self.COLOR_WHITE
        pic_container.line.fill.background()
        
        # 插入图片
        try:
            pic = slide.shapes.add_picture(
                image_path,
                Inches(1), Inches(2),
                width=Inches(6)
            )
            # 调整图片大小以适应容器
            if pic.height > Inches(4.8):
                ratio = Inches(4.8) / pic.height
                pic.height = Inches(4.8)
                pic.width = int(pic.width * ratio)
            
            # 居中图片
            pic.left = Inches(4.05) - int(pic.width / 2)
            pic.top = Inches(4.4) - int(pic.height / 2)
            
        except Exception as e:
            logger.error(f"插入图片失败: {e}")
        
        # 右侧：文字说明区域
        if caption:
            text_container = slide.shapes.add_shape(
                MSO_SHAPE.ROUNDED_RECTANGLE,
                Inches(7.8), Inches(1.8),
                Inches(5), Inches(5.2)
            )
            text_container.fill.solid()
            text_container.fill.fore_color.rgb = self.COLOR_WHITE
            text_container.line.fill.background()
            
            text_frame = text_container.text_frame
            text_frame.word_wrap = True
            text_frame.margin_left = Inches(0.3)
            text_frame.margin_right = Inches(0.3)
            text_frame.margin_top = Inches(0.3)
            text_frame.margin_bottom = Inches(0.3)
            
            # 处理文字内容（支持多行）
            lines = caption.split('\n') if caption else []
            for i, line in enumerate(lines):
                if i > 0:
                    text_frame.add_paragraph()
                
                para = text_frame.paragraphs[i]
                
                # 检测缩进
                indent_level = 0
                clean_line = line
                if line.startswith("  - "):
                    indent_level = 1
                    clean_line = line[4:]
                elif line.startswith("- "):
                    indent_level = 0
                    clean_line = line[2:]
                
                # 清理Markdown标记
                clean_line, is_bold = self._clean_markdown_text(clean_line)
                
                para.text = clean_line
                para.level = indent_level
                para.font.size = Pt(18 if indent_level == 0 else 16)
                para.font.color.rgb = self.COLOR_TEXT_DARK
                
                # 加粗处理
                if is_bold:
                    para.font.bold = True
        
        logger.debug(f"创建图片页: {title}")
    
    def save(self, output_path: str):
        """保存PPT"""
        self.prs.save(output_path)
        logger.info(f"PPT已保存: {output_path}")
