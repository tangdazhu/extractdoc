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
from .layout_detector import LayoutDetector
from .content_parser import ContentParser
from utils.config_manager import config
from utils.token_cost import TokenCostCalculator
from utils.content_merger import ContentMerger

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
        self.layout_detector = LayoutDetector()
        self.content_parser = ContentParser()
        self.content_merger = ContentMerger()

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

    def convert_multiple_urls(self, urls: list, output_path: str, use_cache: bool = True) -> Dict:
        """
        从多个URL生成PPT（合并内容）

        Args:
            urls: URL列表
            output_path: 输出PPT文件路径
            use_cache: 是否使用缓存（默认True）

        Returns:
            转换结果字典
        """
        import time
        from concurrent.futures import ThreadPoolExecutor, as_completed

        if not urls:
            return {
                "success": False,
                "message": "URL列表不能为空",
                "output_path": "",
                "slides_count": 0
            }

        if len(urls) == 1:
            logger.info("只有一个URL，使用单URL转换")
            return self.convert(urls[0], output_path, use_cache)

        start_time = time.time()
        logger.info(f"开始多URL转换: {len(urls)}个URL")

        try:
            # 如果不使用缓存，先清理所有URL的缓存
            if not use_cache:
                logger.info("不使用缓存，清理所有URL的缓存")
                for url in urls:
                    self.content_extractor.clear_cache(url)

            # 1. 并行提取各URL内容
            logger.info("步骤1: 并行提取各URL内容")
            extracted_contents = []
            total_step1_tokens = {"input": 0, "output": 0, "total": 0}

            max_workers = config.get("web_extraction.max_parallel_workers", 5)
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_url = {
                    executor.submit(self.content_extractor.extract_from_url, url): url
                    for url in urls
                }

                for future in as_completed(future_to_url):
                    url = future_to_url[future]
                    try:
                        article = future.result()
                        article['source_url'] = url
                        extracted_contents.append(article)

                        # 累计Token使用
                        tokens = article.get("token_usage", {})
                        total_step1_tokens["input"] += tokens.get("input_tokens", 0)
                        total_step1_tokens["output"] += tokens.get("output_tokens", 0)
                        total_step1_tokens["total"] += tokens.get("total_tokens", 0)

                        logger.info(f"成功提取URL: {url}")
                    except Exception as e:
                        logger.error(f"提取URL失败 {url}: {e}")

            if not extracted_contents:
                raise ValueError("所有URL提取均失败")

            logger.info(f"成功提取{len(extracted_contents)}/{len(urls)}个URL")

            # 2. 合并内容
            logger.info("步骤2: 合并内容并去重")
            merged_article = self.content_merger.merge(extracted_contents)
            logger.info(f"合并完成: {len(merged_article['sections'])}个章节, {len(merged_article['images'])}张图片")

            # 3. AI分析生成PPT结构
            logger.info("步骤3: AI分析生成PPT结构")
            ppt_structure = self.content_analyzer.analyze_content(merged_article)

            # 获取步骤3的Token使用情况
            step3_tokens = ppt_structure.get("token_usage", {})
            step3_input = step3_tokens.get("input_tokens", 0)
            step3_output = step3_tokens.get("output_tokens", 0)
            step3_total = step3_tokens.get("total_tokens", 0)

            # 汇总Token使用情况
            total_input = total_step1_tokens["input"] + step3_input
            total_output = total_step1_tokens["output"] + step3_output
            total_tokens = total_step1_tokens["total"] + step3_total

            # 4. 生成PPT（添加来源信息）
            logger.info("步骤4: 生成PPT文件")
            images = merged_article.get("images", [])
            logger.info(f"合并后包含{len(images)}张图片")

            # 修改封面副标题，显示来源数量
            if "cover" in ppt_structure:
                original_subtitle = ppt_structure["cover"].get("subtitle", "")
                ppt_structure["cover"]["subtitle"] = f"基于{len(urls)}个来源的综合分析"
                if original_subtitle:
                    ppt_structure["cover"]["subtitle"] += f" | {original_subtitle}"

            self._create_ppt(ppt_structure, output_path, images)

            # 计算总耗时
            elapsed_time = time.time() - start_time

            # 计算费用
            if total_tokens > 0:
                total_cost = TokenCostCalculator.calculate_and_format(total_input, total_output)
                token_description = f"步骤1（提取{len(extracted_contents)}个URL）={total_step1_tokens['total']}(I:{total_step1_tokens['input']}/O:{total_step1_tokens['output']}), 步骤3（分析PPT结构）={step3_total}(I:{step3_input}/O:{step3_output}), 总计={total_tokens}，费用={total_cost}"
            else:
                token_description = "0（从缓存获取），费用=0元"

            result = {
                "success": True,
                "output_path": output_path,
                "slides_count": len(ppt_structure["slides"]) + 2,
                "title": ppt_structure["cover"]["title"],
                "source_urls": urls,
                "merged_sources_count": len(extracted_contents),
                "elapsed_time": elapsed_time,
                "token_usage": {
                    "step1": total_step1_tokens,
                    "step3": {
                        "input": step3_input,
                        "output": step3_output,
                        "total": step3_total,
                    },
                    "total": {
                        "input": total_input,
                        "output": total_output,
                        "total": total_tokens,
                    },
                    "description": token_description,
                },
                "message": f"成功从{len(extracted_contents)}个来源生成PPT，共{len(ppt_structure['slides']) + 2}页，耗时{elapsed_time:.1f}秒",
            }

            logger.info(f"多URL转换成功: {result['message']}")
            return result

        except Exception as e:
            logger.error(f"多URL转换失败: {e}", exc_info=True)
            return {
                "success": False,
                "output_path": "",
                "slides_count": 0,
                "message": f"多URL转换失败: {str(e)}",
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
        logger.info(f"选择PPT生成器: style={self.style}")
        if self.style == "style_b":
            # 学术风格
            logger.info("使用学术风格生成器")
            generator = AcademicStylePPTGenerator()
        else:
            # 默认商务风格
            logger.info("使用商务风格生成器")
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

        # 3. 创建内容页（使用自动布局选择）
        image_index = 0
        for slide_data in ppt_structure["slides"]:
            title = slide_data.get("title", "未知标题")
            points = slide_data.get("points", [])
            
            # 检查是否有图片标记
            has_image = self._slide_contains_image_marker(slide_data)
            
            if has_image and image_index < len(images):
                # 创建图文页
                text_points = [p for p in points if "[图片]" not in str(p)]
                image_path = self._download_image(images[image_index])
                if image_path:
                    generator.create_picture_slide(
                        title=title,
                        image_path=str(image_path),
                        caption="\n".join(text_points) if text_points else ""
                    )
                else:
                    generator.create_content_slide(title, text_points)
                image_index += 1
            else:
                # 检查是否启用自动布局检测
                auto_detect = config.get("ppt_generation.layout_types.auto_detect", True)
                
                if auto_detect:
                    # 自动检测布局类型
                    content_dict = {"title": title, "content": points}
                    layout_type = self.layout_detector.detect_layout_type(content_dict)
                    
                    # 根据布局类型创建页面
                    self._create_slide_by_layout(generator, layout_type, content_dict)
                else:
                    # 使用默认布局
                    generator.create_content_slide(title, points)

        # 3. 根据配置决定是否添加剩余图片
        add_remaining = config.get("ppt_generation.generation_preferences.add_remaining_images", False)
        if add_remaining and image_index < len(images):
            remaining_images = images[image_index:]
            logger.info(f"添加{len(remaining_images)}张剩余图片（配置启用）")
            for img_url in remaining_images:
                image_path = self._download_image(img_url)
                if image_path:
                    generator.create_picture_slide(
                        title="补充图片",
                        image_path=str(image_path)
                    )
        elif image_index < len(images):
            remaining_count = len(images) - image_index
            logger.info(f"跳过{remaining_count}张剩余图片（配置禁用add_remaining_images）")

        # 保存PPT
        generator.save(output_path)
        logger.info(f"PPT已保存: {output_path}")
    
    def _create_slide_by_layout(self, generator, layout_type: str, content: Dict):
        """
        根据布局类型创建页面
        
        Args:
            generator: PPT生成器
            layout_type: 布局类型
            content: 内容字典
        """
        title = content.get("title", "")
        points = content.get("content", [])
        
        try:
            if layout_type == "two_column":
                # 左右对比布局
                left, right, left_title, right_title = self.content_parser.parse_two_column_content(content)
                generator.create_two_column_slide(title, left, right, left_title, right_title)
                
            elif layout_type == "three_column":
                # 三列卡片布局
                cards = self.content_parser.parse_three_column_content(content)
                generator.create_three_column_slide(title, cards)
                
            elif layout_type == "flow_diagram":
                # 流程图布局
                steps = self.content_parser.parse_flow_diagram_content(content)
                generator.create_flow_diagram_slide(title, steps)
                
            elif layout_type == "timeline":
                # 时间线布局
                items = self.content_parser.parse_timeline_content(content)
                generator.create_timeline_slide(title, items)
                
            else:
                # 默认：bullet list
                generator.create_content_slide(title, points)
                
        except Exception as e:
            # 如果特殊布局失败，回退到默认布局
            logger.warning(f"布局{layout_type}创建失败，回退到默认布局: {e}")
            generator.create_content_slide(title, points)
    
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
            from urllib.parse import urlparse, parse_qs
            import mimetypes
            
            # 智能设置Referer（根据图片URL来源）
            referer = self._get_referer_for_image(img_url)
            
            # 添加请求头（避免403/防盗链）
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": referer
            }
            
            # 下载图片
            response = requests.get(img_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # 验证图片
            img_data = BytesIO(response.content)
            pil_img = PILImage.open(img_data)
            
            # 智能提取文件扩展名
            suffix = self._extract_image_extension(img_url, pil_img.format)
            
            # 保存到临时文件
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            pil_img.save(temp_file.name)
            temp_file.close()
            
            logger.debug(f"下载图片成功: {img_url}")
            return Path(temp_file.name)
            
        except Exception as e:
            logger.warning(f"下载图片失败: {img_url}, 错误: {e}")
            return None
    
    def _extract_image_extension(self, img_url: str, pil_format: str = None) -> str:
        """
        智能提取图片扩展名
        
        Args:
            img_url: 图片URL
            pil_format: PIL检测到的图片格式（如'JPEG', 'PNG'）
            
        Returns:
            文件扩展名（如'.jpg', '.png'）
        """
        from urllib.parse import urlparse
        import re
        
        # 方法1: 优先使用PIL检测到的格式
        if pil_format:
            format_map = {
                'JPEG': '.jpg',
                'PNG': '.png',
                'GIF': '.gif',
                'WEBP': '.webp',
                'BMP': '.bmp',
                'TIFF': '.tiff'
            }
            ext = format_map.get(pil_format.upper())
            if ext:
                return ext
        
        # 方法2: 从URL路径提取（去除查询参数）
        parsed = urlparse(img_url)
        path = parsed.path
        
        # 匹配常见图片扩展名（忽略大小写）
        match = re.search(r'\.(jpg|jpeg|png|gif|webp|bmp|tiff|svg)(?:[?#]|$)', path, re.IGNORECASE)
        if match:
            return '.' + match.group(1).lower()
        
        # 方法3: 检查文件名中是否包含扩展名（不在末尾的情况）
        match = re.search(r'\.(jpg|jpeg|png|gif|webp|bmp|tiff)', path, re.IGNORECASE)
        if match:
            return '.' + match.group(1).lower()
        
        # 默认返回.jpg
        return '.jpg'
    
    def _get_referer_for_image(self, img_url: str) -> str:
        """
        根据图片URL智能设置Referer
        
        Args:
            img_url: 图片URL
            
        Returns:
            适合的Referer地址
        """
        # 微信图片：使用微信Referer
        if "mmbiz.qpic.cn" in img_url or "mmbiz.qlogo.cn" in img_url:
            return "https://mp.weixin.qq.com/"
        
        # 头条图片：使用头条Referer
        if "toutiaoimg.com" in img_url or "toutiaostatic.com" in img_url:
            return "https://www.toutiao.com/"
        
        # 知乎图片
        if "zhimg.com" in img_url:
            return "https://www.zhihu.com/"
        
        # CSDN图片
        if "csdnimg.cn" in img_url:
            return "https://blog.csdn.net/"
        
        # 掘金图片
        if "juejin.cn" in img_url or "juejin.im" in img_url:
            return "https://juejin.cn/"
        
        # B站图片
        if "bilibili.com" in img_url or "hdslb.com" in img_url:
            return "https://www.bilibili.com/"
        
        # 默认：使用图片所在域名
        from urllib.parse import urlparse
        parsed = urlparse(img_url)
        if parsed.scheme and parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}/"
        
        # 兼容性默认值
        return "https://www.toutiao.com/"
