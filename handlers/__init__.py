"""
Handler modules for OCR text extraction system.

This package contains specialized handlers for specific image types and table formats.
"""

from .special_tables import SpecialTableHandler
from .image_specific import ImageSpecificHandler

__all__ = ["SpecialTableHandler", "ImageSpecificHandler"]
