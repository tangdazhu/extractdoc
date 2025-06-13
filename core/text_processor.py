"""
Text processing and OCR character fixing
Handles text repair and normalization
"""

import re
import logging
from typing import Dict, Set


class TextProcessor:
    """
    文本处理器，负责OCR字符修复和文本规范化
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # OCR字符修复映射表
        self.character_fixes = {
            "项": "颖",  # 如果OCR将"颖"识别为"项"
            "顼": "颖",  # 如果OCR将"颖"识别为"顼"
            "须": "赟",  # 如果OCR将"赟"识别为"须"
            "贇": "赟",  # 如果OCR将"赟"识别为"贇"
            "廷": "赟",  # 如果OCR将"赟"识别为"廷"
        }

        # 特定名字修复
        self.specific_name_fixes = {
            "姚项": "姚颖",
            "姚顼": "姚颖",
            "李须": "李赟",
            "李廷": "李赟",
            "李贇": "李赟",
        }

        # 需要智能补全的名字
        self.completion_names = {"沈尚容", "周莉", "姚", "李"}

    def fix_ocr_characters(self, text: str) -> str:
        """
        修复OCR识别错误的字符

        Args:
            text: 待修复的文本

        Returns:
            修复后的文本
        """
        if not text:
            return text

        # 应用特定名字修复
        for wrong_name, correct_name in self.specific_name_fixes.items():
            text = text.replace(wrong_name, correct_name)

        # 智能姓名补全
        if any(name in text for name in self.completion_names):
            text = self._apply_name_completion(text)

        return text

    def _apply_name_completion(self, text: str) -> str:
        """
        应用姓名智能补全

        Args:
            text: 待处理文本

        Returns:
            补全后的文本
        """
        # 处理"李"的补全（李赟）
        if "李" in text and "李赟" not in text:
            text = text.replace("李、", "李赟、")
            text = text.replace("李，", "李赟，")
            text = text.replace("李 ", "李赟 ")
            # 最后处理单独的"李"
            if text.strip() == "李":
                text = "李赟"

        # 处理"姚"的补全（姚颖）
        if "姚" in text and "姚颖" not in text:
            text = text.replace("、姚", "、姚颖")
            text = text.replace("姚，", "姚颖，")
            text = text.replace("姚、", "姚颖、")
            text = text.replace("姚 ", "姚颖 ")
            # 最后处理单独的"姚"
            if text.strip() == "姚":
                text = "姚颖"

        return text

    def clean_text(self, text: str) -> str:
        """
        清理文本，移除多余的空白字符

        Args:
            text: 待清理的文本

        Returns:
            清理后的文本
        """
        if not text:
            return text

        # 移除多余的空白字符
        text = re.sub(r"\s+", " ", text)
        # 移除首尾空白
        text = text.strip()

        return text

    def is_date_like(self, text: str) -> bool:
        """
        判断文本是否像日期格式

        Args:
            text: 待判断的文本

        Returns:
            是否为日期格式
        """
        date_patterns = [
            r"\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日]?",  # 2024-03-15, 2024年3月15日
            r"\d{1,2}[-/]\d{1,2}[-/]\d{4}",  # 15/03/2024
            r"\d{4}\.\d{1,2}\.\d{1,2}",  # 2024.03.15
            r"\d{1,2}月\d{1,2}日",  # 3月15日
            r"20\d{2}-\d{2}-\d{2}",  # 2025-01-25 format
        ]

        return any(re.search(pattern, text) for pattern in date_patterns)

    def is_person_name(self, text: str) -> bool:
        """
        判断文本是否像人名

        Args:
            text: 待判断的文本

        Returns:
            True如果文本像人名，False否则
        """
        if not text or len(text) > 4:  # 人名通常不超过4个字符
            return False

        # 检查是否包含数字或特殊字符
        if re.search(r"[0-9\W]", text):
            return False  # 检查是否在已知名字列表中
        return text in self.completion_names or any(
            name in text for name in self.completion_names
        )

    def process_layout_elements(self, layout_elements):
        """
        处理布局元素，提取文本内容 - 完全按照原始文件的逻辑

        Args:
            layout_elements: PaddleOCR返回的布局元素列表

        Returns:
            处理后的文本内容
        """
        try:
            all_text_lines = []

            # 按照原始文件的逻辑处理每个元素
            for element in layout_elements:
                if isinstance(element, dict):
                    element_type = element.get("type", "").lower()
                    if element_type == "text":
                        text_content_list = element.get("res")
                        if isinstance(text_content_list, list):
                            for item in text_content_list:
                                if isinstance(item, tuple) and len(item) == 2:
                                    if isinstance(item[1], tuple) and len(item[1]) == 2:
                                        all_text_lines.append(item[1][0])
                                    elif isinstance(item[0], str):
                                        all_text_lines.append(item[0])
                                elif isinstance(item, str):
                                    all_text_lines.append(item)
                        elif (
                            isinstance(text_content_list, tuple)
                            and len(text_content_list) == 2
                            and isinstance(text_content_list[0], str)
                        ):
                            all_text_lines.append(text_content_list[0])
                elif isinstance(element, list) and len(element) == 2:
                    text_tuple = element[1]
                    if (
                        isinstance(text_tuple, tuple)
                        and len(text_tuple) == 2
                        and isinstance(text_tuple[0], str)
                    ):
                        text_line = text_tuple[0]
                        if text_line.strip():
                            all_text_lines.append(text_line)

            # 处理提取的文本
            if all_text_lines:
                # 应用OCR字符修复
                fixed_lines = []
                for line in all_text_lines:
                    if line.strip():
                        cleaned_text = self.clean_text(line)
                        fixed_text = self.fix_ocr_characters(cleaned_text)
                        fixed_lines.append(fixed_text)

                return "\n".join(fixed_lines) if fixed_lines else "无文本内容"
            else:
                self.logger.warning("未从布局元素中提取到任何文本")
                return "未检测到文本内容"

        except Exception as e:
            self.logger.error(f"处理布局元素时出错: {e}")
            return f"文本处理出错: {str(e)}"
