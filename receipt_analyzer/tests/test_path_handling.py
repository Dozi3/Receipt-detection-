"""Tests for robust path handling and filename safety."""

import pytest
import tempfile
import os
from pathlib import Path

from ..core.naming import safe_filename, unique_path, build_receipt_filename
from ..core.parsing import ParsedReceipt
from ..core.processing import save_image
from ..core.config import Config, OutputConfig
from PIL import Image


def test_safe_filename_with_unicode():
    """Test that safe_filename handles Unicode characters properly."""
    # Test Unicode characters
    assert safe_filename("résumé.pdf") == "résumé.pdf"
    assert safe_filename("документ.pdf") == "документ.pdf"
    assert safe_filename("文档.pdf") == "文档.pdf"
    
    # Test with spaces
    assert safe_filename("my file name.pdf") == "my_file_name.pdf"
    
    # Test with Windows-reserved characters
    unsafe_name = "file<>:\"/\\|?*name.pdf"
    safe_name = safe_filename(unsafe_name)
    assert "<" not in safe_name
    assert ">" not in safe_name
    assert ":" not in safe_name
    assert "\"" not in safe_name
    assert "/" not in safe_name
    assert "\\" not in safe_name
    assert "?" not in safe_name
    assert "*" not in safe_name


def test_safe_filename_with_reserved_names():
    """Test that safe_filename handles Windows reserved names properly."""
    # Test Windows reserved names
    reserved_names = ["CON", "PRN", "AUX", "NUL", 
                     "COM1", "COM2", "COM3", "COM4", "COM5",
                     "LPT1", "LPT2", "LPT3", "LPT4", "LPT5"]
    
    for name in reserved_names:
        # Each reserved name should be modified
        assert safe_filename(name) != name
        assert "_" in safe_filename(name)
        
    # Test with extensions
    assert safe_filename("CON.pdf") != "CON.pdf"
    assert "_" in safe_filename("CON.pdf")


def test_unique_path_with_unicode():
    """Test that unique_path handles Unicode paths properly."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a path with Unicode
        unicode_name = "тест_файл.txt"
        base_path = Path(temp_dir) / unicode_name
        
        # First call should return the same path
        unique1 = unique_path(base_path)
        assert unique1 == base_path
        
        # Create the file
        with open(base_path, 'w') as f:
            f.write("test")
        
        # Next call should return a different path
        unique2 = unique_path(base_path)
        assert unique2 != base_path
        assert unicode_name.split('.')[0] in unique2.name


def test_build_receipt_filename_with_special_chars():
    """Test that build_receipt_filename handles special characters in vendor names."""
    from datetime import date
    
    receipt = ParsedReceipt()
    receipt.vendor = "Café & Bar/Lounge"
    receipt.amount = 12.34
    receipt.date = date(2023, 12, 25)
    
    filename = build_receipt_filename(receipt, "png")
    
    # Should sanitize special characters
    assert "/" not in filename
    assert "&" not in filename
    assert " " not in filename
    assert filename.endswith(".png")
    assert "Café" in filename  # Unicode should be preserved


def test_save_image_with_unicode_path():
    """Test that save_image works with Unicode paths."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a config
        config = Config()
        config.output = OutputConfig(format="png")
        
        # Create a simple test image
        img = Image.new('RGB', (100, 100), color='white')
        
        # Try with Unicode path
        unicode_path = Path(temp_dir) / "тестовый_файл.png"
        
        # Save image
        result = save_image(img, unicode_path, config)
        
        # Should succeed and create the file
        assert result is True
        assert unicode_path.exists()


if __name__ == "__main__":
    pytest.main([__file__])
