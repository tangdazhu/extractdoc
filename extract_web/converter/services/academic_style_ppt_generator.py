# -*- coding: utf-8 -*-
"""
学术风格PPT生成器

适合学术报告、论文演示、研究汇报
配色：深绿色系，专业、严谨
"""
import logging
from typing import List, Dict, Any, Optional
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE

logger = logging.getLogger(__name__)


class AcademicStylePPTGenerator:
    """
    学术风格PPT生成器
    
    设计特点:
    - 深绿色渐变背景
    - 金色装饰条
    - 白色内容区域
    - 简洁专业
    """
    
    # 配色方案
    COLOR_PRIMARY_DARK = RGBColor(0, 102, 68)  # 深绿
    COLOR_PRIMARY_LIGHT = RGBColor(76, 175, 80)  # 浅绿
    COLOR_ACCENT = RGBColor(255, 193, 7)  # 金色强调
    COLOR_WHITE = RGBColor(255, 255, 255)
    COLOR_TEXT_DARK = RGBColor(50, 50, 50)
    COLOR_TEXT_LIGHT = RGBColor(150, 150, 150)
    
    def __init__(self):
        """初始化生成器"""
        self.prs = Presentation()
        self.prs.slide_width = Inches(13.33)  # 16:9
        self.prs.slide_height = Inches(7.5)
        logger.info("初始化学术风格PPT生成器")
    
    def _add_gradient_background(self, slide, angle=90.0):
        """添加渐变背景"""
        background = slide.background
        fill = background.fill
        fill.gradient()
        fill.gradient_angle = angle
        fill.gradient_stops[0].color.rgb = self.COLOR_PRIMARY_DARK
        fill.gradient_stops[1].color.rgb = self.COLOR_PRIMARY_LIGHT
    
    def _add_top_accent_bar(self, slide):
        """添加顶部金色装饰条"""
        top_bar = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE,
            0, 0,
            Inches(13.33), Inches(0.3)
        )
        top_bar.fill.solid()
        top_bar.fill.fore_color.rgb = self.COLOR_ACCENT
        top_bar.line.fill.background()
    
    def create_cover_slide(self, title: str, subtitle: str = "", 
                          reporter: str = "", date: str = ""):
        """
        创建封面页
        
        Args:
            title: 主标题
            subtitle: 副标题
            reporter: 汇报人/作者
            date: 日期
        """
        slide = self.prs.slides.add_slide(self.prs.slide_layouts[6])
        self._add_gradient_background(slide)
        self._add_top_accent_bar(slide)
        
        # 主标题
        title_box = slide.shapes.add_textbox(
            Inches(1.5), Inches(2.8),
            Inches(10), Inches(1.2)
        )
        title_frame = title_box.text_frame
        title_frame.text = title
        title_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
        title_frame.paragraphs[0].font.size = Pt(54)
        title_frame.paragraphs[0].font.bold = True
        title_frame.paragraphs[0].font.color.rgb = self.COLOR_WHITE
        
        # 副标题
        if subtitle:
            subtitle_box = slide.shapes.add_textbox(
                Inches(2), Inches(4.2),
                Inches(9.33), Inches(0.5)
            )
            subtitle_frame = subtitle_box.text_frame
            subtitle_frame.text = subtitle
            subtitle_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
            subtitle_frame.paragraphs[0].font.size = Pt(20)
            subtitle_frame.paragraphs[0].font.color.rgb = self.COLOR_WHITE
        
        # 作者信息（左下）
        if reporter:
            author_box = slide.shapes.add_textbox(
                Inches(1.5), Inches(6.2),
                Inches(4), Inches(0.8)
            )
            author_frame = author_box.text_frame
            author_frame.text = f"作者: {reporter}"
            author_frame.paragraphs[0].font.size = Pt(16)
            author_frame.paragraphs[0].font.color.rgb = self.COLOR_WHITE
        
        # 日期信息（右下）
        if date:
            date_box = slide.shapes.add_textbox(
                Inches(8), Inches(6.5),
                Inches(3.5), Inches(0.5)
            )
            date_frame = date_box.text_frame
            date_frame.text = f"日期: {date}"
            date_frame.paragraphs[0].alignment = PP_ALIGN.RIGHT
            date_frame.paragraphs[0].font.size = Pt(16)
            date_frame.paragraphs[0].font.color.rgb = self.COLOR_WHITE
        
        logger.info(f"创建封面页: {title}")
    
    def create_catalog_slide(self, catalog_items: List[Dict[str, str]]):
        """
        创建目录页
        
        Args:
            catalog_items: 目录项列表，每项包含 {"number": "01", "title": "标题"}
        """
        slide = self.prs.slides.add_slide(self.prs.slide_layouts[6])
        self._add_gradient_background(slide)
        self._add_top_accent_bar(slide)
        
        # 标题
        title_box = slide.shapes.add_textbox(
            Inches(1), Inches(0.8),
            Inches(3), Inches(0.8)
        )
        title_frame = title_box.text_frame
        title_frame.text = "目录"
        title_frame.paragraphs[0].font.size = Pt(48)
        title_frame.paragraphs[0].font.bold = True
        title_frame.paragraphs[0].font.color.rgb = self.COLOR_WHITE
        
        # CONTENTS副标题
        subtitle_box = slide.shapes.add_textbox(
            Inches(4), Inches(1),
            Inches(3), Inches(0.5)
        )
        subtitle_frame = subtitle_box.text_frame
        subtitle_frame.text = "CONTENTS"
        subtitle_frame.paragraphs[0].font.size = Pt(24)
        subtitle_frame.paragraphs[0].font.color.rgb = self.COLOR_TEXT_LIGHT
        
        # 目录项（最多显示5项）
        start_y = 2.2
        item_height = 0.8
        
        for i, item in enumerate(catalog_items[:5]):
            number = item.get("number", f"{i+1:02d}")
            title = item.get("title", "")
            
            y_pos = start_y + i * item_height
            
            # 目录项框
            item_shape = slide.shapes.add_shape(
                MSO_SHAPE.ROUNDED_RECTANGLE,
                Inches(1.5), Inches(y_pos),
                Inches(10), Inches(0.6)
            )
            item_shape.fill.solid()
            item_shape.fill.fore_color.rgb = self.COLOR_WHITE
            item_shape.fill.fore_color.brightness = -0.1
            item_shape.line.fill.background()
            
            item_text = item_shape.text_frame
            item_text.text = f"{number}  {title}"
            item_text.paragraphs[0].font.size = Pt(20)
            item_text.paragraphs[0].font.color.rgb = self.COLOR_TEXT_DARK
            item_text.vertical_anchor = MSO_ANCHOR.MIDDLE
            item_text.margin_left = Inches(0.3)
        
        logger.info(f"创建目录页: {len(catalog_items)}项")
    
    def create_content_slide(self, title: str, content_lines: List[str]):
        """
        创建内容页
        
        Args:
            title: 页面标题
            content_lines: 内容行列表
        """
        slide = self.prs.slides.add_slide(self.prs.slide_layouts[6])
        self._add_gradient_background(slide)
        self._add_top_accent_bar(slide)
        
        # 标题栏
        title_bar = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE,
            0, Inches(0.3),
            Inches(13.33), Inches(0.9)
        )
        title_bar.fill.solid()
        title_bar.fill.fore_color.rgb = self.COLOR_WHITE
        title_bar.line.fill.background()
        
        # 标题文字
        title_text = title_bar.text_frame
        title_text.text = title
        title_text.paragraphs[0].font.size = Pt(32)
        title_text.paragraphs[0].font.bold = True
        title_text.paragraphs[0].font.color.rgb = self.COLOR_PRIMARY_DARK
        title_text.vertical_anchor = MSO_ANCHOR.MIDDLE
        title_text.margin_left = Inches(0.5)
        
        # 内容区域
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
            
            para.text = clean_line
            para.level = indent_level
            para.font.size = Pt(20 if indent_level == 0 else 18)
            para.font.color.rgb = self.COLOR_TEXT_DARK
            
            # 加粗处理
            if "**" in clean_line:
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
        self._add_top_accent_bar(slide)
        
        # 大号数字（金色）
        number_box = slide.shapes.add_textbox(
            Inches(3), Inches(2.5),
            Inches(7.33), Inches(1.5)
        )
        number_frame = number_box.text_frame
        number_frame.text = number
        number_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
        number_frame.paragraphs[0].font.size = Pt(100)
        number_frame.paragraphs[0].font.bold = True
        number_frame.paragraphs[0].font.color.rgb = self.COLOR_ACCENT
        
        # 章节标题
        section_title = slide.shapes.add_textbox(
            Inches(3), Inches(4.2),
            Inches(7.33), Inches(0.8)
        )
        section_frame = section_title.text_frame
        section_frame.text = title
        section_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
        section_frame.paragraphs[0].font.size = Pt(40)
        section_frame.paragraphs[0].font.bold = True
        section_frame.paragraphs[0].font.color.rgb = self.COLOR_WHITE
        
        logger.debug(f"创建章节页: {number} - {title}")
    
    def create_picture_slide(self, title: str, image_path: str, caption: str = ""):
        """
        创建图片页
        
        Args:
            title: 页面标题
            image_path: 图片路径
            caption: 图片说明
        """
        slide = self.prs.slides.add_slide(self.prs.slide_layouts[6])
        self._add_gradient_background(slide)
        self._add_top_accent_bar(slide)
        
        # 标题栏
        title_bar = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE,
            0, Inches(0.3),
            Inches(13.33), Inches(0.9)
        )
        title_bar.fill.solid()
        title_bar.fill.fore_color.rgb = self.COLOR_WHITE
        title_bar.line.fill.background()
        
        title_text = title_bar.text_frame
        title_text.text = title
        title_text.paragraphs[0].font.size = Pt(32)
        title_text.paragraphs[0].font.bold = True
        title_text.paragraphs[0].font.color.rgb = self.COLOR_PRIMARY_DARK
        title_text.vertical_anchor = MSO_ANCHOR.MIDDLE
        title_text.margin_left = Inches(0.5)
        
        # 图片容器
        pic_container = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE,
            Inches(2), Inches(2),
            Inches(9.33), Inches(4.5)
        )
        pic_container.fill.solid()
        pic_container.fill.fore_color.rgb = self.COLOR_WHITE
        pic_container.line.fill.background()
        
        # 插入图片
        try:
            pic = slide.shapes.add_picture(
                image_path,
                Inches(2.5), Inches(2.3),
                width=Inches(8.33)
            )
            # 调整图片大小
            if pic.height > Inches(3.8):
                pic.height = Inches(3.8)
                pic.width = int(pic.width * (Inches(3.8) / pic.height))
            
            # 居中图片
            pic.left = Inches(6.665) - int(pic.width / 2)
            pic.top = Inches(4) - int(pic.height / 2)
            
        except Exception as e:
            logger.error(f"插入图片失败: {e}")
        
        # 图片说明
        if caption:
            caption_box = slide.shapes.add_textbox(
                Inches(2), Inches(6.7),
                Inches(9.33), Inches(0.5)
            )
            caption_frame = caption_box.text_frame
            caption_frame.text = caption
            caption_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
            caption_frame.paragraphs[0].font.size = Pt(14)
            caption_frame.paragraphs[0].font.color.rgb = self.COLOR_WHITE
        
        logger.debug(f"创建图片页: {title}")
    
    def save(self, output_path: str):
        """保存PPT"""
        self.prs.save(output_path)
        logger.info(f"PPT已保存: {output_path}")
