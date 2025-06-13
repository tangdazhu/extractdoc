"""
PDF exporter for OCR text extraction system.

This module handles exporting structured content to PDF format
with proper formatting and layout preservation.
"""

import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate,
        Paragraph,
        Spacer,
        Table,
        TableStyle,
        PageBreak,
    )
    from reportlab.platypus.flowables import HRFlowable
except ImportError:
    raise ImportError(
        "reportlab library is required. Install with: pip install reportlab"
    )

from .base_exporter import BaseExporter, ExportError

logger = logging.getLogger(__name__)


class PdfExporter(BaseExporter):
    """PDF document exporter with formatting capabilities."""

    def __init__(self, output_path: str, page_size=letter):
        """Initialize PDF exporter."""
        super().__init__(output_path)
        self.page_size = page_size
        self.document = None
        self.story = []
        self._init_styles()

    def _init_styles(self):
        """Initialize document styles."""
        self.styles = getSampleStyleSheet()

        # Custom styles
        self.styles.add(
            ParagraphStyle(
                name="CustomTitle",
                parent=self.styles["Title"],
                fontSize=18,
                spaceAfter=20,
                alignment=1,  # Center alignment
                textColor=colors.black,
            )
        )

        self.styles.add(
            ParagraphStyle(
                name="CustomHeading1",
                parent=self.styles["Heading1"],
                fontSize=14,
                spaceAfter=12,
                textColor=colors.black,
            )
        )

        self.styles.add(
            ParagraphStyle(
                name="CustomHeading2",
                parent=self.styles["Heading2"],
                fontSize=12,
                spaceAfter=10,
                textColor=colors.darkgrey,
            )
        )

        self.styles.add(
            ParagraphStyle(
                name="CustomNormal",
                parent=self.styles["Normal"],
                fontSize=10,
                spaceAfter=8,
                textColor=colors.black,
            )
        )

        self.styles.add(
            ParagraphStyle(
                name="TableHeader",
                parent=self.styles["Normal"],
                fontSize=9,
                textColor=colors.white,
                alignment=1,  # Center alignment
            )
        )

        self.styles.add(
            ParagraphStyle(
                name="TableCell",
                parent=self.styles["Normal"],
                fontSize=9,
                textColor=colors.black,
            )
        )

    def get_export_format(self) -> str:
        """Get export format identifier."""
        return "pdf"

    def export_document(
        self, document_structure: Dict[str, Any], metadata: Optional[Dict] = None
    ) -> bool:
        """
        Export complete document structure to PDF.

        Args:
            document_structure: Structured document data
            metadata: Optional document metadata

        Returns:
            True if export successful
        """
        try:
            if not self.validate_output_path():
                return False

            # Prepare data for export
            prepared_data = self.prepare_export_data(document_structure)

            # Create PDF document
            self.document = SimpleDocTemplate(
                str(self.output_path),
                pagesize=self.page_size,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=72,
            )

            # Build document story
            self.story = []

            # Add title if available
            title = prepared_data.get("title", "")
            if title:
                self._add_title(title)

            # Process sections
            sections = prepared_data.get("sections", [])
            for section in sections:
                self._add_section(section)

            # Build PDF
            self.document.build(self.story)
            self.logger.info(
                f"PDF document exported successfully to {self.output_path}"
            )
            return True

        except Exception as e:
            self.logger.error(f"Error exporting PDF document: {e}")
            raise ExportError(f"Failed to export PDF document: {e}")

    def export_tables(
        self, tables: List[List[List[str]]], table_metadata: Optional[List[Dict]] = None
    ) -> bool:
        """
        Export tables to PDF document.

        Args:
            tables: List of table structures
            table_metadata: Optional metadata for each table

        Returns:
            True if export successful
        """
        try:
            if not self.validate_output_path():
                return False

            # Create PDF document
            if not self.document:
                self.document = SimpleDocTemplate(
                    str(self.output_path),
                    pagesize=self.page_size,
                    rightMargin=72,
                    leftMargin=72,
                    topMargin=72,
                    bottomMargin=72,
                )
                self.story = []

            # Add each table
            for i, table_data in enumerate(tables):
                if table_data:  # Only add non-empty tables
                    metadata = (
                        table_metadata[i]
                        if table_metadata and i < len(table_metadata)
                        else {}
                    )
                    self._add_table(table_data, metadata)

                    # Add spacing between tables
                    if i < len(tables) - 1:
                        self.story.append(Spacer(1, 20))

            # Build PDF
            self.document.build(self.story)
            self.logger.info(f"Tables exported successfully to {self.output_path}")
            return True

        except Exception as e:
            self.logger.error(f"Error exporting tables to PDF: {e}")
            return False

    def export_text_content(self, text_contents: List[Dict]) -> bool:
        """
        Export text content to PDF document.

        Args:
            text_contents: List of formatted text content

        Returns:
            True if export successful
        """
        try:
            if not self.validate_output_path():
                return False

            # Create PDF document
            if not self.document:
                self.document = SimpleDocTemplate(
                    str(self.output_path),
                    pagesize=self.page_size,
                    rightMargin=72,
                    leftMargin=72,
                    topMargin=72,
                    bottomMargin=72,
                )
                self.story = []

            # Add each text content
            for content in text_contents:
                self._add_text_content(content)

            # Build PDF
            self.document.build(self.story)
            self.logger.info(
                f"Text content exported successfully to {self.output_path}"
            )
            return True

        except Exception as e:
            self.logger.error(f"Error exporting text content to PDF: {e}")
            return False

    def _add_title(self, title: str):
        """Add document title."""
        title_paragraph = Paragraph(title, self.styles["CustomTitle"])
        self.story.append(title_paragraph)
        self.story.append(Spacer(1, 20))

    def _add_section(self, section: Dict):
        """Add a document section with title and content."""
        title = section.get("title", "")
        level = section.get("level", 1)
        content = section.get("content", [])

        # Add section title
        if title:
            style_name = f"CustomHeading{min(level, 2)}"
            section_heading = Paragraph(title, self.styles[style_name])
            self.story.append(section_heading)
            self.story.append(Spacer(1, 10))

        # Add section content
        for item in content:
            self._add_content_item(item)

    def _add_content_item(self, item: Dict):
        """Add a single content item to the document."""
        item_type = item.get("type", "text")
        content = item.get("content", "")

        if item_type == "text":
            self._add_text_content(item)
        elif item_type == "table":
            self._add_table(content, item.get("metadata", {}))
        elif item_type == "image":
            self._add_image_placeholder(content, item.get("metadata", {}))

    def _add_text_content(self, text_item: Dict):
        """Add formatted text content."""
        text = text_item.get("content", "")
        subtype = text_item.get("subtype", "paragraph")

        if not text.strip():
            return

        # Determine style based on subtype
        style_name = self._get_style_name_for_subtype(subtype)

        # Handle list items
        if subtype == "list_item":
            text = f"• {text}"

        # Create paragraph
        paragraph = Paragraph(text, self.styles[style_name])
        self.story.append(paragraph)
        self.story.append(Spacer(1, 6))

    def _get_style_name_for_subtype(self, subtype: str) -> str:
        """Get style name for content subtype."""
        style_mapping = {
            "title": "CustomTitle",
            "subtitle": "CustomHeading2",
            "paragraph": "CustomNormal",
            "list_item": "CustomNormal",
            "header": "CustomNormal",
            "footer": "CustomNormal",
        }
        return style_mapping.get(subtype, "CustomNormal")

    def _add_table(self, table_data: List[List[str]], metadata: Optional[Dict] = None):
        """Add a formatted table to the document."""
        if not table_data:
            return

        # Prepare table data
        processed_data = []
        for row in table_data:
            processed_row = []
            for cell in row:
                # Create paragraph for each cell to enable text wrapping
                if isinstance(cell, str):
                    cell_paragraph = Paragraph(cell, self.styles["TableCell"])
                    processed_row.append(cell_paragraph)
                else:
                    processed_row.append(str(cell))
            processed_data.append(processed_row)

        # Calculate column widths
        max_cols = max(len(row) for row in processed_data) if processed_data else 0
        if max_cols == 0:
            return

        # Create table
        available_width = self.page_size[0] - 144  # Page width minus margins
        col_width = available_width / max_cols
        col_widths = [col_width] * max_cols

        table = Table(processed_data, colWidths=col_widths)

        # Apply table style
        table_style = TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.grey),  # Header background
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),  # Header text color
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),  # Header font
                ("FONTSIZE", (0, 0), (-1, 0), 9),  # Header font size
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),  # Header padding
                ("BACKGROUND", (0, 1), (-1, -1), colors.beige),  # Cell background
                ("TEXTCOLOR", (0, 1), (-1, -1), colors.black),  # Cell text color
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),  # Cell font
                ("FONTSIZE", (0, 1), (-1, -1), 8),  # Cell font size
                ("GRID", (0, 0), (-1, -1), 1, colors.black),  # Grid lines
                ("VALIGN", (0, 0), (-1, -1), "TOP"),  # Vertical alignment
            ]
        )

        table.setStyle(table_style)

        # Add table to story
        self.story.append(table)
        self.story.append(Spacer(1, 20))

    def _add_image_placeholder(self, image_data: Dict, metadata: Optional[Dict] = None):
        """Add image placeholder text."""
        placeholder_text = "[Image placeholder]"
        if metadata and "filename" in metadata:
            placeholder_text += f" - {metadata['filename']}"

        paragraph = Paragraph(f"<i>{placeholder_text}</i>", self.styles["CustomNormal"])
        self.story.append(paragraph)
        self.story.append(Spacer(1, 10))

    def add_page_break(self):
        """Add a page break to the document."""
        self.story.append(PageBreak())

    def add_horizontal_line(self):
        """Add a horizontal line separator."""
        line = HRFlowable(width="100%", thickness=1, lineCap="round", color=colors.grey)
        self.story.append(line)
        self.story.append(Spacer(1, 10))

    def add_spacer(self, height: float = 20):
        """Add vertical space."""
        self.story.append(Spacer(1, height))
