# -*- coding: utf-8 -*-
"""
URL到PPT转换器

从URL提取内容并生成PPT
"""

import logging
from pathlib import Path
from typing import Dict, Optional
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor

from .web_content_extractor import WebContentExtractor
from .web_to_ppt_analyzer import WebToPPTAnalyzer
from utils.config_manager import config

logger = logging.getLogger(__name__)


class URLToPPTConverter:
    """URL到PPT转换器"""

    def __init__(self, style: str = "style_a"):
        """
        初始化转换器

        Args:
            style: PPT样式名称（style_a或style_b）
        """
        self.style = style
        self.style_config = config.get(f"ppt_generation.styles.{style}", {})

        # 初始化组件
        self.content_extractor = WebContentExtractor()
        self.content_analyzer = WebToPPTAnalyzer()

        logger.info(f"初始化URLToPPTConverter: style={style}")

    def convert(self, url: str, output_path: str, use_cache: bool = True) -> Dict:
        """
        从URL生成PPT

        Args:
            url: 网页URL
            output_path: 输出PPT文件路径
            use_cache: 是否使用缓存（默认True）

        Returns:
            转换结果字典：
            {
                'success': True/False,
                'output_path': 输出文件路径,
                'slides_count': 幻灯片数量,
                'message': 消息,
                'elapsed_time': 耗时（秒）
            }
        """
        import time

        start_time = time.time()
        logger.info(f"开始转换URL到PPT: {url}")
        logger.info(f"缓存设置: {'启用' if use_cache else '禁用'}")

        try:
            # 如果不使用缓存，先清理该URL的缓存
            if not use_cache:
                logger.info("不使用缓存，清理该URL的缓存")
                self.content_extractor.clear_cache(url)

            # 1. 提取网页内容
            logger.info("步骤1: 提取网页内容")
            article = self.content_extractor.extract_from_url(url)

            # 获取步骤1的Token使用情况
            step1_tokens = article.get("token_usage", {})
            step1_input = step1_tokens.get("input_tokens", 0)
            step1_output = step1_tokens.get("output_tokens", 0)
            step1_total = step1_tokens.get("total_tokens", 0)

            # 2. AI分析生成PPT结构
            logger.info("步骤2: AI分析生成PPT结构")
            ppt_structure = self.content_analyzer.analyze_content(article)

            # 获取步骤2的Token使用情况
            step2_tokens = ppt_structure.get("token_usage", {})
            step2_input = step2_tokens.get("input_tokens", 0)
            step2_output = step2_tokens.get("output_tokens", 0)
            step2_total = step2_tokens.get("total_tokens", 0)

            # 汇总Token使用情况
            total_input = step1_input + step2_input
            total_output = step1_output + step2_output
            total_tokens = step1_total + step2_total

            # 3. 生成PPT
            logger.info("步骤3: 生成PPT文件")
            # 传递图片列表给PPT生成器
            images = article.get("images", [])
            logger.info(f"文章包含{len(images)}张图片")
            self._create_ppt(ppt_structure, output_path, images)

            # 计算总耗时
            elapsed_time = time.time() - start_time

            # 构建消息
            token_msg = ""
            if step1_total > 0 or step2_total > 0:
                token_msg = f"，Token使用: 步骤1（提取内容）={step1_total}(I:{step1_input}/O:{step1_output}), 步骤2（分析PPT结构）={step2_total}(I:{step2_input}/O:{step2_output}), 总计={total_tokens}"
            else:
                token_msg = "，Token使用: 0（从缓存获取）"

            result = {
                "success": True,
                "output_path": output_path,
                "slides_count": len(ppt_structure["slides"]) + 1,  # +1 for cover
                "title": ppt_structure["cover"]["title"],
                "elapsed_time": elapsed_time,
                "token_usage": {
                    "step1": {
                        "input": step1_input,
                        "output": step1_output,
                        "total": step1_total,
                    },
                    "step2": {
                        "input": step2_input,
                        "output": step2_output,
                        "total": step2_total,
                    },
                    "total": {
                        "input": total_input,
                        "output": total_output,
                        "total": total_tokens,
                    },
                },
                "message": f"成功生成PPT，共{len(ppt_structure['slides']) + 1}页，耗时{elapsed_time:.1f}秒{token_msg}",
            }

            logger.info(f"转换成功: {result['message']}")
            return result

        except Exception as e:
            logger.error(f"转换失败: {e}", exc_info=True)
            return {
                "success": False,
                "output_path": "",
                "slides_count": 0,
                "message": f"转换失败: {str(e)}",
            }

    def _create_ppt(self, ppt_structure: Dict, output_path: str, images: list = None):
        """
        创建PPT文件

        Args:
            ppt_structure: PPT结构字典
            output_path: 输出文件路径
            images: 图片URL列表
        """
        if images is None:
            images = []
        # 加载模板或创建新演示文稿
        template_path = self.style_config.get("template_path")
        if template_path and Path(template_path).exists():
            logger.info(f"使用模板: {template_path}")
            prs = Presentation(template_path)
        else:
            logger.info("创建新演示文稿")
            prs = Presentation()
            # 设置幻灯片尺寸
            slide_size = config.get("ppt_generation.slide_size", {})
            prs.slide_width = Inches(slide_size.get("width", 10.0))
            prs.slide_height = Inches(slide_size.get("height", 7.5))

        # 1. 创建封面页
        self._create_cover_slide(prs, ppt_structure["cover"])

        # 2. 创建内容页（同时处理图片插入）
        image_index = 0  # 当前使用的图片索引
        for slide_data in ppt_structure["slides"]:
            # 检查是否需要插入图片
            if image_index < len(images):
                self._create_content_slide(prs, slide_data, images, image_index)
                # 如果这页使用了图片，索引递增
                if self._slide_contains_image_marker(slide_data):
                    image_index += 1
            else:
                self._create_content_slide(prs, slide_data)

        # 3. 如果还有剩余图片，添加到末尾
        if image_index < len(images):
            remaining_images = images[image_index:]
            logger.info(f"添加{len(remaining_images)}张剩余图片到PPT末尾")
            self._create_image_slides(prs, remaining_images)

        # 保存PPT
        prs.save(output_path)
        logger.info(f"PPT已保存: {output_path}")

    def _create_cover_slide(self, prs: Presentation, cover_data: Dict):
        """
        创建封面页

        Args:
            prs: 演示文稿对象
            cover_data: 封面数据
        """
        # 使用标题幻灯片布局（通常是第一个布局）
        slide_layout = prs.slide_layouts[0]
        slide = prs.slides.add_slide(slide_layout)

        # 设置标题
        title = slide.shapes.title
        title.text = cover_data.get("title", "未知标题")

        # 设置字体
        title_font_size = self.style_config.get("title_font_size", 44)
        for paragraph in title.text_frame.paragraphs:
            paragraph.font.size = Pt(title_font_size)
            paragraph.font.bold = True
            paragraph.font.color.rgb = RGBColor(0, 0, 0)

        # 设置副标题（包含作者和时间）
        if len(slide.placeholders) > 1:
            subtitle = slide.placeholders[1]
            subtitle_parts = []

            if cover_data.get("subtitle"):
                subtitle_parts.append(cover_data["subtitle"])

            if cover_data.get("author"):
                subtitle_parts.append(f"作者: {cover_data['author']}")

            if cover_data.get("date"):
                subtitle_parts.append(f"日期: {cover_data['date']}")

            subtitle.text = "\n".join(subtitle_parts)

            # 设置副标题字体
            for paragraph in subtitle.text_frame.paragraphs:
                paragraph.font.size = Pt(18)
                paragraph.font.color.rgb = RGBColor(64, 64, 64)

        logger.info(f"创建封面页: {cover_data.get('title')}")

    def _slide_contains_image_marker(self, slide_data: Dict) -> bool:
        """检查幻灯片是否包含图片标记"""
        points = slide_data.get("points", [])
        return any("[图片]" in str(point) for point in points)

    def _create_content_slide(
        self,
        prs: Presentation,
        slide_data: Dict,
        images: list = None,
        image_index: int = 0,
    ):
        """
        创建内容页

        Args:
            prs: 演示文稿对象
            slide_data: 幻灯片数据
            images: 图片URL列表
            image_index: 当前图片索引
        """
        if images is None:
            images = []
        # 使用标题和内容布局（通常是第二个布局）
        slide_layout = prs.slide_layouts[1]
        slide = prs.slides.add_slide(slide_layout)

        # 设置标题
        title = slide.shapes.title
        title.text = slide_data.get("title", "未知标题")

        # 设置标题字体
        content_font_size = self.style_config.get("content_font_size", 18)
        for paragraph in title.text_frame.paragraphs:
            paragraph.font.size = Pt(content_font_size + 6)
            paragraph.font.bold = True

        # 设置内容
        if len(slide.placeholders) > 1:
            content = slide.placeholders[1]
            text_frame = content.text_frame
            text_frame.clear()

            # 添加要点
            points = slide_data.get("points", [])
            has_image_marker = False
            for point in points:
                # 检查是否是图片标记
                if "[图片]" in str(point):
                    has_image_marker = True
                    # 跳过图片标记文本，稍后插入实际图片
                    continue

                p = text_frame.add_paragraph()
                p.text = point
                p.level = 0
                p.font.size = Pt(content_font_size)
                p.space_before = Pt(6)

            # 如果有图片标记且有可用图片，插入图片
            if has_image_marker and image_index < len(images):
                self._insert_image_to_slide(prs, slide, images[image_index])

        logger.debug(f"创建内容页: {slide_data.get('title')}")

    def _insert_image_to_slide(self, prs: Presentation, slide, img_url: str):
        """
        在幻灯片中插入图片（右侧区域）

        Args:
            prs: 演示文稿对象
            slide: 幻灯片对象
            img_url: 图片URL
        """
        try:
            import requests
            from io import BytesIO
            from PIL import Image as PILImage

            # 下载图片
            response = requests.get(img_url, timeout=10)
            response.raise_for_status()

            img_data = BytesIO(response.content)
            pil_img = PILImage.open(img_data)

            # 计算图片位置（右侧，文字下方）
            slide_width = prs.slide_width
            slide_height = prs.slide_height

            # 图片放在右侧，宽度为幻灯片的40%
            pic_width = slide_width * 0.4
            img_width, img_height = pil_img.size
            aspect_ratio = img_width / img_height
            pic_height = pic_width / aspect_ratio

            # 位置：右侧，垂直居中
            left = slide_width * 0.55
            top = (slide_height - pic_height) / 2

            # 重新读取图片数据
            img_data.seek(0)

            # 添加图片
            slide.shapes.add_picture(
                img_data, left, top, width=pic_width, height=pic_height
            )
            logger.info(f"在内容页插入图片: {img_url}")

        except Exception as e:
            logger.warning(f"插入图片失败: {img_url}, 错误: {e}")

    def _create_image_slides(self, prs: Presentation, images: list):
        """
        创建图片页

        Args:
            prs: 演示文稿对象
            images: 图片URL列表
        """
        import requests
        from io import BytesIO
        from PIL import Image as PILImage

        for i, img_url in enumerate(images):
            try:
                logger.debug(f"下载图片{i+1}/{len(images)}: {img_url}")

                # 下载图片
                response = requests.get(img_url, timeout=10)
                response.raise_for_status()

                # 使用PIL验证图片
                img_data = BytesIO(response.content)
                pil_img = PILImage.open(img_data)

                # 创建空白幻灯片
                blank_slide_layout = prs.slide_layouts[6]  # 空白布局
                slide = prs.slides.add_slide(blank_slide_layout)

                # 计算图片位置和大小（居中显示，保持宽高比）
                slide_width = prs.slide_width
                slide_height = prs.slide_height

                img_width, img_height = pil_img.size
                aspect_ratio = img_width / img_height

                # 设置最大尺寸（留边距）
                max_width = slide_width * 0.9
                max_height = slide_height * 0.9

                if img_width > max_width or img_height > max_height:
                    if aspect_ratio > max_width / max_height:
                        # 宽度为限制因素
                        pic_width = max_width
                        pic_height = max_width / aspect_ratio
                    else:
                        # 高度为限制因素
                        pic_height = max_height
                        pic_width = max_height * aspect_ratio
                else:
                    pic_width = Inches(img_width / 96)  # 假设96 DPI
                    pic_height = Inches(img_height / 96)

                # 居中位置
                left = (slide_width - pic_width) / 2
                top = (slide_height - pic_height) / 2

                # 重新读取图片数据（PIL已经消耗了流）
                img_data.seek(0)

                # 添加图片
                slide.shapes.add_picture(
                    img_data, left, top, width=pic_width, height=pic_height
                )

                logger.info(f"成功添加图片{i+1}: {img_url}")

            except Exception as e:
                logger.warning(f"添加图片{i+1}失败: {img_url}, 错误: {e}")
                continue
