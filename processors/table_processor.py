"""
Table processing module for OCR text extraction.

This module handles all table-specific operations including table reconstruction,
formatting, and content processing.
"""

import logging
from typing import List, Dict, Any, Tuple, Optional
from collections import defaultdict
import re

logger = logging.getLogger(__name__)


class TableProcessor:
    """Handles table processing operations."""

    def __init__(self):
        self.logger = logger

    def process_table_elements(self, table_elements: List[Dict]) -> List[List[str]]:
        """
        Process table elements and convert them to structured table format.

        Args:
            table_elements: List of table element dictionaries

        Returns:
            List of table rows (each row is a list of cell values)
        """
        if not table_elements:
            return []

        try:
            # Group elements by row based on Y coordinates
            rows = self._group_elements_by_row(table_elements)

            # Convert to structured table
            structured_table = []
            for row_elements in rows:
                row_cells = self._extract_row_cells(row_elements)
                if row_cells:  # Only add non-empty rows
                    structured_table.append(row_cells)

            return structured_table

        except Exception as e:
            self.logger.error(f"Error processing table elements: {e}")
            return []

    def _group_elements_by_row(self, elements: List[Dict]) -> List[List[Dict]]:
        """Group table elements by row based on Y coordinates."""
        if not elements:
            return []

        # Sort elements by Y coordinate
        sorted_elements = sorted(elements, key=lambda x: x.get("bbox", [0, 0, 0, 0])[1])

        rows = []
        current_row = []
        current_y = None
        y_tolerance = 10  # Pixels tolerance for same row

        for element in sorted_elements:
            bbox = element.get("bbox", [0, 0, 0, 0])
            element_y = bbox[1]

            if current_y is None or abs(element_y - current_y) <= y_tolerance:
                current_row.append(element)
                current_y = element_y if current_y is None else current_y
            else:
                if current_row:
                    # Sort current row by X coordinate
                    current_row.sort(key=lambda x: x.get("bbox", [0, 0, 0, 0])[0])
                    rows.append(current_row)
                current_row = [element]
                current_y = element_y

        # Add the last row
        if current_row:
            current_row.sort(key=lambda x: x.get("bbox", [0, 0, 0, 0])[0])
            rows.append(current_row)

        return rows

    def _extract_row_cells(self, row_elements: List[Dict]) -> List[str]:
        """Extract cell values from row elements."""
        cells = []
        for element in row_elements:
            text = element.get("text", "").strip()
            if text:
                cells.append(text)
        return cells

    def reconstruct_table_structure(
        self, text_elements: List[Dict], table_bbox: Tuple[int, int, int, int]
    ) -> List[List[str]]:
        """
        Reconstruct table structure from text elements within table boundaries.

        Args:
            text_elements: List of text element dictionaries
            table_bbox: Table bounding box (x1, y1, x2, y2)

        Returns:
            Reconstructed table as list of rows
        """
        if not text_elements or not table_bbox:
            return []

        try:
            # Filter elements within table boundaries
            table_texts = self._filter_elements_in_bbox(text_elements, table_bbox)

            if not table_texts:
                return []

            # Use coordinate-based reconstruction
            return self._reconstruct_by_coordinates(table_texts)

        except Exception as e:
            self.logger.error(f"Error reconstructing table structure: {e}")
            return []

    def _filter_elements_in_bbox(
        self, elements: List[Dict], bbox: Tuple[int, int, int, int]
    ) -> List[Dict]:
        """Filter elements that fall within the given bounding box."""
        x1, y1, x2, y2 = bbox
        filtered = []

        for element in elements:
            elem_bbox = element.get("bbox")
            if not elem_bbox or len(elem_bbox) < 4:
                continue

            elem_x1, elem_y1, elem_x2, elem_y2 = elem_bbox

            # Check if element center is within table bbox
            center_x = (elem_x1 + elem_x2) / 2
            center_y = (elem_y1 + elem_y2) / 2

            if x1 <= center_x <= x2 and y1 <= center_y <= y2:
                filtered.append(element)

        return filtered

    def _reconstruct_by_coordinates(self, elements: List[Dict]) -> List[List[str]]:
        """Reconstruct table using coordinate-based approach."""
        if not elements:
            return []

        # Group by rows first
        rows = self._group_elements_by_row(elements)

        # Extract unique column positions
        x_positions = set()
        for element in elements:
            bbox = element.get("bbox", [0, 0, 0, 0])
            x_positions.add(bbox[0])  # Left edge

        sorted_x_positions = sorted(x_positions)

        # Build table structure
        table = []
        for row_elements in rows:
            row_cells = [""] * len(sorted_x_positions)

            for element in row_elements:
                text = element.get("text", "").strip()
                if not text:
                    continue

                bbox = element.get("bbox", [0, 0, 0, 0])
                element_x = bbox[0]

                # Find the closest column position
                col_index = self._find_closest_column_index(
                    element_x, sorted_x_positions
                )
                if 0 <= col_index < len(row_cells):
                    if row_cells[col_index]:
                        row_cells[col_index] += " " + text
                    else:
                        row_cells[col_index] = text

            # Remove empty trailing cells
            while row_cells and not row_cells[-1]:
                row_cells.pop()

            if row_cells:  # Only add non-empty rows
                table.append(row_cells)

        return table

    def _find_closest_column_index(
        self, x_position: float, sorted_positions: List[float]
    ) -> int:
        """Find the index of the closest column position."""
        if not sorted_positions:
            return 0

        min_distance = float("inf")
        closest_index = 0

        for i, pos in enumerate(sorted_positions):
            distance = abs(x_position - pos)
            if distance < min_distance:
                min_distance = distance
                closest_index = i

        return closest_index

    def merge_table_cells(
        self, table: List[List[str]], merge_threshold: int = 50
    ) -> List[List[str]]:
        """
        Merge adjacent cells that likely belong together.

        Args:
            table: Input table structure
            merge_threshold: Distance threshold for merging

        Returns:
            Table with merged cells
        """
        if not table:
            return table

        merged_table = []
        for row in table:
            merged_row = []
            current_cell = ""

            for cell in row:
                cell_text = cell.strip()
                if not cell_text:
                    continue

                if current_cell:
                    # Check if cells should be merged
                    if self._should_merge_cells(current_cell, cell_text):
                        current_cell += " " + cell_text
                    else:
                        merged_row.append(current_cell)
                        current_cell = cell_text
                else:
                    current_cell = cell_text

            if current_cell:
                merged_row.append(current_cell)

            if merged_row:
                merged_table.append(merged_row)

        return merged_table

    def _should_merge_cells(self, cell1: str, cell2: str) -> bool:
        """Determine if two cells should be merged."""
        # Don't merge if either cell contains numbers (likely separate data points)
        if re.search(r"\d", cell1) and re.search(r"\d", cell2):
            return False

        # Merge if both are short text fragments
        if len(cell1) < 10 and len(cell2) < 10:
            return True

        # Merge if one appears to be a continuation
        if cell1.endswith((",", "，", "、")) or cell2.startswith(("的", "和", "或")):
            return True

        return False

    def validate_table_structure(self, table: List[List[str]]) -> bool:
        """
        Validate if the table structure is reasonable.

        Args:
            table: Table structure to validate

        Returns:
            True if table structure is valid
        """
        if not table:
            return False

        # Check minimum table size
        if len(table) < 2:
            return False

        # Check if table has consistent column count
        column_counts = [len(row) for row in table if row]
        if not column_counts:
            return False

        # Allow some variation in column count
        min_cols = min(column_counts)
        max_cols = max(column_counts)

        # Table is valid if column variation is reasonable
        return (max_cols - min_cols) <= 2 and min_cols >= 2

    def clean_table_data(self, table: List[List[str]]) -> List[List[str]]:
        """
        Clean table data by removing empty rows and normalizing text.

        Args:
            table: Input table structure

        Returns:
            Cleaned table structure
        """
        if not table:
            return []

        cleaned_table = []
        for row in table:
            cleaned_row = []
            for cell in row:
                # Clean cell text
                cleaned_cell = self._clean_cell_text(cell)
                cleaned_row.append(cleaned_cell)

            # Only add rows that have at least one non-empty cell
            if any(cell.strip() for cell in cleaned_row):
                cleaned_table.append(cleaned_row)

        return cleaned_table

    def _clean_cell_text(self, text: str) -> str:
        """Clean individual cell text."""
        if not text:
            return ""

        # Remove excessive whitespace
        cleaned = " ".join(text.split())

        # Remove common OCR artifacts
        cleaned = re.sub(r"[|｜]", "", cleaned)  # Remove table separators
        cleaned = re.sub(r"^\s*[-_=]+\s*$", "", cleaned)  # Remove separator lines

        return cleaned.strip()
