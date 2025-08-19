#!/usr/bin/env python
"""
Create a simple test script that can help troubleshoot the issue with
the diagnostics.py file by testing the test_receipt_detection function.
"""

import sys
import os
import traceback
from pathlib import Path

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the necessary modules from receipt_analyzer
from receipt_analyzer.core.config import Config
from receipt_analyzer.core.pdf_io import get_page_images
from receipt_analyzer.core.detection_opencv import detect_receipts_opencv
from receipt_analyzer.core.detection_simple import detect_receipts_simple
from receipt_analyzer.core.logging_utils import configure_logging, log_info, log_warn, log_fail, log_debug, log_success

def get_test_config():
    """Create a test configuration."""
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

def test_receipt_detection(images, pdf_path, page_num, config, output_dir, save_images=False):
    """Test receipt detection with different methods."""
    if not images:
        log_fail("No images to test detection on")
        return []
    
    log_info(f"Testing receipt detection on {len(images)} images from page {page_num+1}")
    
    detected_receipts = []
    
    # Test OpenCV detection
    try:
        log_info("Testing OpenCV detection...")
        receipts_opencv = detect_receipts_opencv(images, str(pdf_path), page_num, config.opencv)
        log_info(f"OpenCV detection found {len(receipts_opencv) if receipts_opencv else 0} receipts")
        
        # Save detected receipts
        if receipts_opencv and save_images and output_dir:
            for i, receipt in enumerate(receipts_opencv):
                try:
                    img_path = output_dir / f"page_{page_num+1}_opencv_receipt_{i+1}.jpg"
                    receipt.save(img_path, "JPEG")
                    log_info(f"Saved OpenCV receipt to {img_path}")
                except Exception as save_err:
                    log_fail(f"Failed to save OpenCV receipt: {save_err}")
        
        detected_receipts.extend(receipts_opencv if receipts_opencv else [])
    except Exception as opencv_err:
        log_fail(f"OpenCV detection failed: {opencv_err}")
        log_debug(f"OpenCV detection error details: {traceback.format_exc()}")
    
    # Test simple detection
    try:
        log_info("Testing simple detection...")
        receipts_simple = detect_receipts_simple(images, str(pdf_path), page_num)
        log_info(f"Simple detection found {len(receipts_simple) if receipts_simple else 0} receipts")
        
        # Save detected receipts
        if receipts_simple and save_images and output_dir:
            for i, receipt in enumerate(receipts_simple):
                try:
                    img_path = output_dir / f"page_{page_num+1}_simple_receipt_{i+1}.jpg"
                    receipt.save(img_path, "JPEG")
                    log_info(f"Saved simple receipt to {img_path}")
                except Exception as save_err:
                    log_fail(f"Failed to save simple receipt: {save_err}")
                    
        # If no OpenCV receipts but we have simple receipts, use those
        if not detected_receipts:
            detected_receipts.extend(receipts_simple if receipts_simple else [])
    except Exception as simple_err:
        log_fail(f"Simple detection failed: {simple_err}")
        log_debug(f"Simple detection error details: {traceback.format_exc()}")
    
    # If we still have no receipts, just use the original images
    if not detected_receipts:
        log_warn("No receipts detected, using original images")
        detected_receipts = images
        
    return detected_receipts

def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage: python test_detection.py <pdf_path>")
        return
    
    pdf_path = sys.argv[1]
    
    if not Path(pdf_path).exists():
        log_fail(f"PDF file not found: {pdf_path}")
        return
    
    # Configure logging
    configure_logging()
    
    log_info("=" * 50)
    log_info(f"Testing receipt detection for {pdf_path}")
    log_info("=" * 50)
    
    # Create output directory
    output_dir = Path("./detection_test_output")
    output_dir.mkdir(exist_ok=True)
    
    # Create configuration
    config = get_test_config()
    
    # Get the page images
    page_num = 0  # First page (index 0)
    try:
        log_info(f"Getting images from page {page_num+1}...")
        images = get_page_images(Path(pdf_path), page_num)
        log_info(f"Got {len(images)} images from page {page_num+1}")
        
        # Save the extracted images
        for i, img in enumerate(images):
            try:
                img_path = output_dir / f"page_{page_num+1}_image_{i+1}.jpg"
                img.save(img_path, "JPEG")
                log_info(f"Saved extracted image to {img_path}")
            except Exception as save_err:
                log_fail(f"Failed to save extracted image: {save_err}")
        
        # Test receipt detection
        receipts = test_receipt_detection(images, pdf_path, page_num, config, output_dir, save_images=True)
        
        log_info(f"Detection found {len(receipts)} receipts")
        
    except Exception as e:
        log_fail(f"Error in test: {e}")
        log_debug(f"Error details: {traceback.format_exc()}")
    
    log_info("=" * 50)
    log_info("Test complete")
    log_info("=" * 50)

if __name__ == "__main__":
    main()
