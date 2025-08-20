"""Tests for robust error handling in OCR processing."""

import pytest
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

from ..core.config import OCRConfig
from ..core.ocr import perform_ocr, extract_text_with_orientation, check_tesseract_available


def create_tiny_text_image(size=(20, 10), text="TEST"):
    """Create a tiny image with text for OCR testing."""
    img = Image.new('RGB', size, color='white')
    draw = ImageDraw.Draw(img)
    
    # Try to use a small font if possible
    try:
        font = ImageFont.truetype("arial.ttf", 8)
    except IOError:
        # Draw text without font
        draw.text((2, 1), text, fill='black')
    else:
        draw.text((2, 1), text, fill='black', font=font)
    
    return img


def create_normal_text_image(size=(200, 100), text="Receipt Test"):
    """Create a normal-sized image with text for OCR testing."""
    img = Image.new('RGB', size, color='white')
    draw = ImageDraw.Draw(img)
    
    try:
        font = ImageFont.truetype("arial.ttf", 20)
    except IOError:
        # Draw text without font
        draw.text((40, 40), text, fill='black')
    else:
        draw.text((40, 40), text, fill='black', font=font)
    
    return img


def test_ocr_with_tiny_image():
    """Test that OCR doesn't crash with very small images."""
    # Skip if Tesseract not available
    tesseract_available, _ = check_tesseract_available()
    if not tesseract_available:
        pytest.skip("Tesseract not available for testing")
    
    # Create a tiny image
    tiny_image = create_tiny_text_image()
    
    # Create a minimal config
    config = OCRConfig()
    
    # Perform OCR
    text, metadata = perform_ocr(tiny_image, config, "test.pdf", 0, 0)
    
    # Should not crash, might not extract text
    assert isinstance(text, str)
    assert isinstance(metadata, dict)


def test_ocr_orientation_with_small_image():
    """Test that orientation detection handles small images gracefully."""
    # Skip if Tesseract not available
    tesseract_available, _ = check_tesseract_available()
    if not tesseract_available:
        pytest.skip("Tesseract not available for testing")
    
    # Create a small image
    small_image = create_tiny_text_image(size=(80, 40))
    
    # Create a minimal config
    config = OCRConfig()
    
    # Try to extract text with orientation
    try:
        text, angle, confidences = extract_text_with_orientation(small_image, config)
        
        # Should return some values (even if empty)
        assert isinstance(text, str)
        assert isinstance(angle, int)
        assert isinstance(confidences, dict)
        
    except Exception as e:
        # If an exception occurs, the test fails
        pytest.fail(f"extract_text_with_orientation raised {e} with small image")


def test_ocr_with_none_image():
    """Test that OCR handles None images gracefully."""
    # Create a minimal config
    config = OCRConfig()
    
    # Perform OCR with None image
    text, metadata = perform_ocr(None, config, "test.pdf", 0, 0)
    
    # Should not crash, should return empty results
    assert text == ""
    assert metadata == {}


def test_ocr_with_normal_image():
    """Test OCR with normal-sized image."""
    # Skip if Tesseract not available
    tesseract_available, _ = check_tesseract_available()
    if not tesseract_available:
        pytest.skip("Tesseract not available for testing")
    
    # Create a normal image with text
    normal_image = create_normal_text_image()
    
    # Create a minimal config
    config = OCRConfig()
    
    # Perform OCR
    text, metadata = perform_ocr(normal_image, config, "test.pdf", 0, 0)
    
    # Should extract text successfully
    assert isinstance(text, str)
    assert isinstance(metadata, dict)


if __name__ == "__main__":
    pytest.main([__file__])
