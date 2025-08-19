#!/usr/bin/env python
"""
Simpler test script to process first page of PDF file and identify issues.
This is specifically for debugging why the first page (summary page) is causing crashes.
"""

import sys
import os
import traceback
from pathlib import Path
import logging
import time

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the necessary modules from receipt_analyzer
from receipt_analyzer.core.config import Config
from receipt_analyzer.core.pdf_io import get_page_images, get_pdf_page_count
from receipt_analyzer.core.detection_opencv import detect_receipts_opencv, pil_to_cv2, cv2_to_pil
from receipt_analyzer.core.detection_simple import detect_receipts_simple
from receipt_analyzer.core.ocr import perform_ocr
from receipt_analyzer.core.processing import process_pdf_page, process_receipt
from receipt_analyzer.core.vendors import load_vendor_map
from receipt_analyzer.core.logging_utils import get_logger, log_info, log_warn, log_fail, log_debug, log_success

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = get_logger()

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

def test_processing_first_page(pdf_path):
    """Test processing the first page of a PDF file."""
    try:
        # Create output directory
        output_dir = Path("./test_output")
        output_dir.mkdir(exist_ok=True)
        
        # Load config
        config = get_test_config()
        
        # Load vendor map
        vendor_map = load_vendor_map()
        
        # Check PDF page count
        pdf_path_obj = Path(pdf_path)
        page_count = get_pdf_page_count(pdf_path_obj)
        log_info(f"PDF has {page_count} pages")
        
        if page_count == 0:
            log_fail(f"No pages found in {pdf_path}")
            return
        
        # Process first page (index 0)
        page_num = 0
        log_info(f"Processing first page of {pdf_path}")
        
        # Step 1: Extract images
        log_info("Extracting images from first page...")
        try:
            images = get_page_images(pdf_path_obj, page_num)
            log_info(f"Extracted {len(images)} images")
            
            if not images:
                log_fail("Failed to extract any images from first page")
                return
                
            # Save extracted images for inspection
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
            
        # Step 2: Test image conversion
        log_info("Testing image format conversion...")
        for i, img in enumerate(images):
            try:
                cv_img = pil_to_cv2(img)
                log_info(f"Successfully converted image {i+1} to OpenCV format, shape: {cv_img.shape}")
                
                pil_img = cv2_to_pil(cv_img)
                log_info(f"Successfully converted image {i+1} back to PIL format, size: {pil_img.size}")
                
                # Save the converted image
                try:
                    img_path = output_dir / f"converted_image_{i+1}.jpg"
                    pil_img.save(img_path, "JPEG")
                    log_info(f"Saved converted image to {img_path}")
                except Exception as save_err:
                    log_fail(f"Failed to save converted image: {save_err}")
            except Exception as conv_err:
                log_fail(f"Image conversion failed for image {i+1}: {conv_err}")
                log_debug(f"Conversion error details: {traceback.format_exc()}")
                
        # Step 3: Test receipt detection methods
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
            
            # Try OCR on the first detected receipt
            if receipts_opencv:
                log_info("Testing OCR on first OpenCV receipt...")
                try:
                    ocr_result = perform_ocr(receipts_opencv[0], config.ocr, str(pdf_path), page_num, 0)
                    
                    if ocr_result:
                        text, metadata = ocr_result
                        log_info(f"OCR extracted {len(text)} characters")
                        
                        # Save OCR text
                        ocr_path = output_dir / "opencv_receipt_ocr.txt"
                        with open(ocr_path, 'w', encoding='utf-8') as f:
                            f.write(text)
                        log_info(f"Saved OCR text to {ocr_path}")
                        
                        # Print a preview
                        preview = text.replace('\n', ' ').strip()[:200]
                        log_info(f"Text preview: {preview}...")
                    else:
                        log_warn("OCR returned no text")
                except Exception as ocr_err:
                    log_fail(f"OCR failed: {ocr_err}")
                    log_debug(f"OCR error details: {traceback.format_exc()}")
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
        
        # Step 4: Test OCR on first extracted image
        log_info("Testing OCR on first extracted image...")
        try:
            ocr_result = perform_ocr(images[0], config.ocr, str(pdf_path), page_num, 0)
            
            if ocr_result:
                text, metadata = ocr_result
                log_info(f"OCR extracted {len(text)} characters")
                
                # Save OCR text
                ocr_path = output_dir / "first_image_ocr.txt"
                with open(ocr_path, 'w', encoding='utf-8') as f:
                    f.write(text)
                log_info(f"Saved OCR text to {ocr_path}")
                
                # Print a preview
                preview = text.replace('\n', ' ').strip()[:200]
                log_info(f"Text preview: {preview}...")
            else:
                log_warn("OCR returned no text")
        except Exception as ocr_err:
            log_fail(f"OCR failed: {ocr_err}")
            log_debug(f"OCR error details: {traceback.format_exc()}")
        
        # Step 5: Process the first page through the full pipeline
        log_info("Processing first page through full pipeline...")
        start_time = time.time()
        
        try:
            records = process_pdf_page(pdf_path_obj, page_num, config, vendor_map, output_dir)
            log_info(f"Processed {len(records)} receipts in {time.time() - start_time:.2f} seconds")
            
            # Display details of any records found
            for i, record in enumerate(records):
                log_info(f"Receipt {i+1}: Vendor={record.receipt.vendor}, "
                          f"Amount={record.receipt.amount}, Date={record.receipt.date}")
            
            if not records:
                log_info("No receipts found (this is expected for a summary page)")
        except Exception as e:
            log_fail(f"Error processing first page: {e}")
            log_debug(f"Processing error details: {traceback.format_exc()}")
    except Exception as e:
        log_fail(f"Error in test: {e}")
        log_debug(f"Error details: {traceback.format_exc()}")

def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage: python test_first_page.py <pdf_path>")
        return
    
    pdf_path = sys.argv[1]
    
    if not Path(pdf_path).exists():
        log_fail(f"PDF file not found: {pdf_path}")
        return
    
    log_info("=" * 50)
    log_info(f"Testing first page processing for {pdf_path}")
    log_info("=" * 50)
    
    test_processing_first_page(pdf_path)
    
    log_info("=" * 50)
    log_info("Test complete")
    log_info("=" * 50)

if __name__ == "__main__":
    main()
