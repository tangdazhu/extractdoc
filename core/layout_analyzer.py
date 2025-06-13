"""
Layout analysis and content classification
Handles document structure analysis
"""

import re
import logging
from typing import List, Dict, Any, Optional


class LayoutAnalyzer:
    """
    布局分析器，负责分析文档结构和内容分类
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def analyze_content_structure(self, text: str) -> List[Dict[str, Any]]:
        """
        分析文本内容结构

        Args:
            text: 待分析的文本

        Returns:
            结构化的内容列表
        """
        if not text or not text.strip():
            return [text] if text else []

        # 分割行
        raw_lines = re.split(r"[\n\r]+", text)
        lines = [line.strip() for line in raw_lines if line.strip()]

        if not lines:
            return [text.strip()] if text.strip() else []

        # 分析结构
        formatted_content = []
        current_main_section = None

        for i, line in enumerate(lines):
            formatted_line = self._analyze_line_type(
                line, current_main_section, lines, i
            )

            if formatted_line:
                if formatted_line.get("type") in [
                    "numbered_main",
                    "numbered_chinese",
                    "section_header",
                ]:
                    current_main_section = formatted_line.get("text")
                elif formatted_line.get("type") == "title":
                    current_main_section = None

                formatted_content.append(formatted_line)

        return formatted_content

    def _analyze_line_type(
        self,
        line: str,
        current_section: Optional[str],
        all_lines: List[str],
        line_index: int,
    ) -> Optional[Dict[str, Any]]:
        """
        分析单行的类型

        Args:
            line: 当前行文本
            current_section: 当前主节
            all_lines: 所有行
            line_index: 当前行索引

        Returns:
            格式化后的行信息
        """
        # 主标题 (全大写)
        if (
            line.upper() == line
            and len(line) <= 20
            and any(
                keyword in line.upper()
                for keyword in ["CONTENT", "WHITEPAPER", "目录", "内容"]
            )
        ):
            return {"type": "title", "text": line, "level": 0}

        # 文档描述/副标题
        if any(
            keyword in line.lower()
            for keyword in ["whitepaper", "solution", "开发团队", "系统架构"]
        ):
            return {"type": "subtitle", "text": line, "level": 0}

        # 主编号节 (1. 2. 3.)
        match = re.match(r"^\d+[.、]\s*(.+)", line)
        if match:
            return {
                "type": "numbered_main",
                "text": match.group(1),
                "number": line.split(".")[0] if "." in line else line.split("、")[0],
                "level": 1,
            }

        # 中文编号节 (一、二、三、)
        match = re.match(r"^[一二三四五六七八九十]+[、.]\s*(.+)", line)
        if match:
            return {
                "type": "numbered_chinese",
                "text": match.group(1),
                "number": line.split("、")[0],
                "level": 1,
            }

        # 子项目符号 (·)
        if line.startswith("·"):
            text_content = line[1:].strip()
            return {
                "type": "bullet_sub",
                "text": text_content,
                "level": 2,
                "parent": current_section,
            }

        # 其他项目符号
        if line.startswith(("•", "-", "*", "○", "●")):
            text_content = line[1:].strip()
            return {
                "type": "bullet",
                "text": text_content,
                "level": 2 if current_section else 1,
                "parent": current_section,
            }

        # 括号编号 (1) (2) (3)
        match = re.match(r"^[（(]\d+[）)]\s*(.+)", line)
        if match:
            return {
                "type": "numbered_paren",
                "text": match.group(1),
                "number": line.split(")")[0].strip("()（）"),
                "level": 2,
                "parent": current_section,
            }

        # 独立数字 (可能需要与下一行合并)
        if re.match(r"^\d+[.]\s*$", line) and line_index + 1 < len(all_lines):
            next_line = all_lines[line_index + 1]
            if not re.match(r"^\d+[.、]", next_line) and not next_line.startswith(
                ("·", "•", "-")
            ):
                return {
                    "type": "numbered_main",
                    "text": next_line,
                    "number": line.rstrip("."),
                    "level": 1,
                }

        # 技术术语或节标题
        if len(line) <= 50 and any(
            keyword in line
            for keyword in [
                "开发",
                "技术",
                "平台",
                "框架",
                "选型",
                "架构",
                "模型",
                "评估",
                "安全",
                "合规",
                "案例",
                "实践",
                "场景",
            ]
        ):

            if current_section and len(line) <= 30:
                return {
                    "type": "section_sub",
                    "text": line,
                    "level": 2,
                    "parent": current_section,
                }
            else:
                return {"type": "section_header", "text": line, "level": 1}

        # 常规文本
        if current_section and len(line) <= 40:
            return {
                "type": "text_sub",
                "text": line,
                "level": 2,
                "parent": current_section,
            }
        else:
            return {"type": "text", "text": line, "level": 0}

    def detect_content_format(self, formatted_content: List[Dict[str, Any]]) -> str:
        """
        检测内容格式类型

        Args:
            formatted_content: 格式化后的内容

        Returns:
            格式类型: 'ppt', 'docx', 'auto'
        """
        if not formatted_content:
            return "docx"

        # 统计不同类型的元素
        has_main_sections = any(
            item.get("type") == "numbered_main" for item in formatted_content
        )
        has_bullets = any(
            item.get("type") in ["bullet_sub", "bullet"] for item in formatted_content
        )
        has_title = any(item.get("type") == "title" for item in formatted_content)

        # 如果有标题、主节和项目符号，推荐PPT格式
        if has_title and has_main_sections and has_bullets:
            return "ppt"
        else:
            return "docx"

    def analyze_layout(self, layout_elements: List[Any]) -> Dict[str, Any]:
        """
        分析OCR提取的布局元素

        Args:
            layout_elements: OCR提取的布局元素列表

        Returns:
            布局分析结果
        """
        try:
            if not layout_elements:
                return {
                    "elements": [],
                    "text_content": "",
                    "structure_type": "unknown",
                    "formatted_content": [],
                }

            # 提取文本内容
            text_content = self._extract_text_from_elements(layout_elements)

            # 分析内容结构
            formatted_content = self.analyze_content_structure(text_content)

            # 检测内容格式
            structure_type = self.detect_content_format(formatted_content)

            # 提取布局信息
            layout_info = self._extract_layout_info(layout_elements)

            return {
                "elements": layout_elements,
                "text_content": text_content,
                "structure_type": structure_type,
                "formatted_content": formatted_content,
                "layout_info": layout_info,
            }

        except Exception as e:
            self.logger.error(f"Error analyzing layout: {e}")
            return {
                "elements": layout_elements or [],
                "text_content": "",
                "structure_type": "unknown",
                "formatted_content": [],
                "layout_info": {},
            }

    def _extract_text_from_elements(self, layout_elements: List[Any]) -> str:
        """
        从布局元素中提取文本内容

        Args:
            layout_elements: OCR布局元素

        Returns:
            提取的文本内容
        """
        try:
            text_lines = []

            if not layout_elements:
                return ""

            for element in layout_elements:
                if isinstance(element, (list, tuple)) and len(element) >= 2:
                    # PaddleOCR format: [bbox, (text, confidence)]
                    if len(element) == 2 and isinstance(element[1], (list, tuple)):
                        text = element[1][0] if element[1] else ""
                        if text and isinstance(text, str):
                            text_lines.append(text.strip())
                    # Alternative format: [bbox, text, confidence]
                    elif len(element) >= 3:
                        text = element[1] if isinstance(element[1], str) else ""
                        if text:
                            text_lines.append(text.strip())

            return "\n".join(text_lines)

        except Exception as e:
            self.logger.error(f"Error extracting text from elements: {e}")
            return ""

    def _extract_layout_info(self, layout_elements: List[Any]) -> Dict[str, Any]:
        """
        提取布局信息（坐标、字体大小等）

        Args:
            layout_elements: OCR布局元素

        Returns:
            布局信息字典
        """
        try:
            layout_info = {
                "text_blocks": [],
                "total_elements": len(layout_elements) if layout_elements else 0,
                "bbox_info": [],
            }

            if not layout_elements:
                return layout_info

            for i, element in enumerate(layout_elements):
                if isinstance(element, (list, tuple)) and len(element) >= 2:
                    try:
                        bbox = element[0] if element[0] else []
                        text_info = element[1] if len(element) > 1 else []

                        text = ""
                        confidence = 0.0

                        if isinstance(text_info, (list, tuple)) and len(text_info) >= 2:
                            text = text_info[0] if text_info[0] else ""
                            confidence = text_info[1] if text_info[1] else 0.0
                        elif isinstance(text_info, str):
                            text = text_info

                        block_info = {
                            "index": i,
                            "text": text,
                            "confidence": confidence,
                            "bbox": bbox,
                        }

                        layout_info["text_blocks"].append(block_info)
                        if bbox:
                            layout_info["bbox_info"].append(bbox)

                    except Exception as block_error:
                        self.logger.warning(
                            f"Error processing layout element {i}: {block_error}"
                        )
                        continue

            return layout_info

        except Exception as e:
            self.logger.error(f"Error extracting layout info: {e}")
            return {
                "text_blocks": [],
                "total_elements": 0,
                "bbox_info": [],
            }
