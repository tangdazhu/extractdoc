# -*- coding: utf-8 -*-
"""
文本工具模块
提供文本处理相关的实用函数
"""

import re
import string
from typing import List, Any, Union, Optional


class TextUtils:
    """文本处理工具类"""

    @staticmethod
    def natural_sort_key(s):
        """Sort strings with numbers in natural order (1.jpg, 2.jpg, ..., 10.jpg)."""
        return [
            int(text) if text.isdigit() else text.lower()
            for text in re.split(r"(\d+)", s)
        ]

    @staticmethod
    def clean_text(text: str) -> str:
        """
        清理文本内容
        - 去除多余空白字符
        - 规范化换行符
        """
        if not text:
            return ""

        # 统一换行符
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # 去除行首行尾空白
        lines = [line.strip() for line in text.split("\n")]

        # 去除空行
        lines = [line for line in lines if line]

        return "\n".join(lines)

    @staticmethod
    def normalize_whitespace(text: str) -> str:
        """规范化空白字符"""
        if not text:
            return ""

        # 将多个空格替换为单个空格
        text = re.sub(r"\s+", " ", text)

        return text.strip()

    @staticmethod
    def remove_punctuation(text: str) -> str:
        """移除标点符号"""
        if not text:
            return ""

        # 创建翻译表，移除所有标点符号
        translator = str.maketrans("", "", string.punctuation)
        return text.translate(translator)

    @staticmethod
    def split_by_sentences(text: str) -> List[str]:
        """按句子分割文本"""
        if not text:
            return []

        # 按常见句子结束符分割
        sentences = re.split(r"[.!?。！？]+", text)

        # 清理并过滤空句子
        sentences = [s.strip() for s in sentences if s.strip()]

        return sentences

    @staticmethod
    def extract_numbers(text: str) -> List[int]:
        """从文本中提取所有数字"""
        if not text:
            return []

        # 使用正则表达式查找所有数字
        numbers = re.findall(r"\d+", text)

        return [int(num) for num in numbers]

    @staticmethod
    def format_filename(filename: str) -> str:
        """
        格式化文件名，移除非法字符
        """
        if not filename:
            return "untitled"

        # 移除或替换非法字符
        illegal_chars = r'[<>:"/\\|?*]'
        filename = re.sub(illegal_chars, "_", filename)

        # 移除多余的空格和点
        filename = re.sub(r"\s+", " ", filename)
        filename = filename.strip(". ")

        # 确保文件名不为空
        if not filename:
            filename = "untitled"

        return filename

    @staticmethod
    def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
        """
        截断文本到指定长度
        """
        if not text:
            return ""

        if len(text) <= max_length:
            return text

        return text[: max_length - len(suffix)] + suffix

    @staticmethod
    def is_empty_or_whitespace(text: str) -> bool:
        """检查文本是否为空或只包含空白字符"""
        return not text or text.isspace()

    @staticmethod
    def contains_chinese(text: str) -> bool:
        """检查文本是否包含中文字符"""
        if not text:
            return False

        # 检查是否包含中文字符范围
        chinese_pattern = re.compile(r"[\u4e00-\u9fff]")
        return bool(chinese_pattern.search(text))

    @staticmethod
    def word_count(text: str) -> int:
        """统计单词数量（对中文按字符计算）"""
        if not text:
            return 0

        # 如果包含中文，按字符计算
        if TextUtils.contains_chinese(text):
            # 移除空白字符后计算字符数
            return len(re.sub(r"\s+", "", text))
        else:
            # 英文按单词计算
            words = text.split()
            return len(words)

    @staticmethod
    def capitalize_words(text: str) -> str:
        """将每个单词的首字母大写"""
        if not text:
            return ""

        return " ".join(word.capitalize() for word in text.split())

    @staticmethod
    def remove_extra_newlines(text: str) -> str:
        """移除多余的换行符"""
        if not text:
            return ""

        # 将多个连续换行符替换为单个换行符
        text = re.sub(r"\n\s*\n", "\n", text)

        return text.strip()

    @staticmethod
    def extract_emails(text: str) -> List[str]:
        """从文本中提取邮箱地址"""
        if not text:
            return []

        email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        emails = re.findall(email_pattern, text)

        return emails

    @staticmethod
    def extract_urls(text: str) -> List[str]:
        """从文本中提取URL"""
        if not text:
            return []

        url_pattern = r"https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:[\w.])*)?)?"
        urls = re.findall(url_pattern, text)

        return urls

    @staticmethod
    def ensure_string(value: Any) -> str:
        """确保值是字符串类型"""
        if value is None:
            return ""
        elif isinstance(value, str):
            return value
        else:
            return str(value)

    @staticmethod
    def join_with_separator(items: List[str], separator: str = "\n") -> str:
        """用指定分隔符连接字符串列表"""
        if not items:
            return ""

        # 过滤空字符串
        valid_items = [item for item in items if item and item.strip()]

        return separator.join(valid_items)
