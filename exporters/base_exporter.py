"""
Base exporter class for document export functionality.

This module provides the abstract base class for all document exporters.
"""

import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class ExportError(Exception):
    """Exception raised during export operations."""

    pass


class BaseExporter(ABC):
    """Abstract base class for document exporters."""

    def __init__(self, output_path: str):
        """
        Initialize the exporter.

        Args:
            output_path: Path where the exported document will be saved
        """
        self.output_path = Path(output_path)
        self.logger = logger
        self._setup_logging()

    def _setup_logging(self):
        """Setup logging for the exporter."""
        self.logger.info(
            f"Initialized {self.__class__.__name__} with output: {self.output_path}"
        )

    @abstractmethod
    def export_document(
        self, document_structure: Dict[str, Any], metadata: Optional[Dict] = None
    ) -> bool:
        """
        Export document structure to file.

        Args:
            document_structure: Structured document data
            metadata: Optional metadata for the document

        Returns:
            True if export successful, False otherwise
        """
        pass

    @abstractmethod
    def export_tables(
        self, tables: List[List[List[str]]], table_metadata: Optional[List[Dict]] = None
    ) -> bool:
        """
        Export tables to document.

        Args:
            tables: List of table structures
            table_metadata: Optional metadata for each table

        Returns:
            True if export successful, False otherwise
        """
        pass

    @abstractmethod
    def export_text_content(self, text_contents: List[Dict]) -> bool:
        """
        Export text content to document.

        Args:
            text_contents: List of formatted text content

        Returns:
            True if export successful, False otherwise
        """
        pass

    def validate_output_path(self) -> bool:
        """
        Validate the output path.

        Returns:
            True if path is valid and writable
        """
        try:
            # Check if parent directory exists
            parent_dir = self.output_path.parent
            if not parent_dir.exists():
                parent_dir.mkdir(parents=True, exist_ok=True)

            # Check if we can write to the location
            if self.output_path.exists():
                if not self.output_path.is_file():
                    raise ExportError(f"Output path is not a file: {self.output_path}")

                # Check if file is writable
                test_file = self.output_path.with_suffix(
                    self.output_path.suffix + ".tmp"
                )
                try:
                    test_file.touch()
                    test_file.unlink()
                except PermissionError:
                    raise ExportError(
                        f"Cannot write to output path: {self.output_path}"
                    )

            return True

        except Exception as e:
            self.logger.error(f"Output path validation failed: {e}")
            return False

    def prepare_export_data(self, document_structure: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare and validate data for export.

        Args:
            document_structure: Raw document structure

        Returns:
            Processed document structure ready for export
        """
        try:
            prepared_data = {
                "title": document_structure.get("title", "Untitled Document"),
                "sections": [],
                "metadata": document_structure.get("metadata", {}),
            }

            # Process sections
            sections = document_structure.get("sections", [])
            for section in sections:
                processed_section = self._process_section(section)
                if processed_section:
                    prepared_data["sections"].append(processed_section)

            return prepared_data

        except Exception as e:
            self.logger.error(f"Error preparing export data: {e}")
            raise ExportError(f"Failed to prepare export data: {e}")

    def _process_section(self, section: Dict) -> Optional[Dict]:
        """Process a single section for export."""
        if not isinstance(section, dict):
            return None

        processed_section = {
            "title": section.get("title", ""),
            "level": section.get("level", 1),
            "content": [],
        }

        # Process section content
        content = section.get("content", [])
        for item in content:
            processed_item = self._process_content_item(item)
            if processed_item:
                processed_section["content"].append(processed_item)

        return processed_section

    def _process_content_item(self, item: Dict) -> Optional[Dict]:
        """Process a single content item."""
        if not isinstance(item, dict):
            return None

        item_type = item.get("type", "text")

        # Validate required fields
        if "content" not in item:
            return None

        processed_item = {"type": item_type, "content": item["content"]}

        # Add optional fields
        if "subtype" in item:
            processed_item["subtype"] = item["subtype"]
        if "metadata" in item:
            processed_item["metadata"] = item["metadata"]

        return processed_item

    def add_export_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add export-specific metadata.

        Args:
            metadata: Existing metadata

        Returns:
            Enhanced metadata with export information
        """
        enhanced_metadata = metadata.copy() if metadata else {}

        enhanced_metadata.update(
            {
                "exporter": self.__class__.__name__,
                "export_path": str(self.output_path),
                "export_format": self.get_export_format(),
            }
        )

        return enhanced_metadata

    @abstractmethod
    def get_export_format(self) -> str:
        """
        Get the export format identifier.

        Returns:
            Format identifier string (e.g., 'docx', 'pdf')
        """
        pass

    def cleanup_temp_files(self):
        """Clean up any temporary files created during export."""
        # Base implementation - subclasses can override
        pass

    def get_export_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the export operation.

        Returns:
            Dictionary with export statistics
        """
        return {
            "output_path": str(self.output_path),
            "file_exists": self.output_path.exists(),
            "file_size": (
                self.output_path.stat().st_size if self.output_path.exists() else 0
            ),
            "format": self.get_export_format(),
        }

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.cleanup_temp_files()
        if exc_type:
            self.logger.error(f"Export failed with {exc_type.__name__}: {exc_val}")
        return False
