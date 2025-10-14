# -*- coding: utf-8 -*-
"""
创建 PPT 模板文件

生成两个预定义模板：
1. 简约商务风格 (business_template.pptx)
2. 学术报告风格 (academic_template.pptx)
"""

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor
from pathlib import Path


def create_business_template():
    """创建简约商务风格模板"""
    prs = Presentation()
    prs.slide_width = Inches(10)
    prs.slide_height = Inches(5.625)
    
    # 修改默认布局的样式
    # 标题布局
    title_layout = prs.slide_layouts[0]
    # 内容布局
    bullet_layout = prs.slide_layouts[1]
    
    # 添加示例页面展示样式
    slide = prs.slides.add_slide(title_layout)
    title = slide.shapes.title
    subtitle = slide.placeholders[1]
    
    title.text = "简约商务风格"
    title.text_frame.paragraphs[0].font.size = Pt(44)
    title.text_frame.paragraphs[0].font.bold = True
    title.text_frame.paragraphs[0].font.color.rgb = RGBColor(0, 51, 102)  # 深蓝色
    
    subtitle.text = "适合商务汇报、项目展示"
    subtitle.text_frame.paragraphs[0].font.size = Pt(24)
    subtitle.text_frame.paragraphs[0].font.color.rgb = RGBColor(102, 102, 102)  # 灰色
    
    # 添加内容页示例
    slide2 = prs.slides.add_slide(bullet_layout)
    shapes = slide2.shapes
    title_shape = shapes.title
    body_shape = shapes.placeholders[1]
    
    title_shape.text = "内容页示例"
    title_shape.text_frame.paragraphs[0].font.size = Pt(32)
    title_shape.text_frame.paragraphs[0].font.color.rgb = RGBColor(0, 51, 102)
    
    tf = body_shape.text_frame
    tf.text = "第一个要点"
    tf.paragraphs[0].font.size = Pt(18)
    
    p = tf.add_paragraph()
    p.text = "第二个要点"
    p.level = 0
    p.font.size = Pt(18)
    
    output_path = Path(__file__).parent / "templates" / "business_template.pptx"
    prs.save(str(output_path))
    print(f"[OK] Business template created: {output_path}")


def create_academic_template():
    """创建学术报告风格模板"""
    prs = Presentation()
    prs.slide_width = Inches(10)
    prs.slide_height = Inches(5.625)
    
    # 标题页
    title_layout = prs.slide_layouts[0]
    slide = prs.slides.add_slide(title_layout)
    title = slide.shapes.title
    subtitle = slide.placeholders[1]
    
    title.text = "学术报告风格"
    title.text_frame.paragraphs[0].font.size = Pt(40)
    title.text_frame.paragraphs[0].font.bold = True
    title.text_frame.paragraphs[0].font.color.rgb = RGBColor(51, 51, 51)  # 深灰色
    
    subtitle.text = "适合学术论文、研究报告"
    subtitle.text_frame.paragraphs[0].font.size = Pt(20)
    subtitle.text_frame.paragraphs[0].font.color.rgb = RGBColor(102, 102, 102)
    
    # 内容页
    bullet_layout = prs.slide_layouts[1]
    slide2 = prs.slides.add_slide(bullet_layout)
    shapes = slide2.shapes
    title_shape = shapes.title
    body_shape = shapes.placeholders[1]
    
    title_shape.text = "研究内容"
    title_shape.text_frame.paragraphs[0].font.size = Pt(28)
    title_shape.text_frame.paragraphs[0].font.color.rgb = RGBColor(51, 51, 51)
    
    tf = body_shape.text_frame
    tf.text = "研究背景与动机"
    tf.paragraphs[0].font.size = Pt(16)
    
    p = tf.add_paragraph()
    p.text = "研究方法与实验设计"
    p.level = 0
    p.font.size = Pt(16)
    
    output_path = Path(__file__).parent / "templates" / "academic_template.pptx"
    prs.save(str(output_path))
    print(f"[OK] Academic template created: {output_path}")


if __name__ == "__main__":
    create_business_template()
    create_academic_template()
    print("\n[SUCCESS] All templates created!")
