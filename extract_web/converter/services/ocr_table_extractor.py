"""OCR表格提取模块。

使用paddleocr对PDF表格区域进行OCR识别,作为pdfplumber的补充和fallback。
"""

import logging
from pathlib import Path
from typing import List, Dict, Optional
import io

logger = logging.getLogger("converter")

try:
    from paddleocr import PaddleOCR
    import fitz  # PyMuPDF
    from PIL import Image
    import numpy as np
    PADDLEOCR_AVAILABLE = True
except ImportError as e:
    PADDLEOCR_AVAILABLE = False
    logger.warning(f"paddleocr或相关依赖未安装: {e}")


class OCRTableExtractor:
    """使用OCR提取PDF表格内容"""
    
    def __init__(self):
        """初始化OCR引擎"""
        if not PADDLEOCR_AVAILABLE:
            raise ImportError("paddleocr未安装,无法使用OCR表格提取")
        
        # 初始化paddleocr
        # use_angle_cls=True: 支持旋转文字识别
        # lang='ch': 中英文混合识别
        self.ocr = PaddleOCR(
            use_angle_cls=True,
            lang='ch',
            show_log=False,
            use_gpu=False  # 如果有GPU可以设置为True
        )
        logger.info("OCR表格提取器初始化成功")
    
    def extract_table_from_page(
        self,
        pdf_path: Path,
        page_num: int,
        table_bbox: Optional[tuple] = None
    ) -> List[List[str]]:
        """
        从PDF页面提取表格内容
        
        Args:
            pdf_path: PDF文件路径
            page_num: 页码(从1开始)
            table_bbox: 表格区域坐标(x0, y0, x1, y1),如果为None则提取整页
            
        Returns:
            表格数据,二维列表
        """
        try:
            # 1. 将PDF页面转为图片
            pdf_document = fitz.open(str(pdf_path))
            page = pdf_document[page_num - 1]  # fitz页码从0开始
            
            # 如果指定了表格区域,裁剪图片
            if table_bbox:
                # 创建裁剪矩形
                rect = fitz.Rect(table_bbox)
                pix = page.get_pixmap(clip=rect, matrix=fitz.Matrix(2, 2))  # 2倍缩放提高清晰度
            else:
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            
            # 转为PIL Image
            img_data = pix.tobytes("png")
            image = Image.open(io.BytesIO(img_data))
            
            # 转为numpy数组(paddleocr需要)
            img_array = np.array(image)
            
            # 2. 使用paddleocr识别
            result = self.ocr.ocr(img_array, cls=True)
            
            if not result or not result[0]:
                logger.warning(f"页面{page_num}OCR识别结果为空")
                return []
            
            # 3. 解析OCR结果为表格
            # paddleocr返回格式: [[[bbox], (text, confidence)], ...]
            ocr_lines = []
            for line in result[0]:
                bbox = line[0]  # [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                text = line[1][0]  # 识别的文字
                confidence = line[1][1]  # 置信度
                
                # 计算文本框的中心y坐标,用于行分组
                y_center = (bbox[0][1] + bbox[2][1]) / 2
                
                ocr_lines.append({
                    'text': text,
                    'confidence': confidence,
                    'bbox': bbox,
                    'y_center': y_center,
                    'x_left': bbox[0][0]  # 左边界x坐标,用于列排序
                })
            
            # 4. 过滤页眉页脚(通常在页面顶部和底部)
            page_height = pix.height
            filtered_lines = []
            for line in ocr_lines:
                y_pos = line['y_center']
                text = line['text']
                
                # 过滤顶部10%和底部10%的内容(页眉页脚)
                # 同时过滤包含常见页眉页脚关键词的行
                is_header_footer = (
                    y_pos < page_height * 0.10 or  # 顶部10%
                    y_pos > page_height * 0.90 or  # 底部10%
                    '远景智能' in text or
                    'Proprietary' in text or
                    'Confidential' in text
                )
                
                if not is_header_footer:
                    filtered_lines.append(line)
                else:
                    logger.debug(f"过滤页眉页脚: y={y_pos:.1f}, text='{text[:30]}'")
            
            # 5. 按y坐标分组为行(容差10像素)
            rows = self._group_into_rows(filtered_lines, y_tolerance=10)
            
            # 6. 过滤单行标题(表格标题通常是单独一行,只有1列)
            # 如果第1行只有1列,且第2行有多列,则第1行可能是标题
            if len(rows) >= 2:
                first_row_cols = len(rows[0])
                second_row_cols = len(rows[1])
                
                if first_row_cols == 1 and second_row_cols >= 3:
                    # 第1行只有1列,第2行有多列 → 第1行是标题,删除
                    title_text = rows[0][0]['text']
                    logger.debug(f"过滤表格标题行: '{title_text}'")
                    rows = rows[1:]  # 删除第1行
            
            # 7. 每行内按x坐标排序为列
            table_data = []
            for row in rows:
                sorted_row = sorted(row, key=lambda x: x['x_left'])
                row_texts = [item['text'] for item in sorted_row]
                table_data.append(row_texts)
            
            # 8. 删除全空的列
            table_data = self._remove_empty_columns(table_data)
            
            # 9. 规范化表格结构(确保所有行的列数一致)
            table_data = self._normalize_table_structure(table_data)
            
            logger.info(f"页面{page_num}OCR提取表格: {len(table_data)}行")
            return table_data
            
        except Exception as e:
            logger.error(f"OCR提取表格失败(页面{page_num}): {e}")
            return []
    
    def _group_into_rows(self, ocr_lines: List[dict], y_tolerance: int = 10) -> List[List[dict]]:
        """
        将OCR识别的文本按y坐标分组为行
        
        Args:
            ocr_lines: OCR识别结果列表
            y_tolerance: y坐标容差(像素)
            
        Returns:
            分组后的行列表
        """
        if not ocr_lines:
            return []
        
        # 按y坐标排序
        sorted_lines = sorted(ocr_lines, key=lambda x: x['y_center'])
        
        rows = []
        current_row = [sorted_lines[0]]
        current_y = sorted_lines[0]['y_center']
        
        for line in sorted_lines[1:]:
            # 如果y坐标差距小于容差,认为是同一行
            if abs(line['y_center'] - current_y) <= y_tolerance:
                current_row.append(line)
            else:
                # 开始新行
                rows.append(current_row)
                current_row = [line]
                current_y = line['y_center']
        
        # 添加最后一行
        if current_row:
            rows.append(current_row)
        
        return rows
    
    def _remove_empty_columns(self, table: List[List[str]]) -> List[List[str]]:
        """
        删除全空的列
        
        Args:
            table: 原始表格数据
            
        Returns:
            删除空列后的表格
        """
        if not table or len(table) == 0:
            return []
        
        # 找出最大列数
        max_cols = max(len(row) for row in table)
        if max_cols == 0:
            return []
        
        # 检查每一列是否全空
        empty_cols = []
        for col_idx in range(max_cols):
            is_empty = True
            for row in table:
                if col_idx < len(row) and row[col_idx].strip():
                    is_empty = False
                    break
            if is_empty:
                empty_cols.append(col_idx)
        
        # 如果有空列,删除它们
        if empty_cols:
            logger.debug(f"删除{len(empty_cols)}个空列: {empty_cols}")
            new_table = []
            for row in table:
                new_row = [cell for i, cell in enumerate(row) if i not in empty_cols]
                new_table.append(new_row)
            return new_table
        
        return table
    
    def _normalize_table_structure(self, table: List[List[str]]) -> List[List[str]]:
        """
        规范化表格结构,确保所有行的列数一致
        
        Args:
            table: 原始表格数据
            
        Returns:
            规范化后的表格
        """
        if not table:
            return []
        
        # 找出最大列数
        max_cols = max(len(row) for row in table)
        
        # 补齐所有行到最大列数
        normalized_table = []
        for row in table:
            if len(row) < max_cols:
                # 补空字符串
                normalized_row = row + [''] * (max_cols - len(row))
                logger.debug(f"规范化行: {len(row)}列 → {max_cols}列")
            else:
                normalized_row = row
            normalized_table.append(normalized_row)
        
        return normalized_table
    
    def verify_table_content(
        self,
        pdfplumber_table: List[List[str]],
        pdf_path: Path,
        page_num: int
    ) -> List[List[str]]:
        """
        使用OCR验证pdfplumber提取的表格内容
        
        如果检测到可疑内容(如重复行),使用OCR重新提取
        
        Args:
            pdfplumber_table: pdfplumber提取的表格
            pdf_path: PDF文件路径
            page_num: 页码
            
        Returns:
            验证/修正后的表格
        """
        # 检测是否有重复行
        has_duplicate = self._detect_duplicate_rows(pdfplumber_table)
        
        if has_duplicate:
            logger.warning(f"页面{page_num}检测到重复内容,使用OCR重新提取")
            ocr_table = self.extract_table_from_page(pdf_path, page_num)
            if ocr_table and len(ocr_table) > 0:
                logger.info(f"OCR重新提取成功,行数: {len(ocr_table)}")
                return ocr_table
            else:
                logger.warning("OCR提取失败,保留原始表格")
                return pdfplumber_table
        
        return pdfplumber_table
    
    def _detect_duplicate_rows(self, table: List[List[str]]) -> bool:
        """
        检测表格中是否有重复的行内容
        
        Args:
            table: 表格数据
            
        Returns:
            是否有重复
        """
        if len(table) < 2:
            return False
        
        # 检查相邻行的第二列(内容列)是否重复
        for i in range(1, len(table) - 1):
            if len(table[i]) > 1 and len(table[i+1]) > 1:
                content1 = table[i][1].strip()
                content2 = table[i+1][1].strip()
                if content1 and content2 and content1 == content2:
                    logger.debug(f"检测到重复内容: 第{i}行和第{i+1}行")
                    return True
        
        return False


def get_ocr_extractor() -> Optional[OCRTableExtractor]:
    """
    获取OCR提取器实例(单例)
    
    Returns:
        OCR提取器实例,如果不可用则返回None
    """
    if not PADDLEOCR_AVAILABLE:
        return None
    
    if not hasattr(get_ocr_extractor, '_instance'):
        try:
            get_ocr_extractor._instance = OCRTableExtractor()
        except Exception as e:
            logger.error(f"初始化OCR提取器失败: {e}")
            get_ocr_extractor._instance = None
    
    return get_ocr_extractor._instance
