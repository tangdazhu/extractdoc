"""
OCR Engine wrapper for PaddleOCR
Handles OCR initialization and text extraction
"""

import logging
from typing import List, Optional, Dict, Any
from paddleocr import PaddleOCR
from PIL import Image


class OCREngine:
    """
    OCR引擎封装类，提供统一的OCR接口
    """

    def __init__(self, lang="ch", use_gpu=False, show_log=False):
        """
        初始化OCR引擎

        Args:
            lang: 识别语言，默认中文
            use_gpu: 是否使用GPU
            show_log: 是否显示日志
        """
        self.logger = logging.getLogger(__name__)
        try:
            self.ocr = PaddleOCR(
                use_angle_cls=True,
                lang=lang,
                layout=True,
                use_gpu=use_gpu,
                show_log=show_log,
            )
            self.logger.info("OCR engine initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize OCR engine: {e}")
            raise

    def extract_layout_elements(self, image_path: str) -> List[Any]:
        """
        从图片中提取布局元素

        Args:
            image_path: 图片路径

        Returns:
            布局元素列表
        """
        try:
            result = self.ocr.ocr(image_path, cls=True)

            if not result:
                self.logger.warning(f"OCR returned empty result for {image_path}")
                return []

            if isinstance(result, list) and len(result) > 0:
                return result[0] if isinstance(result[0], list) else []

            return []

        except Exception as e:
            self.logger.error(f"Error during OCR extraction from {image_path}: {e}")
            return []

    def extract_text_simple(self, image_path: str) -> str:
        """
        简单文本提取（不使用布局分析）

        Args:
            image_path: 图片路径

        Returns:
            提取的文本
        """
        try:
            result = self.ocr.ocr(image_path, cls=True)

            text_lines = []
            if result and len(result) > 0 and result[0] is not None:
                for line in result[0]:
                    if line and len(line) > 1 and line[1] and len(line[1]) > 0:
                        text_lines.append(line[1][0])

            if not text_lines:
                self.logger.warning(f"No text detected in {image_path}")
                return "No text detected in this image."

            return "\n".join(text_lines)

        except Exception as e:
            self.logger.error(f"Error processing {image_path}: {e}")
            return f"Error processing image: {str(e)}"
