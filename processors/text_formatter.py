"""
Text formatting module for OCR text extraction.

This module handles text formatting operations including content structure analysis,
paragraph formatting, and document style detection.
"""

import logging
import re
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ContentType(Enum):
    """Content type enumeration."""

    TITLE = "title"
    SUBTITLE = "subtitle"
    PARAGRAPH = "paragraph"
    LIST_ITEM = "list_item"
    TABLE_HEADER = "table_header"
    TABLE_CELL = "table_cell"
    FOOTER = "footer"
    HEADER = "header"


@dataclass
class FormattedContent:
    """Formatted content data structure."""

    text: str
    content_type: ContentType
    level: int = 0
    bbox: Optional[Tuple[int, int, int, int]] = None
    confidence: float = 1.0


class TextFormatter:
    """Handles text formatting and content structure analysis."""

    def __init__(self):
        self.logger = logger
        self._init_patterns()

    def _init_patterns(self):
        """Initialize regex patterns for content detection."""
        self.patterns = {
            "title": [
                r"^[一二三四五六七八九十\d]+[、\.．]\s*.{1,50}$",  # 章节标题
                r"^第[一二三四五六七八九十\d]+[章节部分]\s*.{1,50}$",  # 第X章
                r"^[（(]\s*[一二三四五六七八九十\d]+\s*[)）]\s*.{1,50}$",  # (一)标题
            ],
            "subtitle": [
                r"^\d+\.\d+\s+.{1,100}$",  # 1.1 子标题
                r"^[（(]\s*\d+\s*[)）]\s*.{1,100}$",  # (1)子标题
                r"^[①②③④⑤⑥⑦⑧⑨⑩]\s*.{1,100}$",  # 圆圈数字
            ],
            "list_item": [
                r"^[•·▪▫▬★☆]\s*.+$",  # 项目符号
                r"^\d+[\.、]\s*.+$",  # 数字列表
                r"^[a-zA-Z][\.、]\s*.+$",  # 字母列表
            ],
            "page_number": [
                r"^\s*[-—]\s*\d+\s*[-—]\s*$",  # -1-
                r"^\s*第?\s*\d+\s*页\s*$",  # 第1页
                r"^\s*\d+\s*/\s*\d+\s*$",  # 1/10
            ],
            "date_time": [
                r"\d{4}[年\-/\.]\d{1,2}[月\-/\.]\d{1,2}[日]?",  # 日期
                r"\d{1,2}:\d{2}(:\d{2})?",  # 时间
            ],
        }

    def analyze_content_structure(
        self, text_elements: List[Dict]
    ) -> List[FormattedContent]:
        """
        Analyze content structure and classify text elements.

        Args:
            text_elements: List of text element dictionaries

        Returns:
            List of formatted content objects
        """
        if not text_elements:
            return []

        try:
            formatted_contents = []

            for element in text_elements:
                formatted_content = self._classify_text_element(element)
                if formatted_content:
                    formatted_contents.append(formatted_content)

            # Post-process to improve classification
            self._refine_classification(formatted_contents)

            return formatted_contents

        except Exception as e:
            self.logger.error(f"Error analyzing content structure: {e}")
            return []

    def _classify_text_element(self, element: Dict) -> Optional[FormattedContent]:
        """Classify a single text element."""
        text = element.get("text", "").strip()
        if not text:
            return None

        bbox = element.get("bbox")
        confidence = element.get("confidence", 1.0)

        # Check for different content types
        content_type, level = self._detect_content_type(text)

        return FormattedContent(
            text=text,
            content_type=content_type,
            level=level,
            bbox=bbox,
            confidence=confidence,
        )

    def _detect_content_type(self, text: str) -> Tuple[ContentType, int]:
        """Detect content type and hierarchy level."""
        text_clean = text.strip()

        # Check for page numbers first (often false positives)
        if self._matches_patterns(text_clean, self.patterns["page_number"]):
            return ContentType.FOOTER, 0

        # Check for titles
        for i, pattern in enumerate(self.patterns["title"]):
            if re.match(pattern, text_clean):
                return ContentType.TITLE, i + 1

        # Check for subtitles
        for i, pattern in enumerate(self.patterns["subtitle"]):
            if re.match(pattern, text_clean):
                return ContentType.SUBTITLE, i + 1

        # Check for list items
        if self._matches_patterns(text_clean, self.patterns["list_item"]):
            return ContentType.LIST_ITEM, 0

        # Check text length and characteristics for further classification
        if len(text_clean) < 10 and text_clean.isupper():
            return ContentType.HEADER, 0
        elif len(text_clean) > 100:
            return ContentType.PARAGRAPH, 0
        else:
            return ContentType.PARAGRAPH, 0

    def _matches_patterns(self, text: str, patterns: List[str]) -> bool:
        """Check if text matches any of the given patterns."""
        for pattern in patterns:
            if re.match(pattern, text):
                return True
        return False

    def _refine_classification(self, contents: List[FormattedContent]):
        """Refine classification based on context."""
        for i, content in enumerate(contents):
            # Look at surrounding context
            prev_content = contents[i - 1] if i > 0 else None
            next_content = contents[i + 1] if i < len(contents) - 1 else None

            # Refine based on position and context
            self._refine_single_classification(content, prev_content, next_content)

    def _refine_single_classification(
        self,
        content: FormattedContent,
        prev_content: Optional[FormattedContent],
        next_content: Optional[FormattedContent],
    ):
        """Refine classification for a single content item."""
        # If short text between titles, likely a subtitle
        if (
            content.content_type == ContentType.PARAGRAPH
            and len(content.text) < 50
            and prev_content
            and prev_content.content_type == ContentType.TITLE
        ):
            content.content_type = ContentType.SUBTITLE
            content.level = 1

    def format_content_for_docx(self, contents: List[FormattedContent]) -> List[Dict]:
        """
        Format content for DOCX export.

        Args:
            contents: List of formatted content objects

        Returns:
            List of formatting instructions for DOCX
        """
        docx_elements = []

        for content in contents:
            element = self._create_docx_element(content)
            if element:
                docx_elements.append(element)

        return docx_elements

    def _create_docx_element(self, content: FormattedContent) -> Optional[Dict]:
        """Create DOCX element from formatted content."""
        if not content.text.strip():
            return None

        element = {"text": content.text, "type": content.content_type.value}

        # Add formatting based on content type
        if content.content_type == ContentType.TITLE:
            element.update(
                {
                    "style": "Heading 1",
                    "bold": True,
                    "size": 16
                    + (4 - content.level) * 2,  # Larger for higher level titles
                }
            )
        elif content.content_type == ContentType.SUBTITLE:
            element.update(
                {
                    "style": "Heading 2",
                    "bold": True,
                    "size": 14 + (3 - content.level) * 1,
                }
            )
        elif content.content_type == ContentType.LIST_ITEM:
            element.update({"style": "List Paragraph", "bullet": True})
        elif content.content_type == ContentType.PARAGRAPH:
            element.update({"style": "Normal", "size": 12})
        elif content.content_type in [ContentType.HEADER, ContentType.FOOTER]:
            element.update({"style": "Header", "size": 10, "italic": True})

        return element

    def detect_document_style(self, contents: List[FormattedContent]) -> str:
        """
        Detect the overall document style (PPT-like vs DOCX-like).

        Args:
            contents: List of formatted content objects

        Returns:
            Document style ('ppt' or 'docx')
        """
        if not contents:
            return "docx"

        # Count different content types
        type_counts = {}
        for content in contents:
            content_type = content.content_type
            type_counts[content_type] = type_counts.get(content_type, 0) + 1

        total_contents = len(contents)
        title_ratio = type_counts.get(ContentType.TITLE, 0) / total_contents
        paragraph_ratio = type_counts.get(ContentType.PARAGRAPH, 0) / total_contents

        # PPT-like documents have more titles and shorter paragraphs
        if title_ratio > 0.3 or (title_ratio > 0.15 and paragraph_ratio < 0.5):
            return "ppt"
        else:
            return "docx"

    def merge_fragmented_text(
        self, contents: List[FormattedContent], merge_threshold: int = 50
    ) -> List[FormattedContent]:
        """
        Merge fragmented text that belongs together.

        Args:
            contents: List of formatted content objects
            merge_threshold: Distance threshold for merging (in pixels)

        Returns:
            List with merged content
        """
        if not contents:
            return []

        merged_contents = []
        current_group = []

        for content in contents:
            if not current_group:
                current_group.append(content)
                continue

            # Check if content should be merged with current group
            if self._should_merge_contents(current_group[-1], content, merge_threshold):
                current_group.append(content)
            else:
                # Finalize current group and start new one
                merged_content = self._merge_content_group(current_group)
                if merged_content:
                    merged_contents.append(merged_content)
                current_group = [content]

        # Handle last group
        if current_group:
            merged_content = self._merge_content_group(current_group)
            if merged_content:
                merged_contents.append(merged_content)

        return merged_contents

    def _should_merge_contents(
        self, content1: FormattedContent, content2: FormattedContent, threshold: int
    ) -> bool:
        """Check if two contents should be merged."""
        # Must be same type to merge
        if content1.content_type != content2.content_type:
            return False

        # Don't merge titles or headers
        if content1.content_type in [
            ContentType.TITLE,
            ContentType.HEADER,
            ContentType.FOOTER,
        ]:
            return False

        # Check spatial proximity if bbox available
        if content1.bbox and content2.bbox:
            _, y1_1, _, y1_2 = content1.bbox
            _, y2_1, _, y2_2 = content2.bbox

            # Check vertical distance
            vertical_gap = y2_1 - y1_2
            if vertical_gap > threshold:
                return False

        # Check text characteristics
        text1 = content1.text.strip()
        text2 = content2.text.strip()

        # Merge if one seems to be continuation of the other
        if text1.endswith(("，", ",", "；", ";")) or not text1.endswith(
            ("。", ".", "！", "!", "？", "?")
        ):
            return True

        return False

    def _merge_content_group(
        self, group: List[FormattedContent]
    ) -> Optional[FormattedContent]:
        """Merge a group of content objects."""
        if not group:
            return None

        if len(group) == 1:
            return group[0]

        # Merge text
        merged_text = " ".join(content.text.strip() for content in group)

        # Use properties from first item
        first_content = group[0]

        # Calculate merged bbox
        merged_bbox = None
        if first_content.bbox:
            bboxes = [content.bbox for content in group if content.bbox]
            if bboxes:
                x1 = min(bbox[0] for bbox in bboxes)
                y1 = min(bbox[1] for bbox in bboxes)
                x2 = max(bbox[2] for bbox in bboxes)
                y2 = max(bbox[3] for bbox in bboxes)
                merged_bbox = (x1, y1, x2, y2)  # Average confidence
        avg_confidence = sum(content.confidence for content in group) / len(group)

        return FormattedContent(
            text=merged_text,
            content_type=first_content.content_type,
            level=first_content.level,
            bbox=merged_bbox,
            confidence=avg_confidence,
        )

    def format_text_content(
        self, processed_text, content_analysis: Dict[str, Any]
    ) -> str:
        """
        Format text content from processed text into a readable string.

        Args:
            processed_text: Processed text string or list of processed layout elements
            content_analysis: Analysis results from layout analyzer

        Returns:
            Formatted text content as a string
        """
        try:
            # 如果输入是字符串，直接处理
            if isinstance(processed_text, str):
                if not processed_text or processed_text.strip() == "":
                    return "无文本内容"

                # 简单格式化：按行分割并清理
                lines = processed_text.split("\n")
                formatted_lines = []

                for line in lines:
                    line = line.strip()
                    if line and line not in formatted_lines:  # 去重
                        formatted_lines.append(line)

                return "\n".join(formatted_lines) if formatted_lines else "无文本内容"

            # 如果输入是列表（向后兼容）
            processed_elements = (
                processed_text if isinstance(processed_text, list) else []
            )

            if not processed_elements:
                return "无文本内容"

            # Analyze content structure
            formatted_contents = self.analyze_content_structure(processed_elements)

            if not formatted_contents:
                # Fallback: extract text directly from elements
                text_parts = []
                for element in processed_elements:
                    text = element.get("text", "").strip()
                    if text:
                        text_parts.append(text)
                return "\n".join(text_parts) if text_parts else "无文本内容"

            # Format content based on structure
            output_lines = []

            for content in formatted_contents:
                text = content.text.strip()
                if not text:
                    continue

                # Format based on content type
                if content.content_type == ContentType.TITLE:
                    # Add extra spacing for titles
                    if output_lines:
                        output_lines.append("")
                    output_lines.append(f"# {text}")
                    output_lines.append("")

                elif content.content_type == ContentType.SUBTITLE:
                    if output_lines:
                        output_lines.append("")
                    output_lines.append(f"## {text}")

                elif content.content_type == ContentType.LIST_ITEM:
                    output_lines.append(f"• {text}")

                elif content.content_type == ContentType.HEADER:
                    output_lines.append(f"**{text}**")

                elif content.content_type == ContentType.FOOTER:
                    # Skip page numbers and footers
                    continue

                else:  # PARAGRAPH and others
                    output_lines.append(text)

            # Join with newlines and clean up
            result = "\n".join(output_lines)

            # Clean up multiple consecutive newlines
            result = re.sub(r"\n{3,}", "\n\n", result)

            # Remove leading/trailing whitespace
            result = result.strip()

            return result if result else "无文本内容"

        except Exception as e:
            self.logger.error(f"格式化文本内容时出错: {e}")
            # Fallback: 如果输入是字符串，直接返回
            if isinstance(processed_text, str):
                return processed_text if processed_text else "文本处理出错"

            # 如果是列表，尝试简单提取
            try:
                text_parts = []
                for element in processed_text:
                    text = element.get("text", "").strip()
                    if text:
                        text_parts.append(text)
                return "\n".join(text_parts) if text_parts else "文本处理出错"
            except:
                return "文本处理出错"
