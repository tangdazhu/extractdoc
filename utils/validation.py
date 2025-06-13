"""
Validation utilities for OCR text extraction system.

This module provides validation functions for various data types and structures
used throughout the OCR processing pipeline.
"""

import os
import re
from typing import List, Dict, Any, Optional, Union, Tuple
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class ValidationUtils:
    """Utility class for validation operations."""

    @staticmethod
    def validate_file_path(file_path: Union[str, Path]) -> bool:
        """
        Validate if a file path exists and is accessible.

        Args:
            file_path: Path to the file to validate

        Returns:
            bool: True if file exists and is readable, False otherwise
        """
        try:
            path = Path(file_path)
            return path.exists() and path.is_file() and os.access(path, os.R_OK)
        except Exception as e:
            logger.warning(f"File path validation failed: {e}")
            return False

    @staticmethod
    def validate_directory_path(dir_path: Union[str, Path]) -> bool:
        """
        Validate if a directory path exists and is accessible.

        Args:
            dir_path: Path to the directory to validate

        Returns:
            bool: True if directory exists and is accessible, False otherwise
        """
        try:
            path = Path(dir_path)
            return path.exists() and path.is_dir() and os.access(path, os.R_OK)
        except Exception as e:
            logger.warning(f"Directory path validation failed: {e}")
            return False

    @staticmethod
    def validate_image_file(file_path: Union[str, Path]) -> bool:
        """
        Validate if a file is a supported image format.

        Args:
            file_path: Path to the image file

        Returns:
            bool: True if file is a valid image, False otherwise
        """
        if not ValidationUtils.validate_file_path(file_path):
            return False

        supported_extensions = {
            ".jpg",
            ".jpeg",
            ".png",
            ".bmp",
            ".tiff",
            ".tif",
            ".webp",
        }
        file_ext = Path(file_path).suffix.lower()

        return file_ext in supported_extensions

    @staticmethod
    def validate_output_format(format_str: str) -> bool:
        """
        Validate if the output format is supported.

        Args:
            format_str: Output format string

        Returns:
            bool: True if format is supported, False otherwise
        """
        supported_formats = {"docx", "pdf", "txt", "html", "markdown", "json"}
        return format_str.lower() in supported_formats

    @staticmethod
    def validate_coordinates(coordinates: Dict[str, Any]) -> bool:
        """
        Validate coordinate data structure.

        Args:
            coordinates: Dictionary containing coordinate information

        Returns:
            bool: True if coordinates are valid, False otherwise
        """
        try:
            required_keys = {"x1", "y1", "x2", "y2"}
            if not all(key in coordinates for key in required_keys):
                return False

            # Check if all values are numeric
            for key in required_keys:
                if not isinstance(coordinates[key], (int, float)):
                    return False

            # Check logical constraints
            if (
                coordinates["x2"] <= coordinates["x1"]
                or coordinates["y2"] <= coordinates["y1"]
            ):
                return False

            return True
        except Exception:
            return False

    @staticmethod
    def validate_table_data(table_data: List[List[str]]) -> bool:
        """
        Validate table data structure.

        Args:
            table_data: Table data as list of rows (lists of strings)

        Returns:
            bool: True if table data is valid, False otherwise
        """
        try:
            if not isinstance(table_data, list) or len(table_data) == 0:
                return False

            # Check if all rows are lists
            if not all(isinstance(row, list) for row in table_data):
                return False

            # Check if all cells are strings
            for row in table_data:
                if not all(isinstance(cell, str) for cell in row):
                    return False

            return True
        except Exception:
            return False

    @staticmethod
    def validate_ocr_result(ocr_result: Dict[str, Any]) -> bool:
        """
        Validate OCR result structure.

        Args:
            ocr_result: OCR result dictionary

        Returns:
            bool: True if OCR result is valid, False otherwise
        """
        try:
            required_keys = {"text", "confidence", "bbox"}
            if not all(key in ocr_result for key in required_keys):
                return False

            # Validate text
            if not isinstance(ocr_result["text"], str):
                return False

            # Validate confidence
            confidence = ocr_result["confidence"]
            if not isinstance(confidence, (int, float)) or not (0 <= confidence <= 100):
                return False

            # Validate bounding box
            if not ValidationUtils.validate_coordinates(ocr_result["bbox"]):
                return False

            return True
        except Exception:
            return False

    @staticmethod
    def validate_text_content(text: str) -> bool:
        """
        Validate text content for basic sanity checks.

        Args:
            text: Text content to validate

        Returns:
            bool: True if text appears valid, False otherwise
        """
        try:
            if not isinstance(text, str):
                return False

            # Check for minimum length
            if len(text.strip()) < 1:
                return False

            # Check for reasonable character distribution
            # Should have some letters or numbers
            if not re.search(r"[a-zA-Z0-9]", text):
                return False

            return True
        except Exception:
            return False

    @staticmethod
    def validate_export_settings(settings: Dict[str, Any]) -> bool:
        """
        Validate export settings configuration.

        Args:
            settings: Export settings dictionary

        Returns:
            bool: True if settings are valid, False otherwise
        """
        try:
            # Check required keys
            required_keys = {"output_format", "output_path"}
            if not all(key in settings for key in required_keys):
                return False

            # Validate output format
            if not ValidationUtils.validate_output_format(settings["output_format"]):
                return False

            # Validate output path directory
            output_dir = Path(settings["output_path"]).parent
            if not ValidationUtils.validate_directory_path(output_dir):
                return False

            return True
        except Exception:
            return False

    @staticmethod
    def validate_processing_config(config: Dict[str, Any]) -> bool:
        """
        Validate processing configuration.

        Args:
            config: Processing configuration dictionary

        Returns:
            bool: True if configuration is valid, False otherwise
        """
        try:
            # Validate numeric parameters
            numeric_params = {
                "confidence_threshold": (0, 100),
                "table_detection_threshold": (0, 1),
                "text_merge_threshold": (0, 1000),
            }

            for param, (min_val, max_val) in numeric_params.items():
                if param in config:
                    value = config[param]
                    if not isinstance(value, (int, float)) or not (
                        min_val <= value <= max_val
                    ):
                        return False

            # Validate boolean parameters
            boolean_params = [
                "enable_table_detection",
                "fix_ocr_characters",
                "merge_nearby_text",
            ]
            for param in boolean_params:
                if param in config and not isinstance(config[param], bool):
                    return False

            return True
        except Exception:
            return False

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Sanitize filename by removing invalid characters.

        Args:
            filename: Original filename

        Returns:
            str: Sanitized filename
        """
        try:
            # Remove invalid characters
            invalid_chars = r'[<>:"/\\|?*]'
            sanitized = re.sub(invalid_chars, "_", filename)

            # Remove leading/trailing spaces and dots
            sanitized = sanitized.strip(" .")

            # Ensure filename is not empty
            if not sanitized:
                sanitized = "untitled"

            return sanitized
        except Exception:
            return "untitled"

    @staticmethod
    def validate_language_code(lang_code: str) -> bool:
        """
        Validate language code format.

        Args:
            lang_code: Language code to validate

        Returns:
            bool: True if language code is valid, False otherwise
        """
        try:
            # Common language codes for OCR
            valid_codes = {
                "eng",
                "chi_sim",
                "chi_tra",
                "jpn",
                "kor",
                "ara",
                "rus",
                "fra",
                "deu",
                "spa",
                "ita",
                "por",
                "nld",
                "pol",
                "tur",
                "vie",
                "tha",
                "hin",
                "ben",
                "tel",
                "tam",
                "kan",
                "mal",
                "guj",
                "ori",
                "pan",
                "asm",
                "nep",
                "sin",
                "mya",
                "khm",
                "lao",
                "gle",
                "cym",
                "bre",
                "gla",
                "cor",
                "eus",
                "cat",
                "glg",
                "ast",
                "ext",
                "ara",
                "fas",
                "urd",
                "pus",
                "uig",
                "kaz",
                "kir",
                "tgk",
                "uzb",
                "mon",
                "tib",
                "dzo",
                "bod",
            }

            return lang_code.lower() in valid_codes
        except Exception:
            return False

    @staticmethod
    def validate_confidence_threshold(threshold: Union[int, float]) -> bool:
        """
        Validate confidence threshold value.

        Args:
            threshold: Confidence threshold value

        Returns:
            bool: True if threshold is valid, False otherwise
        """
        try:
            return isinstance(threshold, (int, float)) and 0 <= threshold <= 100
        except Exception:
            return False

    @staticmethod
    def validate_bbox_overlap(bbox1: Dict[str, float], bbox2: Dict[str, float]) -> bool:
        """
        Check if two bounding boxes have valid overlap.

        Args:
            bbox1: First bounding box
            bbox2: Second bounding box

        Returns:
            bool: True if boxes overlap, False otherwise
        """
        try:
            if not (
                ValidationUtils.validate_coordinates(bbox1)
                and ValidationUtils.validate_coordinates(bbox2)
            ):
                return False

            # Check for overlap
            return not (
                bbox1["x2"] <= bbox2["x1"]
                or bbox2["x2"] <= bbox1["x1"]
                or bbox1["y2"] <= bbox2["y1"]
                or bbox2["y2"] <= bbox1["y1"]
            )
        except Exception:
            return False

    @staticmethod
    def validate_memory_usage(max_memory_mb: int = 2048) -> bool:
        """
        Check if system has sufficient memory for processing.

        Args:
            max_memory_mb: Maximum memory required in MB

        Returns:
            bool: True if sufficient memory available, False otherwise
        """
        try:
            import psutil

            available_memory_mb = psutil.virtual_memory().available / (1024 * 1024)
            return available_memory_mb >= max_memory_mb
        except ImportError:
            logger.warning("psutil not available for memory validation")
            return True  # Assume sufficient memory if can't check
        except Exception:
            return True  # Assume sufficient memory on error

    @staticmethod
    def validate_disk_space(
        output_path: Union[str, Path], required_mb: int = 100
    ) -> bool:
        """
        Check if sufficient disk space is available for output.

        Args:
            output_path: Path where output will be saved
            required_mb: Required disk space in MB

        Returns:
            bool: True if sufficient space available, False otherwise
        """
        try:
            import shutil

            free_space_bytes = shutil.disk_usage(Path(output_path).parent).free
            free_space_mb = free_space_bytes / (1024 * 1024)
            return free_space_mb >= required_mb
        except Exception:
            return True  # Assume sufficient space on error
