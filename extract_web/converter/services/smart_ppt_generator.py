# -*- coding: utf-8 -*-
"""
智能PPT生成器

基于AI分析结果生成PPT,完全抛弃固定规则
"""

import logging
from pathlib import Path
from typing import Dict, List

from pptx import Presentation
from pptx.util import Inches, Pt as PptPt

logger = logging.getLogger("converter")


class SmartPPTGenerator:
    """基于AI分析的智能PPT生成器"""
    
    def __init__(self, config: dict = None):
        """
        初始化智能PPT生成器
        
        Args:
            config: 物理布局配置
        """
        self.config = config or self._get_default_config()
    
    def generate_ppt(
        self,
        template_path: Path,
        document_structure: dict,
        page_analyses: List[dict],
        multimodal_data: dict,
        request_id: str
    ) -> Presentation:
        """
        生成PPT
        
        Args:
            template_path: 模板路径
            document_structure: AI分析的文档结构
            page_analyses: AI分析的各页内容
            multimodal_data: 多模态数据
            request_id: 请求ID
            
        Returns:
            生成的Presentation对象
        """
        logger.info("开始智能PPT生成,RequestID=%s", request_id)
        
        # 1. 加载模板
        presentation = Presentation(str(template_path))
        
        # 删除模板中除第一页外的示例页面
        if len(presentation.slides) > 1:
            xml_slides = presentation.slides._sldIdLst
            slides_to_delete = list(range(1, len(xml_slides)))
            for idx in reversed(slides_to_delete):
                rId = xml_slides[idx].rId
                presentation.part.drop_rel(rId)
                del xml_slides[idx]
            logger.debug("已清除模板示例页面(保留第一页)")
        
        # 2. 生成标题页
        self._create_title_slide(
            presentation,
            document_structure.get("title_page", {}),
            multimodal_data
        )
        
        # 3. 生成内容页
        content_pages = document_structure.get("content_pages", [])
        background_images = document_structure.get("background_images", [])
        
        # 构建背景图过滤集合
        bg_image_pages = set()
        for bg_info in background_images:
            if bg_info.get("should_filter", False):
                bg_image_pages.update(bg_info.get("pages", []))
        
        for page_analysis in page_analyses:
            page_num = page_analysis.get("page_number")
            
            # 跳过标题页
            if page_num == document_structure.get("title_page", {}).get("page_number", 1):
                continue
            
            # 跳过低重要度页面(可配置)
            if page_analysis.get("importance") == "low" and self.config.get("skip_low_importance", False):
                logger.debug("跳过低重要度页面: 第%d页", page_num)
                continue
            
            self._create_content_slide(
                presentation,
                page_analysis,
                multimodal_data,
                bg_image_pages
            )
        
        logger.info("智能PPT生成完成,共%d页,RequestID=%s", len(presentation.slides), request_id)
        return presentation
    
    def _create_title_slide(
        self,
        presentation: Presentation,
        title_page_info: dict,
        multimodal_data: dict
    ):
        """创建标题页"""
        
        # 使用模板第一页
        if len(presentation.slides) == 0:
            title_layout = presentation.slide_layouts[0]
            title_slide = presentation.slides.add_slide(title_layout)
        else:
            title_slide = presentation.slides[0]
        
        # 设置标题和副标题
        elements = title_page_info.get("elements", {})
        title_text = elements.get("title", "文档标题")
        subtitle_text = elements.get("subtitle", "AI智能生成")
        
        if title_slide.shapes.title:
            title_slide.shapes.title.text = title_text
        
        if len(title_slide.placeholders) > 1:
            title_slide.placeholders[1].text = subtitle_text
        
        logger.info("已创建标题页: %s", title_text)
        
        # 如果有元数据表,添加到标题页
        metadata_table = elements.get("metadata_table")
        if metadata_table and metadata_table.get("should_include", False):
            table_page = metadata_table.get("page")
            page_tables = [t for t in multimodal_data.get("tables", []) if t["page"] == table_page]
            
            if page_tables:
                table_data = page_tables[0]["data"]
                rows = len(table_data)
                cols = len(table_data[0]) if table_data else 0
                
                if rows > 0 and cols > 0:
                    # 在标题页底部添加表格
                    left = Inches(3.0)
                    top = Inches(5.5)
                    width = Inches(4.0)
                    height = Inches(0.4 * rows)
                    
                    table = title_slide.shapes.add_table(rows, cols, left, top, width, height).table
                    
                    for row_idx, row_data in enumerate(table_data):
                        for col_idx, cell_value in enumerate(row_data):
                            cell = table.cell(row_idx, col_idx)
                            cell.text = str(cell_value) if cell_value else ""
                            cell.text_frame.paragraphs[0].font.size = PptPt(11)
                            if row_idx == 0:
                                cell.text_frame.paragraphs[0].font.bold = True
                    
                    logger.info("已将元数据表添加到标题页")
    
    def _create_content_slide(
        self,
        presentation: Presentation,
        page_analysis: dict,
        multimodal_data: dict,
        bg_image_pages: set
    ):
        """创建内容页"""
        
        page_num = page_analysis.get("page_number")
        title = page_analysis.get("title", f"第{page_num}页")
        layout_type = page_analysis.get("suggested_layout", "title_and_text")
        
        # 选择布局
        try:
            content_layout = presentation.slide_layouts[1]  # 标题和内容布局
        except IndexError:
            content_layout = presentation.slide_layouts[0]
        
        slide = presentation.slides.add_slide(content_layout)
        
        # 设置标题
        if slide.shapes.title:
            slide.shapes.title.text = title
        
        # 添加元素(只添加AI标记为should_keep的元素)
        current_top = Inches(1.0)
        max_height = Inches(5.5)
        
        has_content = False  # 跟踪是否添加了任何内容
        
        for element in page_analysis.get("elements", []):
            if not element.get("should_keep", True):
                logger.debug("跳过元素: %s (原因: %s)", element.get("type"), element.get("reason"))
                continue
            
            if current_top >= max_height:
                logger.warning("第%d页空间不足,跳过剩余元素", page_num)
                break
            
            element_type = element.get("type")
            
            if element_type == "table":
                current_top = self._add_table(slide, page_num, multimodal_data, current_top)
                has_content = True
            elif element_type == "image":
                # 检查是否为背景图
                if page_num in bg_image_pages:
                    logger.debug("跳过第%d页的背景图", page_num)
                    continue
                current_top = self._add_images(slide, page_num, multimodal_data, current_top, max_height)
                has_content = True
            elif element_type == "text":
                current_top = self._add_text(slide, page_num, multimodal_data, current_top, max_height)
                has_content = True
        
        # 如果没有添加任何内容,尝试添加文本
        if not has_content:
            logger.warning("第%d页没有添加任何元素,尝试添加文本内容", page_num)
            page_data = next((p for p in multimodal_data.get("pages", []) if p["page"] == page_num), None)
            if page_data and page_data.get("text", "").strip():
                current_top = self._add_text(slide, page_num, multimodal_data, current_top, max_height)
        
        logger.debug("已创建内容页: 第%d页 - %s", page_num, title)
    
    def _add_table(
        self,
        slide,
        page_num: int,
        multimodal_data: dict,
        current_top: float
    ) -> float:
        """添加表格"""
        
        page_tables = [t for t in multimodal_data.get("tables", []) if t["page"] == page_num]
        
        for table_data in page_tables:
            rows_data = table_data["data"]
            rows = len(rows_data)
            cols = len(rows_data[0]) if rows_data else 0
            
            if rows > 0 and cols > 0:
                left = Inches(0.5)
                width = Inches(9.0)
                row_height = min(0.4, 2.5 / rows)
                height = Inches(row_height * rows)
                
                table = slide.shapes.add_table(rows, cols, left, current_top, width, height).table
                
                for row_idx, row_data in enumerate(rows_data):
                    for col_idx, cell_value in enumerate(row_data):
                        cell = table.cell(row_idx, col_idx)
                        cell.text = str(cell_value) if cell_value else ""
                        cell.text_frame.paragraphs[0].font.size = PptPt(11)
                        if row_idx == 0:
                            cell.text_frame.paragraphs[0].font.bold = True
                
                current_top += height + Inches(0.3)
                logger.debug("已添加表格: 第%d页, %d行x%d列", page_num, rows, cols)
        
        return current_top
    
    def _add_images(
        self,
        slide,
        page_num: int,
        multimodal_data: dict,
        current_top: float,
        max_height: float
    ) -> float:
        """添加图片"""
        
        page_images = [i for i in multimodal_data.get("images", []) if i["page"] == page_num]
        
        # 过滤掉不存在的图片
        valid_images = [img for img in page_images if img.get("path") and img["path"].exists()]
        
        if not valid_images:
            return current_top
        
        # 如果有2张图片,左右并排
        if len(valid_images) == 2:
            available_height = max_height - current_top
            available_width_per_img = Inches(4.5)
            max_img_height = 0
            
            for img_idx, img_data in enumerate(valid_images):
                img_path = img_data["path"]
                img_width_px = img_data["width"]
                img_height_px = img_data["height"]
                
                img_width_inch = img_width_px / 96.0
                img_height_inch = img_height_px / 96.0
                
                width_ratio = available_width_per_img / Inches(img_width_inch)
                height_ratio = available_height / Inches(img_height_inch)
                scale_ratio = min(width_ratio, height_ratio, 1.0)
                
                final_width = Inches(img_width_inch * scale_ratio)
                final_height = Inches(img_height_inch * scale_ratio)
                
                left = Inches(0.5) if img_idx == 0 else Inches(5.5)
                
                slide.shapes.add_picture(
                    str(img_path),
                    left=left,
                    top=current_top,
                    width=final_width,
                    height=final_height
                )
                
                max_img_height = max(max_img_height, final_height)
            
            current_top += max_img_height + Inches(0.3)
            logger.debug("已添加图片: 第%d页 (左右并排)", page_num)
        else:
            # 单张或多张图片,垂直排列
            for img_data in valid_images:
                if current_top >= max_height - Inches(0.5):
                    break
                
                img_path = img_data["path"]
                img_width_px = img_data["width"]
                img_height_px = img_data["height"]
                
                available_height = max_height - current_top - Inches(0.2)
                max_width = Inches(9.0)
                
                img_width_inch = img_width_px / 96.0
                img_height_inch = img_height_px / 96.0
                
                width_ratio = max_width / Inches(img_width_inch)
                height_ratio = available_height / Inches(img_height_inch)
                scale_ratio = min(width_ratio, height_ratio, 1.0)
                
                final_width = Inches(img_width_inch * scale_ratio)
                final_height = Inches(img_height_inch * scale_ratio)
                left = (Inches(10.0) - final_width) / 2
                
                slide.shapes.add_picture(
                    str(img_path),
                    left=left,
                    top=current_top,
                    width=final_width,
                    height=final_height
                )
                
                current_top += final_height + Inches(0.2)
                logger.debug("已添加图片: 第%d页 (%dx%d)", page_num, img_width_px, img_height_px)
        
        return current_top
    
    def _add_text(
        self,
        slide,
        page_num: int,
        multimodal_data: dict,
        current_top: float,
        max_height: float
    ) -> float:
        """添加文本内容"""
        
        # 获取页面文本
        page_data = next((p for p in multimodal_data.get("pages", []) if p["page"] == page_num), None)
        if not page_data:
            return current_top
        
        page_text = page_data.get("text", "")
        if not page_text.strip():
            return current_top
        
        lines = [line.strip() for line in page_text.split('\n') if line.strip()]
        if not lines:
            return current_top
        
        # 过滤掉页眉页脚
        filtered_lines = []
        for line in lines:
            line_lower = line.lower()
            # 跳过页眉页脚
            if 'proprietary and confidential' in line_lower:
                continue
            if line.isdigit() and len(line) <= 2:  # 跳过单独的页码
                continue
            filtered_lines.append(line)
        
        if not filtered_lines:
            return current_top
        
        # 查找内容占位符
        body_shape = None
        for shape in slide.shapes:
            if shape.has_text_frame and shape != slide.shapes.title:
                # 检查是否是内容占位符
                if hasattr(shape, 'placeholder_format'):
                    body_shape = shape
                    break
        
        # 如果找到占位符,使用它;否则创建文本框
        if body_shape:
            text_frame = body_shape.text_frame
            text_frame.clear()
        else:
            text_box = slide.shapes.add_textbox(
                Inches(0.5),
                current_top,
                Inches(9.0),
                max_height - current_top
            )
            text_frame = text_box.text_frame
        
        text_frame.word_wrap = True
        
        # 智能识别列表结构
        for idx, line in enumerate(filtered_lines):
            # 检查是否是编号列表(1. 2. 3. 等)
            is_numbered = line and len(line) > 2 and line[0].isdigit() and line[1] in '.、'
            # 检查是否是子项(以•或-开头,或有缩进)
            is_bullet = line.startswith('•') or line.startswith('-') or line.startswith('  ')
            
            if idx == 0:
                text_frame.text = line
                p = text_frame.paragraphs[0]
            else:
                p = text_frame.add_paragraph()
                p.text = line
            
            # 设置层级
            if is_bullet or (is_numbered and '  ' in line):
                p.level = 1  # 子项
                p.font.size = PptPt(12)
            else:
                p.level = 0  # 主项
                p.font.size = PptPt(14)
        
        logger.debug("已添加文本内容: 第%d页, %d行", page_num, len(filtered_lines))
        
        return max_height  # 文本占满剩余空间
    
    def _get_default_config(self) -> dict:
        """获取默认配置"""
        return {
            "skip_low_importance": False,
            "max_elements_per_slide": 5
        }
