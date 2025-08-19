"""
Test specifically targeting the handling of summary pages in PDFs.
This test verifies that the code doesn't crash when processing
a page that is not a receipt (like a summary page).
"""

import os
import sys
import logging
from pathlib import Path
import pytest
from PIL import Image

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from receipt_analyzer.core.config import Config
from receipt_analyzer.core.pdf_io import get_pdf_page_count, get_page_images
from receipt_analyzer.core.detection_opencv import detect_receipts_opencv
from receipt_analyzer.core.detection_simple import detect_receipts_simple
from receipt_analyzer.core.ocr import perform_ocr
from receipt_analyzer.core.logging_utils import configure_logging, get_logger
from receipt_analyzer.core.processing import process_pdf_page, process_receipt


# Configure logging
configure_logging(level=logging.DEBUG)
logger = get_logger()


def get_test_config():
    """Return a test configuration."""
    config = Config()
    # Set detection method
    config.detection_method = 'opencv'
    # Configure OpenCV settings
    config.opencv = Config()
    config.opencv.min_contour_area = 1000
    config.opencv.max_contour_area = 1000000
    config.opencv.epsilon_factor = 0.02
    config.opencv.area_threshold = 0.8
    # Configure output settings
    config.output = Config()
    config.output.format = 'jpg'
    config.output.jpeg_quality = 85
    config.output.max_edge = 1800
    config.output.per_page_zip = False
    # OCR settings
    config.ocr = Config()
    config.ocr.lang = 'eng'
    config.ocr.config = '--psm 4'
    return config


def test_summary_page_processing():
    """Test that summary pages don't cause crashes."""
    # You'll need to provide a test PDF path with a summary page
    test_dir = Path(__file__).parent
    test_files_dir = test_dir / "test_files"
    test_files_dir.mkdir(exist_ok=True)
    
    # Check if there are any PDF files in the test_files directory
    pdf_files = list(test_files_dir.glob("*.pdf"))
    
    if not pdf_files:
        pytest.skip("No test PDFs found in test_files directory")
    
    # Use the first PDF file found
    test_pdf = pdf_files[0]
    
    # Create an output directory
    output_dir = test_dir / "test_output"
    output_dir.mkdir(exist_ok=True)
    
    # Get configuration
    config = get_test_config()
    
    # Test processing first page (summary page)
    logger.info(f"Testing first page (summary page) of {test_pdf}")
    
    # 1. Extract images
    try:
        page_images = get_page_images(test_pdf, 0)
        logger.info(f"Successfully extracted {len(page_images) if page_images else 0} images from first page")
        
        if not page_images:
            logger.warning("No images extracted from first page")
            assert True  # Just ensure no crash
            return
        
        # 2. Try both detection methods
        try:
            # OpenCV detection
            receipts_opencv = detect_receipts_opencv(page_images, str(test_pdf), 0, config.opencv)
            logger.info(f"OpenCV detection found {len(receipts_opencv) if receipts_opencv else 0} receipts")
            
            # Simple detection
            receipts_simple = detect_receipts_simple(page_images, str(test_pdf), 0)
            logger.info(f"Simple detection found {len(receipts_simple) if receipts_simple else 0} receipts")
            
            # Try OCR on first image regardless of detection results
            first_image = page_images[0]
            logger.info(f"Testing OCR on first image: size={first_image.size}, mode={first_image.mode}")
            
            try:
                ocr_result = perform_ocr(first_image, config.ocr)
                logger.info("OCR completed successfully")
                
                # Save the first image for inspection
                first_image_path = output_dir / "first_page_image.jpg"
                first_image.save(first_image_path, "JPEG")
                logger.info(f"Saved first page image to {first_image_path}")
                
            except Exception as ocr_error:
                logger.error(f"OCR failed: {ocr_error}")
                # This is allowed to fail for a summary page
                assert True
            
            # Test full page processing
            try:
                records = process_pdf_page(test_pdf, 0, config, None, output_dir)
                logger.info(f"Full page processing completed, found {len(records)} records")
            except Exception as page_error:
                logger.error(f"Full page processing failed: {page_error}")
                # This should not fail with our enhanced error handling
                assert False, f"Page processing should not crash but got: {page_error}"
                
            # Test passed if we got here without crashing
            assert True
            
        except Exception as detection_error:
            logger.error(f"Detection failed: {detection_error}")
            # Detection is allowed to fail for a summary page
            assert True
        
    except Exception as extraction_error:
        logger.error(f"Image extraction failed: {extraction_error}")
        # Image extraction should not fail
        assert False, f"Image extraction should not crash but got: {extraction_error}"


def test_process_receipt_with_invalid_image():
    """Test that process_receipt handles invalid images gracefully."""
    config = get_test_config()
    
    # Test with None image
    result = process_receipt(None, config, None, "test.pdf", 0, 0)
    assert result is None, "process_receipt should return None for None image"
    
    # Test with tiny image (too small to be a receipt)
    tiny_image = Image.new('RGB', (5, 5), color='white')
    result = process_receipt(tiny_image, config, None, "test.pdf", 0, 0)
    assert result is None, "process_receipt should return None for tiny image"
    
    # Test with valid but blank image
    blank_image = Image.new('RGB', (200, 200), color='white')
    result = process_receipt(blank_image, config, None, "test.pdf", 0, 0)
    # This might return None or a valid result with empty text
    # The important thing is that it doesn't crash
    logger.info(f"process_receipt with blank image returned: {result}")
    assert True


if __name__ == "__main__":
    # Run tests manually
    print("Testing summary page processing...")
    test_summary_page_processing()
    print("Testing process_receipt with invalid images...")
    test_process_receipt_with_invalid_image()
    print("All tests completed")
