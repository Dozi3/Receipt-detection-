"""Tests for robust error handling in OpenCV detection."""

import pytest
from PIL import Image, ImageDraw
import numpy as np
from pathlib import Path

from ..core.config import OpenCVConfig
from ..core.detection_opencv import detect_receipts_opencv, find_receipt_contours, apply_perspective_transform, pil_to_cv2


def create_synthetic_image_with_degenerate_contours():
    """Create a synthetic image with degenerate contours (lines, triangles, tiny quads)."""
    # Create a white background
    img = Image.new('RGB', (800, 1000), color='white')
    draw = ImageDraw.Draw(img)
    
    # Draw shapes in black
    draw.line((100, 100, 700, 100), fill='black', width=5)  # Line (2 points)
    draw.polygon([(200, 200), (300, 200), (250, 300)], fill='black')  # Triangle (3 points)
    draw.polygon([(400, 400), (410, 400), (410, 410), (400, 410)], fill='black')  # Tiny quad
    draw.polygon([(500, 500), (700, 500), (700, 700), (500, 700)], fill='black')  # Normal quad
    
    return img


def test_detect_receipts_with_degenerate_contours():
    """Test that detect_receipts_opencv doesn't crash with degenerate contours."""
    # Create synthetic image
    test_image = create_synthetic_image_with_degenerate_contours()
    
    # Create a minimal config
    config = OpenCVConfig(
        min_area_ratio=0.001,  # Make this small to detect even tiny quads
        max_area_ratio=0.9,
        min_aspect=0.1,
        max_aspect=10.0,
    )
    
    # Run detection
    results = detect_receipts_opencv([test_image], "test.pdf", 0, config)
    
    # Should not crash and should return at least the original image as fallback
    assert len(results) >= 1
    
    # The first result should be either the original image or a valid detection
    assert results[0].width > 0
    assert results[0].height > 0


def test_find_receipt_contours_with_bad_input():
    """Test that find_receipt_contours handles bad input."""
    # Create a blank image
    cv_image = np.zeros((100, 100), dtype=np.uint8)
    
    # Create a minimal config
    config = OpenCVConfig()
    
    # Test with valid input
    contours = find_receipt_contours(cv_image, (100, 100), config)
    assert isinstance(contours, list)
    
    # Test with empty image
    empty_image = np.zeros((0, 0), dtype=np.uint8)
    contours = find_receipt_contours(empty_image, (0, 0), config)
    assert isinstance(contours, list)
    assert len(contours) == 0


def test_perspective_transform_with_bad_quads():
    """Test that apply_perspective_transform handles bad quads."""
    # Create a test image
    cv_image = np.ones((100, 100, 3), dtype=np.uint8) * 255
    
    # Create a minimal config
    config = OpenCVConfig()
    
    # Test with valid quad
    valid_quad = np.array([[0, 0], [100, 0], [100, 100], [0, 100]], dtype=np.float32)
    result = apply_perspective_transform(cv_image, valid_quad, config)
    assert result is not None
    
    # Test with triangle (3 points)
    triangle = np.array([[0, 0], [100, 0], [50, 100]], dtype=np.float32)
    result = apply_perspective_transform(cv_image, triangle, config)
    assert result is None
    
    # Test with line (2 points)
    line = np.array([[0, 0], [100, 100]], dtype=np.float32)
    result = apply_perspective_transform(cv_image, line, config)
    assert result is None
    
    # Test with zero-area quad
    zero_quad = np.array([[0, 0], [0, 0], [0, 0], [0, 0]], dtype=np.float32)
    result = apply_perspective_transform(cv_image, zero_quad, config)
    assert result is None


if __name__ == "__main__":
    pytest.main([__file__])
