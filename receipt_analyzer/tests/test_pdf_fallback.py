"""Tests for robust PDF rasterization and fallback mechanisms."""

import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from ..core.pdf_io import rasterize_page_pdf2image, rasterize_page_pymupdf, get_page_images


def test_rasterize_page_pdf2image_with_missing_poppler():
    """Test that rasterize_page_pdf2image handles missing Poppler gracefully."""
    # Mock Path
    test_path = Path("test.pdf")
    
    # Mock ImportError for pdf2image
    with patch("importlib.import_module", side_effect=ImportError("No module named 'pdf2image'")):
        result = rasterize_page_pdf2image(test_path, 0)
        
        # Should return None but not crash
        assert result is None


def test_rasterize_page_pdf2image_with_conversion_error():
    """Test that rasterize_page_pdf2image handles conversion errors gracefully."""
    # Mock Path
    test_path = Path("test.pdf")
    
    # Mock pdf2image but make convert_from_path throw an exception
    with patch("pdf2image.convert_from_path", side_effect=Exception("Conversion failed")):
        result = rasterize_page_pdf2image(test_path, 0)
        
        # Should return None but not crash
        assert result is None


def test_rasterize_page_pdf2image_timeout():
    """Test that rasterize_page_pdf2image handles timeouts gracefully."""
    # Skip in automated testing as it might actually time out
    if "CI" in os.environ:
        pytest.skip("Skipping timeout test in CI environment")
    
    # Mock Path
    test_path = Path("test.pdf")
    
    # Mock pdf2image but make convert_from_path hang
    def mock_hang(*args, **kwargs):
        import time
        time.sleep(20)  # Longer than our timeout
        return []
    
    with patch("pdf2image.convert_from_path", side_effect=mock_hang):
        result = rasterize_page_pdf2image(test_path, 0)
        
        # Should return None but not crash
        assert result is None


def test_get_page_images_fallback_chain():
    """Test that get_page_images tries all fallback methods."""
    # Mock Path
    test_path = Path("test.pdf")
    
    # Mock extract_embedded_images to return empty list
    # Mock rasterize_page_pymupdf to return None
    # Mock rasterize_page_pdf2image to return None
    with patch("receipt_analyzer.core.pdf_io.extract_embedded_images", return_value=[]), \
         patch("receipt_analyzer.core.pdf_io.rasterize_page_pymupdf", return_value=None), \
         patch("receipt_analyzer.core.pdf_io.rasterize_page_pdf2image", return_value=None):
        
        result = get_page_images(test_path, 0)
        
        # Should return empty list but not crash
        assert isinstance(result, list)
        assert len(result) == 0


def test_get_page_images_with_exceptions():
    """Test that get_page_images handles exceptions in fallback methods."""
    # Mock Path
    test_path = Path("test.pdf")
    
    # Bypass extract_embedded_images by making it return an empty list
    # Then test the fallback methods
    with patch("receipt_analyzer.core.pdf_io.extract_embedded_images", 
              return_value=[]), \
         patch("receipt_analyzer.core.pdf_io.rasterize_page_pymupdf", 
              side_effect=Exception("PyMuPDF failed")), \
         patch("receipt_analyzer.core.pdf_io.rasterize_page_pdf2image", 
              side_effect=Exception("pdf2image failed")):
        
        result = get_page_images(test_path, 0)
        
        # Should return empty list but not crash
        assert isinstance(result, list)
        assert len(result) == 0


if __name__ == "__main__":
    pytest.main([__file__])
