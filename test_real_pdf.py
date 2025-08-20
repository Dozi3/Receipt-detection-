#!/usr/bin/env python
"""
Test script to specifically diagnose issues with the real-world PDF file
1097986001_expense_30712700.pdf using both simple and OpenCV detection methods.
"""

import sys
import os
import traceback
from pathlib import Path
import time
import json

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the necessary modules from receipt_analyzer
from receipt_analyzer.core.config import Config
from receipt_analyzer.core.pdf_io import get_page_images, get_pdf_page_count
from receipt_analyzer.core.detection_opencv import detect_receipts_opencv
from receipt_analyzer.core.detection_simple import detect_receipts_simple
from receipt_analyzer.core.ocr import perform_ocr
from receipt_analyzer.core.processing import process_pdf_page, process_pdf_files, resize_image_for_output
from receipt_analyzer.core.vendors import load_vendor_map
from receipt_analyzer.core.logging_utils import configure_logging, log_info, log_warn, log_fail, log_debug, log_success

def get_test_config(detection_method='opencv'):
    """Create a test configuration with the specified detection method."""
    config = Config()
    # Set detection method
    config.detection_method = detection_method
    # Configure OpenCV settings
    config.opencv = Config()
    config.opencv.min_contour_area = 1000
    config.opencv.max_contour_area = 1000000
    config.opencv.epsilon_factor = 0.02
    config.opencv.area_threshold = 0.8
    config.opencv.canny1 = 50  # Add missing canny1 parameter
    config.opencv.canny2 = 150  # Add missing canny2 parameter
    config.opencv.morph_close = 9  # Add missing morph_close parameter
    config.opencv.quad_epsilon = 0.02  # Add missing quad_epsilon parameter
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

def test_pdf_extraction(pdf_path, output_dir):
    """Test extracting images from all pages of a PDF."""
    log_info(f"Testing PDF extraction for {pdf_path}")
    
    # Get page count
    pdf_path_obj = Path(pdf_path)
    page_count = get_pdf_page_count(pdf_path_obj)
    log_info(f"PDF has {page_count} pages")
    
    all_images = []
    
    # Extract images from each page
    for page_num in range(page_count):
        try:
            log_info(f"Extracting images from page {page_num+1}...")
            images = get_page_images(pdf_path_obj, page_num)
            log_info(f"Extracted {len(images)} images from page {page_num+1}")
            
            # Save the first image from each page for inspection
            if images:
                page_dir = output_dir / f"page_{page_num+1}"
                page_dir.mkdir(exist_ok=True)
                
                for i, img in enumerate(images):
                    try:
                        img_path = page_dir / f"extracted_image_{i+1}.jpg"
                        img.save(img_path, "JPEG")
                        log_info(f"Saved extracted image to {img_path}")
                    except Exception as save_err:
                        log_fail(f"Failed to save extracted image: {save_err}")
                
                all_images.append((page_num, images))
            else:
                log_warn(f"No images extracted from page {page_num+1}")
        except Exception as e:
            log_fail(f"Error extracting images from page {page_num+1}: {e}")
            log_debug(traceback.format_exc())
    
    return all_images

def test_detection_method(pdf_path, images_by_page, detection_method, output_dir):
    """Test a specific detection method on the extracted images."""
    log_info(f"Testing {detection_method} detection method...")
    
    config = get_test_config(detection_method)
    receipts_found = 0
    
    for page_num, images in images_by_page:
        log_info(f"Processing page {page_num+1} with {detection_method} detection...")
        
        try:
            if detection_method == 'opencv':
                receipts = detect_receipts_opencv(images, str(pdf_path), page_num, config.opencv)
            else:
                receipts = detect_receipts_simple(images, str(pdf_path), page_num)
            
            log_info(f"{detection_method} detection found {len(receipts) if receipts else 0} receipts on page {page_num+1}")
            
            # Save detected receipts
            if receipts:
                page_dir = output_dir / f"page_{page_num+1}"
                page_dir.mkdir(exist_ok=True)
                
                for i, receipt in enumerate(receipts):
                    try:
                        img_path = page_dir / f"{detection_method}_receipt_{i+1}.jpg"
                        receipt.save(img_path, "JPEG")
                        log_info(f"Saved {detection_method} receipt to {img_path}")
                        
                        # Also save a resized version for comparison
                        try:
                            resized = resize_image_for_output(receipt, config.output.max_edge)
                            resized_path = page_dir / f"{detection_method}_receipt_{i+1}_resized.jpg"
                            resized.save(resized_path, "JPEG", quality=config.output.jpeg_quality)
                            log_info(f"Saved resized receipt to {resized_path}")
                        except Exception as resize_err:
                            log_fail(f"Failed to resize receipt: {resize_err}")
                    except Exception as save_err:
                        log_fail(f"Failed to save receipt: {save_err}")
                
                receipts_found += len(receipts)
        except Exception as detect_err:
            log_fail(f"Error in {detection_method} detection for page {page_num+1}: {detect_err}")
            log_debug(traceback.format_exc())
    
    return receipts_found

def test_full_processing(pdf_path, output_dir):
    """Test the full processing pipeline with both detection methods."""
    log_info(f"Testing full processing pipeline for {pdf_path}")
    
    results = {}
    
    for detection_method in ['opencv', 'simple']:
        try:
            config = get_test_config(detection_method)
            vendor_map = load_vendor_map()
            
            log_info(f"Processing with {detection_method} detection method...")
            start_time = time.time()
            
            # Create method-specific output directory
            method_output_dir = output_dir / detection_method
            method_output_dir.mkdir(exist_ok=True, parents=True)
            
            # Process all pages
            records = process_pdf_files([Path(pdf_path)], method_output_dir, config, vendor_map)
            
            processing_time = time.time() - start_time
            log_info(f"{detection_method} processing completed in {processing_time:.2f} seconds")
            
            # records is an integer (total number of receipts processed)
            log_info(f"{detection_method} processing returned count: {records}")
            results[detection_method] = {
                'processing_time': processing_time,
                'receipts_found': records,
                'receipts': []
            }
            
            # Save results to JSON
            try:
                results_path = output_dir / f"{detection_method}_results.json"
                with open(results_path, 'w') as f:
                    json.dump(results[detection_method], f, indent=2)
                log_info(f"Saved {detection_method} results to {results_path}")
            except Exception as json_err:
                log_fail(f"Failed to save results to JSON: {json_err}")
            
        except Exception as proc_err:
            log_fail(f"Error in full processing with {detection_method}: {proc_err}")
            log_debug(traceback.format_exc())
            results[detection_method] = {
                'error': str(proc_err),
                'receipts_found': 0
            }
    
    return results

def main():
    """Main function."""
    # Configure logging
    configure_logging()
    
    # Get the PDF path
    pdf_path = "/workspaces/Receipt-detection-/1097986001_expense_30712700.pdf"
    if not Path(pdf_path).exists():
        log_fail(f"PDF file not found: {pdf_path}")
        return 1
    
    # Create a timestamp for output directory
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_dir = Path(f"./pdf_test_output_{timestamp}")
    output_dir.mkdir(exist_ok=True)
    
    log_info("=" * 80)
    log_info(f"Testing PDF processing for {pdf_path}")
    log_info(f"Output directory: {output_dir}")
    log_info("=" * 80)
    
    # Step 1: Extract images from all pages
    log_info("\nSTEP 1: Extracting images from PDF")
    log_info("-" * 50)
    images_by_page = test_pdf_extraction(pdf_path, output_dir)
    
    # Step 2: Test simple detection
    log_info("\nSTEP 2: Testing simple detection")
    log_info("-" * 50)
    simple_receipts = test_detection_method(pdf_path, images_by_page, 'simple', output_dir)
    log_info(f"Simple detection found {simple_receipts} receipts in total")
    
    # Step 3: Test OpenCV detection
    log_info("\nSTEP 3: Testing OpenCV detection")
    log_info("-" * 50)
    opencv_receipts = test_detection_method(pdf_path, images_by_page, 'opencv', output_dir)
    log_info(f"OpenCV detection found {opencv_receipts} receipts in total")
    
    # Step 4: Test full processing with both methods
    log_info("\nSTEP 4: Testing full processing pipeline")
    log_info("-" * 50)
    results = test_full_processing(pdf_path, output_dir)
    
    # Summary
    log_info("\nSUMMARY")
    log_info("=" * 50)
    log_info(f"PDF: {pdf_path}")
    log_info(f"Total pages: {len(images_by_page)}")
    log_info(f"Simple detection: {simple_receipts} receipts found")
    log_info(f"OpenCV detection: {opencv_receipts} receipts found")
    
    if 'simple' in results and 'opencv' in results:
        log_info(f"Full processing with simple: {results['simple'].get('receipts_found', 0)} receipts")
        log_info(f"Full processing with OpenCV: {results['opencv'].get('receipts_found', 0)} receipts")
        
        if 'processing_time' in results['simple'] and 'processing_time' in results['opencv']:
            log_info(f"Simple processing time: {results['simple']['processing_time']:.2f} seconds")
            log_info(f"OpenCV processing time: {results['opencv']['processing_time']:.2f} seconds")
    
    log_info("=" * 80)
    log_info("Test complete")
    log_info("=" * 80)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
