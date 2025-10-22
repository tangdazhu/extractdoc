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
from .text_formatter import TextFormatter
from .template_manager import TemplateManager
from .template_based_ppt_generator import TemplateBasedPPTGenerator
from .business_style_ppt_generator import BusinessStylePPTGenerator
from .academic_style_ppt_generator import AcademicStylePPTGenerator
from .placeholder_helper import PlaceholderHelper
from utils.config_manager import config
from utils.token_cost import TokenCostCalculator

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

            # 计算费用
            if step1_total > 0 or step2_total > 0:
                total_cost = TokenCostCalculator.calculate_and_format(total_input, total_output)
                token_description = f"步骤1（提取内容）={step1_total}(I:{step1_input}/O:{step1_output}), 步骤2（分析PPT结构）={step2_total}(I:{step2_input}/O:{step2_output}), 总计={total_tokens}，费用={total_cost}"
            else:
                token_description = "0（从缓存获取），费用=0元"

            result = {
                "success": True,
                "output_path": output_path,
                "slides_count": len(ppt_structure["slides"]) + 2,  # +2 for cover and catalog
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
                    "description": token_description,  # 添加描述字段
                },
                "message": f"成功生成PPT，共{len(ppt_structure['slides']) + 2}页，耗时{elapsed_time:.1f}秒",
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
        创建PPT文件（使用风格生成器）

        Args:
            ppt_structure: PPT结构字典
            output_path: 输出文件路径
            images: 图片URL列表
        """
        if images is None:
            images = []
        
        # 根据style选择生成器
        if self.style == "style_b":
            # 学术风格
            generator = AcademicStylePPTGenerator()
        else:
            # 默认商务风格
            generator = BusinessStylePPTGenerator()

        # 1. 创建封面页
        cover_data = ppt_structure["cover"]
        generator.create_cover_slide(
            title=cover_data.get("title", "未知标题"),
            subtitle=cover_data.get("subtitle", ""),
            reporter=cover_data.get("author", ""),
            date=cover_data.get("date", "")
        )

        # 2. 创建目录页
        catalog_items = []
        for i, slide_data in enumerate(ppt_structure["slides"]):
            catalog_items.append({
                "number": f"{i+1:02d}",
                "title": slide_data.get("title", "未知标题")
            })
        generator.create_catalog_slide(catalog_items)

        # 3. 创建内容页
        image_index = 0
        for slide_data in ppt_structure["slides"]:
            title = slide_data.get("title", "未知标题")
            points = slide_data.get("points", [])
            
            # 检查是否有图片标记
            has_image = self._slide_contains_image_marker(slide_data)
            
            if has_image and image_index < len(images):
                # 创建图文页（使用图片占位符布局）
                # 移除[图片]标记
                text_points = [p for p in points if "[图片]" not in str(p)]
                
                # 下载图片
                image_path = self._download_image(images[image_index])
                if image_path:
                    generator.create_picture_slide(
                        title=title,
                        image_path=str(image_path),
                        caption="\n".join(text_points) if text_points else ""
                    )
                else:
                    # 图片下载失败，创建普通内容页
                    generator.create_content_slide(title, text_points)
                
                image_index += 1
            else:
                # 创建普通内容页
                generator.create_content_slide(title, points)

        # 3. 如果还有剩余图片，添加到末尾
        if image_index < len(images):
            remaining_images = images[image_index:]
            logger.info(f"添加{len(remaining_images)}张剩余图片")
            for img_url in remaining_images:
                image_path = self._download_image(img_url)
                if image_path:
                    generator.create_picture_slide(
                        title="补充图片",
                        image_path=str(image_path)
                    )

        # 保存PPT
        generator.save(output_path)
        logger.info(f"PPT已保存: {output_path}")
    
    def _slide_contains_image_marker(self, slide_data: Dict) -> bool:
        """检查幻灯片是否包含图片标记"""
        points = slide_data.get("points", [])
        return any("[图片]" in str(point) for point in points)
    
    def _download_image(self, img_url: str) -> Optional[Path]:
        """
        下载图片到临时文件
        
        Args:
            img_url: 图片URL
            
        Returns:
            临时文件路径，失败返回None
        """
        try:
            import requests
            import tempfile
            from io import BytesIO
            from PIL import Image as PILImage
            
            # 下载图片
            response = requests.get(img_url, timeout=10)
            response.raise_for_status()
            
            # 验证图片
            img_data = BytesIO(response.content)
            pil_img = PILImage.open(img_data)
            
            # 保存到临时文件
            suffix = Path(img_url).suffix or '.jpg'
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            pil_img.save(temp_file.name)
            temp_file.close()
            
            logger.debug(f"下载图片成功: {img_url}")
            return Path(temp_file.name)
            
        except Exception as e:
            logger.warning(f"下载图片失败: {img_url}, 错误: {e}")
            return None
