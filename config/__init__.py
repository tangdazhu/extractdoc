"""
Configuration management for OCR text extraction system.

This package manages application settings, patterns, and configuration.
"""

from .settings import Settings, OCRSettings, ExportSettings
from .patterns import PatternLibrary

__all__ = ["Settings", "OCRSettings", "ExportSettings", "PatternLibrary"]
