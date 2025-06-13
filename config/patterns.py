"""
Pattern library for OCR text extraction system.

This module contains pattern definitions for text recognition,
content classification, and data extraction.
"""

import re
from typing import Dict, List, Pattern
from dataclasses import dataclass, field


@dataclass
class PatternSet:
    """Container for related regex patterns."""

    name: str
    patterns: List[str] = field(default_factory=list)
    compiled_patterns: List[Pattern] = field(default_factory=list, init=False)

    def __post_init__(self):
        """Compile patterns after initialization."""
        self.compiled_patterns = [re.compile(pattern) for pattern in self.patterns]

    def match(self, text: str) -> bool:
        """Check if any pattern matches the text."""
        return any(pattern.search(text) for pattern in self.compiled_patterns)

    def find_all(self, text: str) -> List[str]:
        """Find all matches for any pattern in the text."""
        matches = []
        for pattern in self.compiled_patterns:
            matches.extend(pattern.findall(text))
        return matches


class PatternLibrary:
    """Library of patterns for various text recognition tasks."""

    def __init__(self):
        """Initialize pattern library with predefined patterns."""
        self._init_content_patterns()
        self._init_data_patterns()
        self._init_table_patterns()
        self._init_formatting_patterns()
        self._init_language_patterns()

    def _init_content_patterns(self):
        """Initialize content classification patterns."""

        self.title_patterns = PatternSet(
            name="title_patterns",
            patterns=[
                r"^[一二三四五六七八九十\d]+[、\.．]\s*.{1,50}$",  # 章节标题
                r"^第[一二三四五六七八九十\d]+[章节部分]\s*.{1,50}$",  # 第X章
                r"^[（(]\s*[一二三四五六七八九十\d]+\s*[)）]\s*.{1,50}$",  # (一)标题
                r"^\d+\s+.{1,100}$",  # 数字开头标题
                r"^[A-Z][A-Z\s]{2,50}$",  # 全大写标题
            ],
        )

        self.subtitle_patterns = PatternSet(
            name="subtitle_patterns",
            patterns=[
                r"^\d+\.\d+\s+.{1,100}$",  # 1.1 子标题
                r"^[（(]\s*\d+\s*[)）]\s*.{1,100}$",  # (1)子标题
                r"^[①②③④⑤⑥⑦⑧⑨⑩]\s*.{1,100}$",  # 圆圈数字
                r"^[⑴⑵⑶⑷⑸⑹⑺⑻⑼⑽]\s*.{1,100}$",  # 括号数字
                r"^[ABCDEFGHIJ]\.\s*.{1,100}$",  # 字母编号
            ],
        )

        self.list_patterns = PatternSet(
            name="list_patterns",
            patterns=[
                r"^[•·▪▫▬★☆]\s*.+$",  # 项目符号
                r"^\d+[\.、]\s*.+$",  # 数字列表
                r"^[a-zA-Z][\.、]\s*.+$",  # 字母列表
                r"^[-−—]\s*.+$",  # 破折号列表
                r"^[○●◎◇◆□■]\s*.+$",  # 几何符号列表
            ],
        )

        self.header_footer_patterns = PatternSet(
            name="header_footer_patterns",
            patterns=[
                r"^\s*[-—]\s*\d+\s*[-—]\s*$",  # -1-
                r"^\s*第?\s*\d+\s*页\s*$",  # 第1页
                r"^\s*\d+\s*/\s*\d+\s*$",  # 1/10
                r"^\s*Page\s+\d+.*$",  # Page 1
                r"^\s*共\s*\d+\s*页\s*$",  # 共10页
            ],
        )

    def _init_data_patterns(self):
        """Initialize data extraction patterns."""

        self.date_patterns = PatternSet(
            name="date_patterns",
            patterns=[
                r"\d{4}[年\-/\.]\d{1,2}[月\-/\.]\d{1,2}[日]?",  # 中文/国际日期
                r"\d{1,2}[月\-/\.]\d{1,2}[日\-/\.]\d{4}[年]?",  # 替代格式
                r"\d{1,2}/\d{1,2}/\d{4}",  # MM/DD/YYYY
                r"\d{4}/\d{1,2}/\d{1,2}",  # YYYY/MM/DD
                r"\d{4}-\d{1,2}-\d{1,2}",  # YYYY-MM-DD
                r"\d{1,2}\.\d{1,2}\.\d{4}",  # DD.MM.YYYY
            ],
        )

        self.time_patterns = PatternSet(
            name="time_patterns",
            patterns=[
                r"\d{1,2}:\d{2}(?::\d{2})?",  # HH:MM or HH:MM:SS
                r"\d{1,2}[点：:]\d{2}[分]?(?:\d{2}[秒]?)?",  # 中文时间格式
                r"\d{1,2}[时]\d{2}[分]?",  # X时Y分
                r"(?:上午|下午|AM|PM)\s*\d{1,2}:\d{2}",  # 带AM/PM
            ],
        )

        self.number_patterns = PatternSet(
            name="number_patterns",
            patterns=[
                r"\b\d+\.\d+\b",  # 小数
                r"\b\d+\b",  # 整数
                r"\b\d{1,3}(?:,\d{3})*\b",  # 千分位数字
                r"[￥¥]\s*\d+(?:\.\d{2})?",  # 人民币
                r"\$\s*\d+(?:\.\d{2})?",  # 美元
                r"\b\d+%\b",  # 百分比
            ],
        )

        self.contact_patterns = PatternSet(
            name="contact_patterns",
            patterns=[
                r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # 邮箱
                r"\b1[3-9]\d{9}\b",  # 中国手机号
                r"\b\d{3,4}-\d{7,8}\b",  # 座机号码
                r"\(\d{3,4}\)\s*\d{7,8}\b",  # 括号格式电话
                r"(?:电话|Tel|Phone)[：:\s]*[\d\-\(\)\s]+",  # 电话标识
            ],
        )

    def _init_table_patterns(self):
        """Initialize table detection patterns."""

        self.table_indicators = PatternSet(
            name="table_indicators",
            patterns=[
                r"[|｜]{2,}",  # 多个竖线
                r"^[-_=]{3,}$",  # 水平分隔线
                r"\b表\s*\d+",  # 表格编号
                r"序号|编号|项目|名称|数量|金额|备注",  # 常见表头
                r"合计|小计|总计",  # 汇总行
            ],
        )

        self.table_headers = PatternSet(
            name="table_headers",
            patterns=[
                r"序号|编号|NO\.|No\.",
                r"项目|名称|品名|产品",
                r"数量|qty|quantity",
                r"单价|price|金额|amount",
                r"规格|型号|specification",
                r"备注|说明|remark",
                r"日期|时间|date|time",
                r"状态|status|进度",
            ],
        )

        self.financial_table_patterns = PatternSet(
            name="financial_table_patterns",
            patterns=[
                r"金额|amount|¥|￥|\$",
                r"收入|支出|income|expense",
                r"合计|总计|total|sum",
                r"借方|贷方|debit|credit",
                r"余额|balance|结余",
            ],
        )

    def _init_formatting_patterns(self):
        """Initialize formatting and structure patterns."""

        self.bold_indicators = PatternSet(
            name="bold_indicators",
            patterns=[
                r"\*\*(.+?)\*\*",  # **bold**
                r"__(.+?)__",  # __bold__
                r"【(.+?)】",  # 【标题】
                r"《(.+?)》",  # 《书名》
            ],
        )

        self.italic_indicators = PatternSet(
            name="italic_indicators",
            patterns=[
                r"\*(.+?)\*",  # *italic*
                r"_(.+?)_",  # _italic_
                r"（(.+?)）",  # （注释）
                r"\((.+?)\)",  # (注释)
            ],
        )

        self.structure_markers = PatternSet(
            name="structure_markers",
            patterns=[
                r"^#+\s+",  # Markdown headers
                r"^\s*[-*+]\s+",  # Markdown lists
                r"^\s*\d+\.\s+",  # Numbered lists
                r"^\s*>\s+",  # Blockquotes
                r"```.*?```",  # Code blocks
            ],
        )

    def _init_language_patterns(self):
        """Initialize language detection patterns."""

        self.chinese_patterns = PatternSet(
            name="chinese_patterns",
            patterns=[
                r"[\u4e00-\u9fff]+",  # 中文字符
                r'[，。！？；：""' "（）【】《》]",  # 中文标点
                r"第[一二三四五六七八九十\d]+[章节条款]",  # 中文序号
            ],
        )

        self.english_patterns = PatternSet(
            name="english_patterns",
            patterns=[
                r"\b[A-Za-z]+\b",  # 英文单词
                r'[.,!?;:"\'()\[\]{}]',  # 英文标点
                r"\b(the|and|or|but|in|on|at|to|for|of|with)\b",  # 常用英文词
            ],
        )

        self.mixed_content_patterns = PatternSet(
            name="mixed_content_patterns",
            patterns=[
                r"[\u4e00-\u9fff]+.*[A-Za-z]+",  # 中英混合
                r"[A-Za-z]+.*[\u4e00-\u9fff]+",  # 英中混合
                r"\d+[\u4e00-\u9fff]+",  # 数字+中文
                r"[\u4e00-\u9fff]+\d+",  # 中文+数字
            ],
        )

    def get_pattern_set(self, name: str) -> PatternSet:
        """
        Get pattern set by name.

        Args:
            name: Name of the pattern set

        Returns:
            PatternSet object or None if not found
        """
        return getattr(self, name, None)

    def detect_content_type(self, text: str) -> str:
        """
        Detect content type based on patterns.

        Args:
            text: Text to analyze

        Returns:
            Detected content type
        """
        if not text:
            return "unknown"

        text_clean = text.strip()

        # Check patterns in order of specificity
        if self.header_footer_patterns.match(text_clean):
            return "header_footer"
        elif self.title_patterns.match(text_clean):
            return "title"
        elif self.subtitle_patterns.match(text_clean):
            return "subtitle"
        elif self.list_patterns.match(text_clean):
            return "list_item"
        elif self.table_indicators.match(text_clean):
            return "table_element"
        else:
            return "paragraph"

    def extract_data_elements(self, text: str) -> Dict[str, List[str]]:
        """
        Extract various data elements from text.

        Args:
            text: Text to analyze

        Returns:
            Dictionary with extracted data elements
        """
        if not text:
            return {}

        return {
            "dates": self.date_patterns.find_all(text),
            "times": self.time_patterns.find_all(text),
            "numbers": self.number_patterns.find_all(text),
            "contacts": self.contact_patterns.find_all(text),
        }

    def is_table_content(self, text: str) -> bool:
        """
        Check if text appears to be table content.

        Args:
            text: Text to check

        Returns:
            True if text appears to be table content
        """
        if not text:
            return False

        # Check for table indicators
        if self.table_indicators.match(text):
            return True

        # Check for common table headers
        if self.table_headers.match(text):
            return True

        # Check for financial table patterns
        if self.financial_table_patterns.match(text):
            return True

        return False

    def detect_language(self, text: str) -> str:
        """
        Detect language of text based on patterns.

        Args:
            text: Text to analyze

        Returns:
            Detected language ('zh', 'en', 'mixed', 'unknown')
        """
        if not text:
            return "unknown"

        has_chinese = self.chinese_patterns.match(text)
        has_english = self.english_patterns.match(text)

        if has_chinese and has_english:
            return "mixed"
        elif has_chinese:
            return "zh"
        elif has_english:
            return "en"
        else:
            return "unknown"

    def clean_ocr_artifacts(self, text: str) -> str:
        """
        Clean common OCR artifacts using patterns.

        Args:
            text: Text to clean

        Returns:
            Cleaned text
        """
        if not text:
            return ""

        cleaned = text

        # Remove table separators
        cleaned = re.sub(r"[|｜]+", "", cleaned)

        # Remove line separators
        cleaned = re.sub(r"^[-_=]{3,}$", "", cleaned, flags=re.MULTILINE)

        # Remove excessive whitespace
        cleaned = re.sub(r"\s+", " ", cleaned)

        return cleaned.strip()

    def get_all_pattern_names(self) -> List[str]:
        """
        Get names of all available pattern sets.

        Returns:
            List of pattern set names
        """
        pattern_names = []
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if isinstance(attr, PatternSet):
                pattern_names.append(attr_name)
        return pattern_names
