"""
Image-specific handlers for OCR text extraction.

This module contains handlers for different image types and formats
that require specialized processing approaches.
"""

import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import cv2
import numpy as np

logger = logging.getLogger(__name__)


class ImageSpecificHandler:
    """Handles image-specific processing requirements."""

    def __init__(self):
        self.logger = logger
        self._init_image_patterns()

    def _init_image_patterns(self):
        """Initialize patterns for image type detection."""
        self.image_type_patterns = {
            "screenshot": [
                r"screenshot|屏幕截图|snap",
                r"browser|浏览器|chrome|firefox",
                r"desktop|桌面",
            ],
            "document_scan": [
                r"scan|扫描|scanned",
                r"document|文档|doc",
                r"page|页面|sheet",
            ],
            "presentation_slide": [
                r"slide|幻灯片|ppt|powerpoint",
                r"presentation|演示|讲座",
                r"title|标题|heading",
            ],
            "table_image": [
                r"table|表格|grid",
                r"row|column|行|列",
                r"cell|单元格|data",
            ],
            "form_image": [
                r"form|表单|申请|application",
                r"field|字段|input|输入",
                r"checkbox|选择框|radio",
            ],
        }

    def detect_image_type(
        self, image_path: str, extracted_text: str = ""
    ) -> Optional[str]:
        """
        Detect the type of image based on filename and content.

        Args:
            image_path: Path to the image file
            extracted_text: Text extracted from the image

        Returns:
            Detected image type or None
        """
        try:
            filename = Path(image_path).name.lower()
            combined_text = f"{filename} {extracted_text}".lower()

            # Check patterns for each image type
            for image_type, patterns in self.image_type_patterns.items():
                match_count = 0
                for pattern in patterns:
                    if re.search(pattern, combined_text):
                        match_count += 1

                # If enough patterns match, classify as this type
                if match_count >= len(patterns) * 0.5:
                    return image_type

            return None

        except Exception as e:
            self.logger.error(f"Error detecting image type for {image_path}: {e}")
            return None

    def preprocess_image_by_type(
        self, image_path: str, image_type: Optional[str] = None
    ) -> Optional[np.ndarray]:
        """
        Preprocess image based on its detected type.

        Args:
            image_path: Path to the image file
            image_type: Detected image type (if known)

        Returns:
            Preprocessed image array or None
        """
        try:
            # Load image
            image = cv2.imread(image_path)
            if image is None:
                self.logger.error(f"Could not load image: {image_path}")
                return None

            # Detect image type if not provided
            if image_type is None:
                image_type = self.detect_image_type(image_path)

            # Apply type-specific preprocessing
            if image_type == "screenshot":
                return self._preprocess_screenshot(image)
            elif image_type == "document_scan":
                return self._preprocess_document_scan(image)
            elif image_type == "presentation_slide":
                return self._preprocess_presentation_slide(image)
            elif image_type == "table_image":
                return self._preprocess_table_image(image)
            elif image_type == "form_image":
                return self._preprocess_form_image(image)
            else:
                return self._preprocess_generic_image(image)

        except Exception as e:
            self.logger.error(f"Error preprocessing image {image_path}: {e}")
            return None

    def _preprocess_screenshot(self, image: np.ndarray) -> np.ndarray:
        """Preprocess screenshot images."""
        # Screenshots often have good quality but may need contrast enhancement

        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Enhance contrast
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)

        # Slight denoising
        denoised = cv2.fastNlMeansDenoising(enhanced)

        return denoised

    def _preprocess_document_scan(self, image: np.ndarray) -> np.ndarray:
        """Preprocess scanned document images."""
        # Scanned documents may have skew, noise, and varying lighting

        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Deskew if needed
        deskewed = self._deskew_image(gray)

        # Remove noise
        denoised = cv2.fastNlMeansDenoising(deskewed)

        # Binarize to improve text clarity
        _, binary = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        return binary

    def _preprocess_presentation_slide(self, image: np.ndarray) -> np.ndarray:
        """Preprocess presentation slide images."""
        # Slides often have varied backgrounds and multiple text sizes

        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Enhance contrast for better text visibility
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)

        # Morphological operations to connect text
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 1))
        morphed = cv2.morphologyEx(enhanced, cv2.MORPH_CLOSE, kernel)

        return morphed

    def _preprocess_table_image(self, image: np.ndarray) -> np.ndarray:
        """Preprocess table images with emphasis on structure preservation."""
        # Tables need clear line detection and cell separation

        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Enhance edges for better table line detection
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)
        edges = cv2.Canny(blurred, 50, 150)

        # Dilate to connect broken lines
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        dilated = cv2.dilate(edges, kernel, iterations=1)

        # Combine with original for final result
        result = cv2.bitwise_or(gray, dilated)

        return result

    def _preprocess_form_image(self, image: np.ndarray) -> np.ndarray:
        """Preprocess form images with focus on field detection."""
        # Forms have structured layout with fields and labels

        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Enhance text while preserving form structure
        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)

        # Remove noise while preserving form lines
        denoised = cv2.bilateralFilter(enhanced, 9, 75, 75)

        return denoised

    def _preprocess_generic_image(self, image: np.ndarray) -> np.ndarray:
        """Generic preprocessing for unclassified images."""
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Basic enhancement
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)

        # Light denoising
        denoised = cv2.fastNlMeansDenoising(enhanced, h=10)

        return denoised

    def _deskew_image(self, image: np.ndarray) -> np.ndarray:
        """Detect and correct image skew."""
        try:
            # Find edges
            edges = cv2.Canny(image, 50, 150, apertureSize=3)

            # Find lines using Hough transform
            lines = cv2.HoughLines(edges, 1, np.pi / 180, threshold=100)

            if lines is not None:
                # Calculate average angle
                angles = []
                for rho, theta in lines[:20]:  # Use only first 20 lines
                    angle = np.degrees(theta) - 90
                    if abs(angle) < 45:  # Only consider reasonable angles
                        angles.append(angle)

                if angles:
                    avg_angle = np.mean(angles)

                    # Rotate image to correct skew
                    if abs(avg_angle) > 0.5:  # Only rotate if significant skew
                        (h, w) = image.shape[:2]
                        center = (w // 2, h // 2)
                        rotation_matrix = cv2.getRotationMatrix2D(
                            center, avg_angle, 1.0
                        )
                        rotated = cv2.warpAffine(
                            image,
                            rotation_matrix,
                            (w, h),
                            flags=cv2.INTER_CUBIC,
                            borderMode=cv2.BORDER_REPLICATE,
                        )
                        return rotated

            return image

        except Exception as e:
            self.logger.warning(f"Could not deskew image: {e}")
            return image

    def extract_image_regions(
        self, image_path: str, region_type: str = "text"
    ) -> List[Dict]:
        """
        Extract specific regions from image based on type.

        Args:
            image_path: Path to the image file
            region_type: Type of regions to extract ('text', 'table', 'form')

        Returns:
            List of detected regions with bounding boxes
        """
        try:
            # Load image
            image = cv2.imread(image_path)
            if image is None:
                return []

            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

            if region_type == "text":
                return self._extract_text_regions(gray)
            elif region_type == "table":
                return self._extract_table_regions(gray)
            elif region_type == "form":
                return self._extract_form_regions(gray)
            else:
                return []

        except Exception as e:
            self.logger.error(f"Error extracting regions from {image_path}: {e}")
            return []

    def _extract_text_regions(self, gray_image: np.ndarray) -> List[Dict]:
        """Extract text regions from image."""
        regions = []

        try:
            # Use MSER for text region detection
            mser = cv2.MSER_create()
            regions_mser, _ = mser.detectRegions(gray_image)

            for region in regions_mser:
                x, y, w, h = cv2.boundingRect(region.reshape(-1, 1, 2))

                # Filter by size (likely text regions)
                if (
                    10 < w < gray_image.shape[1] * 0.8
                    and 5 < h < gray_image.shape[0] * 0.3
                ):
                    regions.append(
                        {
                            "type": "text",
                            "bbox": (x, y, x + w, y + h),
                            "confidence": 0.8,
                        }
                    )

        except Exception as e:
            self.logger.warning(f"MSER text detection failed: {e}")

        return regions

    def _extract_table_regions(self, gray_image: np.ndarray) -> List[Dict]:
        """Extract table regions from image."""
        regions = []

        try:
            # Detect horizontal and vertical lines
            horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
            vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))

            horizontal_lines = cv2.morphologyEx(
                gray_image, cv2.MORPH_OPEN, horizontal_kernel
            )
            vertical_lines = cv2.morphologyEx(
                gray_image, cv2.MORPH_OPEN, vertical_kernel
            )

            # Combine lines
            table_mask = cv2.addWeighted(
                horizontal_lines, 0.5, vertical_lines, 0.5, 0.0
            )

            # Find contours
            contours, _ = cv2.findContours(
                table_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )

            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)

                # Filter by size (likely table regions)
                if w > 100 and h > 50:
                    regions.append(
                        {
                            "type": "table",
                            "bbox": (x, y, x + w, y + h),
                            "confidence": 0.7,
                        }
                    )

        except Exception as e:
            self.logger.warning(f"Table detection failed: {e}")

        return regions

    def _extract_form_regions(self, gray_image: np.ndarray) -> List[Dict]:
        """Extract form field regions from image."""
        regions = []

        try:
            # Detect rectangular regions (form fields)
            edges = cv2.Canny(gray_image, 50, 150)
            contours, _ = cv2.findContours(
                edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )

            for contour in contours:
                # Approximate contour
                epsilon = 0.02 * cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, epsilon, True)

                # Check if it's roughly rectangular
                if len(approx) >= 4:
                    x, y, w, h = cv2.boundingRect(contour)

                    # Filter by size and aspect ratio (likely form fields)
                    aspect_ratio = w / h if h > 0 else 0
                    if (
                        20 < w < gray_image.shape[1] * 0.8
                        and 10 < h < 100
                        and 1 < aspect_ratio < 20
                    ):
                        regions.append(
                            {
                                "type": "form_field",
                                "bbox": (x, y, x + w, y + h),
                                "confidence": 0.6,
                            }
                        )

        except Exception as e:
            self.logger.warning(f"Form detection failed: {e}")

        return regions

    def get_optimal_ocr_config(
        self, image_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get optimal OCR configuration for specific image type.

        Args:
            image_type: Detected image type

        Returns:
            OCR configuration dictionary
        """
        base_config = {
            "use_angle_cls": True,
            "lang": "ch",
            "det": True,
            "rec": True,
            "cls": True,
        }

        if image_type == "screenshot":
            base_config.update({"det_db_thresh": 0.3, "det_db_box_thresh": 0.5})
        elif image_type == "document_scan":
            base_config.update({"det_db_thresh": 0.2, "det_db_box_thresh": 0.4})
        elif image_type == "presentation_slide":
            base_config.update({"det_db_thresh": 0.4, "det_db_box_thresh": 0.6})
        elif image_type == "table_image":
            base_config.update({"det_db_thresh": 0.2, "det_db_box_thresh": 0.3})
        elif image_type == "form_image":
            base_config.update({"det_db_thresh": 0.3, "det_db_box_thresh": 0.4})

        return base_config
