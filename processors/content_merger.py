"""
Content merger module for OCR text extraction.

This module handles merging different types of content (text, tables, images)
into a unified document structure.
"""

import logging
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum

from .text_formatter import FormattedContent, ContentType

logger = logging.getLogger(__name__)


class MergeStrategy(Enum):
    """Content merging strategies."""

    PRESERVE_ORDER = "preserve_order"
    GROUP_BY_TYPE = "group_by_type"
    OPTIMIZE_LAYOUT = "optimize_layout"


@dataclass
class MergedElement:
    """Unified element for merged content."""

    content: Union[FormattedContent, List[List[str]], Dict]
    element_type: str  # 'text', 'table', 'image'
    position: int
    bbox: Optional[tuple] = None
    metadata: Optional[Dict] = None


class ContentMerger:
    """Handles merging of different content types into unified document structure."""

    def __init__(self, strategy: MergeStrategy = MergeStrategy.PRESERVE_ORDER):
        self.logger = logger
        self.strategy = strategy

    def merge_content(
        self,
        text_contents: List[FormattedContent],
        tables: List[List[List[str]]],
        table_positions: Optional[List[Dict]] = None,
        images: Optional[List[Dict]] = None,
    ) -> List[MergedElement]:
        """
        Merge different types of content into unified structure.

        Args:
            text_contents: List of formatted text content
            tables: List of table structures
            table_positions: Optional table position information
            images: Optional image information

        Returns:
            List of merged elements in document order
        """
        try:
            elements = []

            # Convert text contents to merged elements
            for i, text_content in enumerate(text_contents):
                element = MergedElement(
                    content=text_content,
                    element_type="text",
                    position=self._get_text_position(text_content),
                    bbox=text_content.bbox,
                    metadata={"original_index": i},
                )
                elements.append(element)

            # Convert tables to merged elements
            for i, table in enumerate(tables):
                position_info = (
                    table_positions[i]
                    if table_positions and i < len(table_positions)
                    else {}
                )
                element = MergedElement(
                    content=table,
                    element_type="table",
                    position=position_info.get(
                        "position", i * 1000
                    ),  # Default positioning
                    bbox=position_info.get("bbox"),
                    metadata={"table_index": i, "position_info": position_info},
                )
                elements.append(element)

            # Convert images to merged elements
            if images:
                for i, image in enumerate(images):
                    element = MergedElement(
                        content=image,
                        element_type="image",
                        position=image.get("position", (i + len(tables)) * 1000),
                        bbox=image.get("bbox"),
                        metadata={"image_index": i},
                    )
                    elements.append(element)

            # Apply merging strategy
            return self._apply_merge_strategy(elements)

        except Exception as e:
            self.logger.error(f"Error merging content: {e}")
            return []

    def _get_text_position(self, text_content: FormattedContent) -> int:
        """Calculate position for text content."""
        if text_content.bbox:
            # Use Y coordinate as primary position indicator
            return text_content.bbox[1]
        return 0

    def _apply_merge_strategy(
        self, elements: List[MergedElement]
    ) -> List[MergedElement]:
        """Apply the configured merge strategy."""
        if self.strategy == MergeStrategy.PRESERVE_ORDER:
            return self._preserve_order_strategy(elements)
        elif self.strategy == MergeStrategy.GROUP_BY_TYPE:
            return self._group_by_type_strategy(elements)
        elif self.strategy == MergeStrategy.OPTIMIZE_LAYOUT:
            return self._optimize_layout_strategy(elements)
        else:
            return sorted(elements, key=lambda x: x.position)

    def _preserve_order_strategy(
        self, elements: List[MergedElement]
    ) -> List[MergedElement]:
        """Preserve original spatial order of elements."""
        return sorted(elements, key=lambda x: x.position)

    def _group_by_type_strategy(
        self, elements: List[MergedElement]
    ) -> List[MergedElement]:
        """Group elements by type while maintaining relative order."""
        text_elements = [e for e in elements if e.element_type == "text"]
        table_elements = [e for e in elements if e.element_type == "table"]
        image_elements = [e for e in elements if e.element_type == "image"]

        # Sort each group by position
        text_elements.sort(key=lambda x: x.position)
        table_elements.sort(key=lambda x: x.position)
        image_elements.sort(key=lambda x: x.position)

        # Combine in order: text, tables, images
        return text_elements + table_elements + image_elements

    def _optimize_layout_strategy(
        self, elements: List[MergedElement]
    ) -> List[MergedElement]:
        """Optimize layout by analyzing spatial relationships."""
        # Sort by position first
        sorted_elements = sorted(elements, key=lambda x: x.position)

        # Group elements that are spatially close
        groups = self._group_spatially_close_elements(sorted_elements)

        # Optimize each group
        optimized_elements = []
        for group in groups:
            optimized_group = self._optimize_group_layout(group)
            optimized_elements.extend(optimized_group)

        return optimized_elements

    def _group_spatially_close_elements(
        self, elements: List[MergedElement], threshold: int = 100
    ) -> List[List[MergedElement]]:
        """Group elements that are spatially close."""
        if not elements:
            return []

        groups = []
        current_group = [elements[0]]

        for i in range(1, len(elements)):
            current_element = elements[i]
            previous_element = elements[i - 1]

            # Check if elements are close enough to group
            if self._are_elements_close(previous_element, current_element, threshold):
                current_group.append(current_element)
            else:
                groups.append(current_group)
                current_group = [current_element]

        if current_group:
            groups.append(current_group)

        return groups

    def _are_elements_close(
        self, element1: MergedElement, element2: MergedElement, threshold: int
    ) -> bool:
        """Check if two elements are spatially close."""
        if not element1.bbox or not element2.bbox:
            # If no bbox info, use position difference
            return abs(element1.position - element2.position) <= threshold

        # Calculate vertical distance between elements
        _, y1_1, _, y1_2 = element1.bbox
        _, y2_1, _, y2_2 = element2.bbox

        vertical_gap = y2_1 - y1_2
        return vertical_gap <= threshold

    def _optimize_group_layout(self, group: List[MergedElement]) -> List[MergedElement]:
        """Optimize layout within a group of elements."""
        if len(group) <= 1:
            return group

        # Separate text and non-text elements
        text_elements = [e for e in group if e.element_type == "text"]
        non_text_elements = [e for e in group if e.element_type != "text"]

        # Process text elements to group related content
        optimized_text = self._optimize_text_elements(text_elements)

        # Merge back with non-text elements, maintaining spatial order
        all_elements = optimized_text + non_text_elements
        return sorted(all_elements, key=lambda x: x.position)

    def _optimize_text_elements(
        self, text_elements: List[MergedElement]
    ) -> List[MergedElement]:
        """Optimize text element ordering and grouping."""
        if not text_elements:
            return []

        # Group related text elements (e.g., titles with their content)
        optimized = []
        i = 0

        while i < len(text_elements):
            current = text_elements[i]

            if isinstance(current.content, FormattedContent):
                if current.content.content_type == ContentType.TITLE:
                    # Look for related content after title
                    title_group = [current]
                    j = i + 1

                    while j < len(text_elements) and self._is_related_to_title(
                        text_elements[j], current
                    ):
                        title_group.append(text_elements[j])
                        j += 1

                    optimized.extend(title_group)
                    i = j
                else:
                    optimized.append(current)
                    i += 1
            else:
                optimized.append(current)
                i += 1

        return optimized

    def _is_related_to_title(
        self, element: MergedElement, title_element: MergedElement
    ) -> bool:
        """Check if an element is related to a title."""
        if not isinstance(element.content, FormattedContent):
            return False

        content = element.content

        # Related if it's a subtitle or paragraph immediately following
        if content.content_type in [ContentType.SUBTITLE, ContentType.PARAGRAPH]:
            return True

        # Related if it's another title of lower level
        if content.content_type == ContentType.TITLE and isinstance(
            title_element.content, FormattedContent
        ):
            return content.level > title_element.content.level

        return False

    def create_document_structure(self, merged_elements: List[MergedElement]) -> Dict:
        """
        Create a structured document representation from merged elements.

        Args:
            merged_elements: List of merged elements

        Returns:
            Document structure dictionary
        """
        try:
            document = {
                "title": "",
                "sections": [],
                "metadata": {
                    "total_elements": len(merged_elements),
                    "text_count": 0,
                    "table_count": 0,
                    "image_count": 0,
                },
            }

            current_section = None

            for element in merged_elements:
                # Update metadata counts
                document["metadata"][f"{element.element_type}_count"] += 1

                if element.element_type == "text" and isinstance(
                    element.content, FormattedContent
                ):
                    text_content = element.content

                    if text_content.content_type == ContentType.TITLE:
                        # Start new section
                        if current_section:
                            document["sections"].append(current_section)

                        current_section = {
                            "title": text_content.text,
                            "level": text_content.level,
                            "content": [],
                        }

                        # Set document title if this is the first major title
                        if not document["title"] and text_content.level == 1:
                            document["title"] = text_content.text

                    else:
                        # Add to current section
                        if not current_section:
                            current_section = {
                                "title": "Introduction",
                                "level": 1,
                                "content": [],
                            }

                        current_section["content"].append(
                            {
                                "type": "text",
                                "content": text_content.text,
                                "subtype": text_content.content_type.value,
                            }
                        )

                elif element.element_type == "table":
                    if not current_section:
                        current_section = {"title": "Data", "level": 1, "content": []}

                    current_section["content"].append(
                        {
                            "type": "table",
                            "content": element.content,
                            "metadata": element.metadata,
                        }
                    )

                elif element.element_type == "image":
                    if not current_section:
                        current_section = {"title": "Images", "level": 1, "content": []}

                    current_section["content"].append(
                        {
                            "type": "image",
                            "content": element.content,
                            "metadata": element.metadata,
                        }
                    )

            # Add final section
            if current_section:
                document["sections"].append(current_section)

            return document

        except Exception as e:
            self.logger.error(f"Error creating document structure: {e}")
            return {"title": "", "sections": [], "metadata": {}}

    def validate_merged_content(self, merged_elements: List[MergedElement]) -> bool:
        """
        Validate the merged content structure.

        Args:
            merged_elements: List of merged elements

        Returns:
            True if structure is valid
        """
        if not merged_elements:
            return False

        # Check for reasonable content distribution
        type_counts = {}
        for element in merged_elements:
            element_type = element.element_type
            type_counts[element_type] = type_counts.get(element_type, 0) + 1

        # Should have at least some text content
        if type_counts.get("text", 0) == 0:
            return False

        # Check position ordering
        positions = [element.position for element in merged_elements]
        if positions != sorted(positions):
            self.logger.warning("Merged elements are not in position order")

        return True
