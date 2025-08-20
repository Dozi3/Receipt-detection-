#!/usr/bin/env python
"""
Create a simple test script to test processing the second page of a PDF,
which is expected to contain a receipt.
"""

import sys
import os
import traceback
from pathlib import Path

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the necessary modules from receipt_analyzer
from receipt_analyzer.core.config import Config
from receipt_analyzer.core.pdf_io import get_page_images, get_pdf_page_count
from receipt_analyzer.core.detection_opencv import detect_receipts_opencv
from receipt_analyzer.core.detection_simple import detect_receipts_simple
from receipt_analyzer.core.ocr import perform_ocr
from receipt_analyzer.core.processing import process_pdf_page
from receipt_analyzer.core.vendors import load_vendor_map
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

def test_processing_second_page(pdf_path):
    """Test processing the second page of a PDF file."""
    try:
        # Create output directory
        output_dir = Path("./second_page_output")
        output_dir.mkdir(exist_ok=True)
        
        # Load config
        config = get_test_config()
        
        # Load vendor map
        vendor_map = load_vendor_map()
        
        # Check PDF page count
        pdf_path_obj = Path(pdf_path)
        page_count = get_pdf_page_count(pdf_path_obj)
        log_info(f"PDF has {page_count} pages")
        
        if page_count < 2:
            log_fail(f"PDF has fewer than 2 pages")
            return
        
        # Process second page (index 1)
        page_num = 1
        log_info(f"Processing second page of {pdf_path}")
        
        # Extract images
        log_info("Extracting images from second page...")
        try:
            images = get_page_images(pdf_path_obj, page_num)
            log_info(f"Extracted {len(images)} images")
            
            if not images:
                log_fail("Failed to extract any images from second page")
                return
                
            # Save extracted images
            for i, img in enumerate(images):
                try:
                    img_path = output_dir / f"extracted_image_{i+1}.jpg"
                    img.save(img_path, "JPEG")
                    log_info(f"Saved extracted image to {img_path}")
                except Exception as save_err:
                    log_fail(f"Failed to save extracted image: {save_err}")
        except Exception as extract_err:
            log_fail(f"Error extracting images: {extract_err}")
            log_debug(f"Extraction error details: {traceback.format_exc()}")
            return
            
        # Test receipt detection
        log_info("Testing receipt detection...")
        
        # Test OpenCV detection
        try:
            log_info("Using OpenCV detection...")
            receipts_opencv = detect_receipts_opencv(images, str(pdf_path), page_num, config.opencv)
            log_info(f"OpenCV detection found {len(receipts_opencv) if receipts_opencv else 0} receipts")
            
            # Save detected receipts
            if receipts_opencv:
                for i, receipt in enumerate(receipts_opencv):
                    try:
                        img_path = output_dir / f"opencv_receipt_{i+1}.jpg"
                        receipt.save(img_path, "JPEG")
                        log_info(f"Saved OpenCV receipt to {img_path}")
                    except Exception as save_err:
                        log_fail(f"Failed to save OpenCV receipt: {save_err}")
        except Exception as opencv_err:
            log_fail(f"OpenCV detection failed: {opencv_err}")
            log_debug(f"OpenCV detection error details: {traceback.format_exc()}")
        
        # Test simple detection
        try:
            log_info("Using simple detection...")
            receipts_simple = detect_receipts_simple(images, str(pdf_path), page_num)
            log_info(f"Simple detection found {len(receipts_simple) if receipts_simple else 0} receipts")
            
            # Save detected receipts
            if receipts_simple:
                for i, receipt in enumerate(receipts_simple):
                    try:
                        img_path = output_dir / f"simple_receipt_{i+1}.jpg"
                        receipt.save(img_path, "JPEG")
                        log_info(f"Saved simple receipt to {img_path}")
                    except Exception as save_err:
                        log_fail(f"Failed to save simple receipt: {save_err}")
        except Exception as simple_err:
            log_fail(f"Simple detection failed: {simple_err}")
            log_debug(f"Simple detection error details: {traceback.format_exc()}")
        
        # Process the second page through the full pipeline
        log_info("Processing second page through full pipeline...")
        
        try:
            records = process_pdf_page(pdf_path_obj, page_num, config, vendor_map, output_dir)
            log_info(f"Processed {len(records)} receipts")
            
            # Display details of any records found
            for i, record in enumerate(records):
                log_info(f"Receipt {i+1}: Vendor={record.receipt.vendor}, "
                          f"Amount={record.receipt.amount}, Date={record.receipt.date}")
            
            if not records:
                log_warn("No receipts found in the second page")
        except Exception as e:
            log_fail(f"Error processing second page: {e}")
            log_debug(f"Processing error details: {traceback.format_exc()}")
    except Exception as e:
        log_fail(f"Error in test: {e}")
        log_debug(f"Error details: {traceback.format_exc()}")

def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage: python test_second_page.py <pdf_path>")
        return
    
    pdf_path = sys.argv[1]
    
    if not Path(pdf_path).exists():
        print(f"PDF file not found: {pdf_path}")
        return
    
    # Configure logging
    configure_logging()
    
    log_info("=" * 50)
    log_info(f"Testing second page processing for {pdf_path}")
    log_info("=" * 50)
    
    test_processing_second_page(pdf_path)
    
    log_info("=" * 50)
    log_info("Test complete")
    log_info("=" * 50)

if __name__ == "__main__":
    main()
