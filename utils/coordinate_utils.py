"""
Coordinate processing utilities for OCR text extraction.

This module provides utilities for working with bounding boxes,
coordinate transformations, and spatial relationship analysis.
"""

import logging
from typing import List, Dict, Tuple, Optional, Any
import math

logger = logging.getLogger(__name__)


class CoordinateUtils:
    """Utilities for coordinate and bounding box operations."""

    @staticmethod
    def normalize_bbox(
        bbox: Tuple[int, int, int, int], image_width: int, image_height: int
    ) -> Tuple[float, float, float, float]:
        """
        Normalize bounding box coordinates to [0, 1] range.

        Args:
            bbox: Bounding box (x1, y1, x2, y2)
            image_width: Image width in pixels
            image_height: Image height in pixels

        Returns:
            Normalized bounding box coordinates
        """
        if image_width <= 0 or image_height <= 0:
            return (0.0, 0.0, 0.0, 0.0)

        x1, y1, x2, y2 = bbox
        return (
            x1 / image_width,
            y1 / image_height,
            x2 / image_width,
            y2 / image_height,
        )

    @staticmethod
    def denormalize_bbox(
        normalized_bbox: Tuple[float, float, float, float],
        image_width: int,
        image_height: int,
    ) -> Tuple[int, int, int, int]:
        """
        Convert normalized coordinates back to pixel coordinates.

        Args:
            normalized_bbox: Normalized bounding box coordinates
            image_width: Image width in pixels
            image_height: Image height in pixels

        Returns:
            Pixel bounding box coordinates
        """
        x1_norm, y1_norm, x2_norm, y2_norm = normalized_bbox
        return (
            int(x1_norm * image_width),
            int(y1_norm * image_height),
            int(x2_norm * image_width),
            int(y2_norm * image_height),
        )

    @staticmethod
    def calculate_bbox_area(bbox: Tuple[int, int, int, int]) -> int:
        """
        Calculate the area of a bounding box.

        Args:
            bbox: Bounding box (x1, y1, x2, y2)

        Returns:
            Area in square pixels
        """
        x1, y1, x2, y2 = bbox
        width = max(0, x2 - x1)
        height = max(0, y2 - y1)
        return width * height

    @staticmethod
    def calculate_bbox_center(bbox: Tuple[int, int, int, int]) -> Tuple[float, float]:
        """
        Calculate the center point of a bounding box.

        Args:
            bbox: Bounding box (x1, y1, x2, y2)

        Returns:
            Center coordinates (x, y)
        """
        x1, y1, x2, y2 = bbox
        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2
        return (center_x, center_y)

    @staticmethod
    def calculate_distance(
        point1: Tuple[float, float], point2: Tuple[float, float]
    ) -> float:
        """
        Calculate Euclidean distance between two points.

        Args:
            point1: First point (x, y)
            point2: Second point (x, y)

        Returns:
            Distance between points
        """
        x1, y1 = point1
        x2, y2 = point2
        return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

    @staticmethod
    def bbox_intersection(
        bbox1: Tuple[int, int, int, int], bbox2: Tuple[int, int, int, int]
    ) -> Optional[Tuple[int, int, int, int]]:
        """
        Calculate intersection of two bounding boxes.

        Args:
            bbox1: First bounding box (x1, y1, x2, y2)
            bbox2: Second bounding box (x1, y1, x2, y2)

        Returns:
            Intersection bounding box or None if no intersection
        """
        x1_1, y1_1, x2_1, y2_1 = bbox1
        x1_2, y1_2, x2_2, y2_2 = bbox2

        # Calculate intersection coordinates
        x1_intersect = max(x1_1, x1_2)
        y1_intersect = max(y1_1, y1_2)
        x2_intersect = min(x2_1, x2_2)
        y2_intersect = min(y2_1, y2_2)

        # Check if intersection exists
        if x1_intersect < x2_intersect and y1_intersect < y2_intersect:
            return (x1_intersect, y1_intersect, x2_intersect, y2_intersect)
        else:
            return None

    @staticmethod
    def bbox_union(
        bbox1: Tuple[int, int, int, int], bbox2: Tuple[int, int, int, int]
    ) -> Tuple[int, int, int, int]:
        """
        Calculate union of two bounding boxes.

        Args:
            bbox1: First bounding box (x1, y1, x2, y2)
            bbox2: Second bounding box (x1, y1, x2, y2)

        Returns:
            Union bounding box
        """
        x1_1, y1_1, x2_1, y2_1 = bbox1
        x1_2, y1_2, x2_2, y2_2 = bbox2

        return (min(x1_1, x1_2), min(y1_1, y1_2), max(x2_1, x2_2), max(y2_1, y2_2))

    @staticmethod
    def calculate_iou(
        bbox1: Tuple[int, int, int, int], bbox2: Tuple[int, int, int, int]
    ) -> float:
        """
        Calculate Intersection over Union (IoU) of two bounding boxes.

        Args:
            bbox1: First bounding box
            bbox2: Second bounding box

        Returns:
            IoU score between 0 and 1
        """
        intersection = CoordinateUtils.bbox_intersection(bbox1, bbox2)
        if intersection is None:
            return 0.0

        intersection_area = CoordinateUtils.calculate_bbox_area(intersection)
        area1 = CoordinateUtils.calculate_bbox_area(bbox1)
        area2 = CoordinateUtils.calculate_bbox_area(bbox2)

        union_area = area1 + area2 - intersection_area

        if union_area <= 0:
            return 0.0

        return intersection_area / union_area

    @staticmethod
    def is_bbox_inside(
        inner_bbox: Tuple[int, int, int, int],
        outer_bbox: Tuple[int, int, int, int],
        tolerance: int = 0,
    ) -> bool:
        """
        Check if one bounding box is inside another.

        Args:
            inner_bbox: Inner bounding box
            outer_bbox: Outer bounding box
            tolerance: Tolerance in pixels

        Returns:
            True if inner_bbox is inside outer_bbox
        """
        x1_inner, y1_inner, x2_inner, y2_inner = inner_bbox
        x1_outer, y1_outer, x2_outer, y2_outer = outer_bbox

        return (
            x1_outer - tolerance <= x1_inner
            and y1_outer - tolerance <= y1_inner
            and x2_inner <= x2_outer + tolerance
            and y2_inner <= y2_outer + tolerance
        )

    @staticmethod
    def expand_bbox(
        bbox: Tuple[int, int, int, int],
        expand_x: int,
        expand_y: int,
        image_width: int = None,
        image_height: int = None,
    ) -> Tuple[int, int, int, int]:
        """
        Expand bounding box by specified amounts.

        Args:
            bbox: Original bounding box
            expand_x: Expansion in x direction
            expand_y: Expansion in y direction
            image_width: Optional image width for boundary checking
            image_height: Optional image height for boundary checking

        Returns:
            Expanded bounding box
        """
        x1, y1, x2, y2 = bbox

        # Expand the box
        new_x1 = x1 - expand_x
        new_y1 = y1 - expand_y
        new_x2 = x2 + expand_x
        new_y2 = y2 + expand_y

        # Clamp to image boundaries if provided
        if image_width is not None:
            new_x1 = max(0, new_x1)
            new_x2 = min(image_width, new_x2)

        if image_height is not None:
            new_y1 = max(0, new_y1)
            new_y2 = min(image_height, new_y2)

        return (new_x1, new_y1, new_x2, new_y2)

    @staticmethod
    def group_bboxes_by_proximity(
        bboxes: List[Tuple[int, int, int, int]], threshold: float = 50.0
    ) -> List[List[int]]:
        """
        Group bounding boxes by spatial proximity.

        Args:
            bboxes: List of bounding boxes
            threshold: Distance threshold for grouping

        Returns:
            List of groups, each containing indices of related bboxes
        """
        if not bboxes:
            return []

        # Calculate centers
        centers = [CoordinateUtils.calculate_bbox_center(bbox) for bbox in bboxes]

        # Initialize groups
        groups = []
        assigned = [False] * len(bboxes)

        for i, center in enumerate(centers):
            if assigned[i]:
                continue

            # Start new group
            current_group = [i]
            assigned[i] = True

            # Find nearby boxes
            for j, other_center in enumerate(centers):
                if assigned[j]:
                    continue

                distance = CoordinateUtils.calculate_distance(center, other_center)
                if distance <= threshold:
                    current_group.append(j)
                    assigned[j] = True

            groups.append(current_group)

        return groups

    @staticmethod
    def sort_bboxes_reading_order(bboxes: List[Tuple[int, int, int, int]]) -> List[int]:
        """
        Sort bounding boxes in reading order (top to bottom, left to right).

        Args:
            bboxes: List of bounding boxes

        Returns:
            List of indices in reading order
        """
        if not bboxes:
            return []

        # Create list of (index, bbox) pairs
        indexed_bboxes = list(enumerate(bboxes))

        # Sort by y coordinate first (top to bottom), then by x coordinate (left to right)
        sorted_bboxes = sorted(indexed_bboxes, key=lambda x: (x[1][1], x[1][0]))

        # Return sorted indices
        return [index for index, _ in sorted_bboxes]

    @staticmethod
    def merge_overlapping_bboxes(
        bboxes: List[Tuple[int, int, int, int]], overlap_threshold: float = 0.5
    ) -> List[Tuple[int, int, int, int]]:
        """
        Merge overlapping bounding boxes.

        Args:
            bboxes: List of bounding boxes
            overlap_threshold: IoU threshold for merging

        Returns:
            List of merged bounding boxes
        """
        if not bboxes:
            return []

        merged_bboxes = []
        remaining_bboxes = bboxes.copy()

        while remaining_bboxes:
            current_bbox = remaining_bboxes.pop(0)
            merged_with_current = [current_bbox]

            # Find overlapping boxes
            i = 0
            while i < len(remaining_bboxes):
                other_bbox = remaining_bboxes[i]
                iou = CoordinateUtils.calculate_iou(current_bbox, other_bbox)

                if iou >= overlap_threshold:
                    merged_with_current.append(remaining_bboxes.pop(i))
                    # Update current_bbox to be the union
                    current_bbox = CoordinateUtils.bbox_union(current_bbox, other_bbox)
                else:
                    i += 1

            # Compute final merged bbox
            if len(merged_with_current) > 1:
                final_bbox = merged_with_current[0]
                for bbox in merged_with_current[1:]:
                    final_bbox = CoordinateUtils.bbox_union(final_bbox, bbox)
                merged_bboxes.append(final_bbox)
            else:
                merged_bboxes.append(current_bbox)

        return merged_bboxes

    @staticmethod
    def validate_bbox(
        bbox: Tuple[int, int, int, int],
        image_width: int = None,
        image_height: int = None,
    ) -> bool:
        """
        Validate bounding box coordinates.

        Args:
            bbox: Bounding box to validate
            image_width: Optional image width for boundary checking
            image_height: Optional image height for boundary checking

        Returns:
            True if bbox is valid
        """
        if len(bbox) != 4:
            return False

        x1, y1, x2, y2 = bbox

        # Check coordinate ordering
        if x1 >= x2 or y1 >= y2:
            return False

        # Check non-negative coordinates
        if x1 < 0 or y1 < 0:
            return False

        # Check image boundaries if provided
        if image_width is not None and x2 > image_width:
            return False

        if image_height is not None and y2 > image_height:
            return False

        return True
