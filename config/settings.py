"""
Settings management for OCR text extraction system.

This module handles application configuration and settings management.
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from pathlib import Path
import yaml
import json

logger = logging.getLogger(__name__)


@dataclass
class OCRSettings:
    """OCR engine configuration settings."""

    use_angle_cls: bool = True
    lang: str = "ch"
    det: bool = True
    rec: bool = True
    cls: bool = True
    det_db_thresh: float = 0.3
    det_db_box_thresh: float = 0.6
    det_db_unclip_ratio: float = 1.5
    rec_batch_num: int = 6
    max_text_length: int = 25
    use_space_char: bool = True
    drop_score: float = 0.5
    use_gpu: bool = False
    gpu_mem: int = 500
    enable_mkldnn: bool = False
    cpu_threads: int = 10


@dataclass
class ExportSettings:
    """Export configuration settings."""

    default_format: str = "docx"
    preserve_formatting: bool = True
    include_images: bool = False
    table_style: str = "grid"
    font_name: str = "Arial"
    font_size: int = 12
    page_margins: Dict[str, float] = field(
        default_factory=lambda: {"top": 1.0, "bottom": 1.0, "left": 1.0, "right": 1.0}
    )
    auto_fit_tables: bool = True
    max_table_width: float = 6.5  # inches


@dataclass
class ProcessingSettings:
    """Text processing configuration settings."""

    min_text_length: int = 2
    max_text_length: int = 1000
    merge_threshold: int = 50
    table_detection_threshold: float = 0.7
    enable_text_cleaning: bool = True
    enable_ocr_error_correction: bool = True
    group_nearby_elements: bool = True
    proximity_threshold: int = 30


@dataclass
class LoggingSettings:
    """Logging configuration settings."""

    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_path: Optional[str] = None
    max_file_size: int = 10485760  # 10MB
    backup_count: int = 5
    console_output: bool = True


class Settings:
    """Main settings manager for the application."""

    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize settings manager.

        Args:
            config_file: Optional path to configuration file
        """
        self.config_file = config_file
        self._config_data = {}

        # Initialize default settings
        self.ocr = OCRSettings()
        self.export = ExportSettings()
        self.processing = ProcessingSettings()
        self.logging = LoggingSettings()

        # Load configuration if file provided
        if config_file:
            self.load_from_file(config_file)

    def load_from_file(self, config_file: str) -> bool:
        """
        Load settings from configuration file.

        Args:
            config_file: Path to configuration file

        Returns:
            True if loaded successfully
        """
        try:
            config_path = Path(config_file)

            if not config_path.exists():
                logger.warning(f"Configuration file not found: {config_file}")
                return False

            # Determine file format and load
            if config_path.suffix.lower() in [".yaml", ".yml"]:
                with open(config_path, "r", encoding="utf-8") as f:
                    self._config_data = yaml.safe_load(f) or {}
            elif config_path.suffix.lower() == ".json":
                with open(config_path, "r", encoding="utf-8") as f:
                    self._config_data = json.load(f)
            else:
                logger.error(
                    f"Unsupported configuration file format: {config_path.suffix}"
                )
                return False

            # Apply loaded configuration
            self._apply_config_data()
            logger.info(f"Configuration loaded from {config_file}")
            return True

        except Exception as e:
            logger.error(f"Error loading configuration from {config_file}: {e}")
            return False

    def _apply_config_data(self):
        """Apply loaded configuration data to settings objects."""
        try:
            # Apply OCR settings
            if "ocr" in self._config_data:
                ocr_config = self._config_data["ocr"]
                for key, value in ocr_config.items():
                    if hasattr(self.ocr, key):
                        setattr(self.ocr, key, value)

            # Apply export settings
            if "export" in self._config_data:
                export_config = self._config_data["export"]
                for key, value in export_config.items():
                    if hasattr(self.export, key):
                        setattr(self.export, key, value)

            # Apply processing settings
            if "processing" in self._config_data:
                processing_config = self._config_data["processing"]
                for key, value in processing_config.items():
                    if hasattr(self.processing, key):
                        setattr(self.processing, key, value)

            # Apply logging settings
            if "logging" in self._config_data:
                logging_config = self._config_data["logging"]
                for key, value in logging_config.items():
                    if hasattr(self.logging, key):
                        setattr(self.logging, key, value)

        except Exception as e:
            logger.error(f"Error applying configuration data: {e}")

    def save_to_file(self, config_file: str, format: str = "yaml") -> bool:
        """
        Save current settings to configuration file.

        Args:
            config_file: Path to save configuration
            format: File format ('yaml' or 'json')

        Returns:
            True if saved successfully
        """
        try:
            config_data = self.to_dict()
            config_path = Path(config_file)

            # Ensure parent directory exists
            config_path.parent.mkdir(parents=True, exist_ok=True)

            if format.lower() in ["yaml", "yml"]:
                with open(config_path, "w", encoding="utf-8") as f:
                    yaml.dump(
                        config_data,
                        f,
                        default_flow_style=False,
                        allow_unicode=True,
                        indent=2,
                    )
            elif format.lower() == "json":
                with open(config_path, "w", encoding="utf-8") as f:
                    json.dump(config_data, f, indent=2, ensure_ascii=False)
            else:
                logger.error(f"Unsupported save format: {format}")
                return False

            logger.info(f"Configuration saved to {config_file}")
            return True

        except Exception as e:
            logger.error(f"Error saving configuration to {config_file}: {e}")
            return False

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert settings to dictionary format.

        Returns:
            Dictionary representation of settings
        """
        return {
            "ocr": {
                "use_angle_cls": self.ocr.use_angle_cls,
                "lang": self.ocr.lang,
                "det": self.ocr.det,
                "rec": self.ocr.rec,
                "cls": self.ocr.cls,
                "det_db_thresh": self.ocr.det_db_thresh,
                "det_db_box_thresh": self.ocr.det_db_box_thresh,
                "det_db_unclip_ratio": self.ocr.det_db_unclip_ratio,
                "rec_batch_num": self.ocr.rec_batch_num,
                "max_text_length": self.ocr.max_text_length,
                "use_space_char": self.ocr.use_space_char,
                "drop_score": self.ocr.drop_score,
                "use_gpu": self.ocr.use_gpu,
                "gpu_mem": self.ocr.gpu_mem,
                "enable_mkldnn": self.ocr.enable_mkldnn,
                "cpu_threads": self.ocr.cpu_threads,
            },
            "export": {
                "default_format": self.export.default_format,
                "preserve_formatting": self.export.preserve_formatting,
                "include_images": self.export.include_images,
                "table_style": self.export.table_style,
                "font_name": self.export.font_name,
                "font_size": self.export.font_size,
                "page_margins": self.export.page_margins,
                "auto_fit_tables": self.export.auto_fit_tables,
                "max_table_width": self.export.max_table_width,
            },
            "processing": {
                "min_text_length": self.processing.min_text_length,
                "max_text_length": self.processing.max_text_length,
                "merge_threshold": self.processing.merge_threshold,
                "table_detection_threshold": self.processing.table_detection_threshold,
                "enable_text_cleaning": self.processing.enable_text_cleaning,
                "enable_ocr_error_correction": self.processing.enable_ocr_error_correction,
                "group_nearby_elements": self.processing.group_nearby_elements,
                "proximity_threshold": self.processing.proximity_threshold,
            },
            "logging": {
                "level": self.logging.level,
                "format": self.logging.format,
                "file_path": self.logging.file_path,
                "max_file_size": self.logging.max_file_size,
                "backup_count": self.logging.backup_count,
                "console_output": self.logging.console_output,
            },
        }

    def update_from_dict(self, config_dict: Dict[str, Any]):
        """
        Update settings from dictionary.

        Args:
            config_dict: Configuration dictionary
        """
        self._config_data = config_dict
        self._apply_config_data()

    def get_ocr_config(self) -> Dict[str, Any]:
        """
        Get OCR configuration for PaddleOCR.

        Returns:
            OCR configuration dictionary
        """
        return {
            "use_angle_cls": self.ocr.use_angle_cls,
            "lang": self.ocr.lang,
            "det": self.ocr.det,
            "rec": self.ocr.rec,
            "cls": self.ocr.cls,
            "det_db_thresh": self.ocr.det_db_thresh,
            "det_db_box_thresh": self.ocr.det_db_box_thresh,
            "det_db_unclip_ratio": self.ocr.det_db_unclip_ratio,
            "rec_batch_num": self.ocr.rec_batch_num,
            "max_text_length": self.ocr.max_text_length,
            "use_space_char": self.ocr.use_space_char,
            "drop_score": self.ocr.drop_score,
            "use_gpu": self.ocr.use_gpu,
            "gpu_mem": self.ocr.gpu_mem,
            "enable_mkldnn": self.ocr.enable_mkldnn,
            "cpu_threads": self.ocr.cpu_threads,
        }

    def reset_to_defaults(self):
        """Reset all settings to default values."""
        self.ocr = OCRSettings()
        self.export = ExportSettings()
        self.processing = ProcessingSettings()
        self.logging = LoggingSettings()
        self._config_data = {}

    def validate_settings(self) -> List[str]:
        """
        Validate current settings and return list of issues.

        Returns:
            List of validation issues (empty if all valid)
        """
        issues = []

        # Validate OCR settings
        if not 0.0 <= self.ocr.det_db_thresh <= 1.0:
            issues.append("OCR det_db_thresh must be between 0.0 and 1.0")

        if not 0.0 <= self.ocr.det_db_box_thresh <= 1.0:
            issues.append("OCR det_db_box_thresh must be between 0.0 and 1.0")

        if self.ocr.rec_batch_num <= 0:
            issues.append("OCR rec_batch_num must be positive")

        if self.ocr.cpu_threads <= 0:
            issues.append("OCR cpu_threads must be positive")

        # Validate export settings
        if self.export.default_format not in ["docx", "pdf"]:
            issues.append("Export default_format must be 'docx' or 'pdf'")

        if self.export.font_size <= 0:
            issues.append("Export font_size must be positive")

        # Validate processing settings
        if self.processing.min_text_length < 0:
            issues.append("Processing min_text_length must be non-negative")

        if self.processing.max_text_length <= self.processing.min_text_length:
            issues.append(
                "Processing max_text_length must be greater than min_text_length"
            )

        if not 0.0 <= self.processing.table_detection_threshold <= 1.0:
            issues.append(
                "Processing table_detection_threshold must be between 0.0 and 1.0"
            )

        # Validate logging settings
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.logging.level not in valid_log_levels:
            issues.append(f"Logging level must be one of: {valid_log_levels}")

        return issues

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a setting value with dictionary-style access.

        Args:
            key: Setting key (supports dot notation like 'logging.file_path')
            default: Default value if key not found

        Returns:
            Setting value or default
        """
        try:
            # Handle direct key access
            if hasattr(self, key):
                return getattr(self, key)

            # Handle dot notation (e.g., 'logging.level', 'ocr.lang')
            if "." in key:
                parts = key.split(".")
                if len(parts) == 2:
                    section, setting_key = parts
                    if hasattr(self, section):
                        section_obj = getattr(self, section)
                        if hasattr(section_obj, setting_key):
                            return getattr(section_obj, setting_key)

            # Handle common key mappings for backward compatibility
            key_mappings = {
                "log_file": "logging.file_path",
                "input_dir": "processing.input_directory",
                "output_dir": "processing.output_directory",
                "confidence_threshold": "processing.confidence_threshold",
                "language": "ocr.lang",
                "use_gpu": "ocr.use_gpu",
                "output_format": "export.default_format",
            }

            if key in key_mappings:
                return self.get(key_mappings[key], default)

            # Check in config data if available
            if key in self._config_data:
                return self._config_data[key]

            return default

        except Exception:
            return default
