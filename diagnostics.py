#!/usr/bin/env python
"""
Diagnostics script to identify PDF processing issues in Receipt Analyzer.
This focuses on tracing the exact failure point when processing PDFs.
"""

import sys
import os
import traceback
import argparse
from pathlib import Path
import logging
from datetime import datetime
from PIL import Image
import fitz  # PyMuPDF

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the necessary modules from receipt_analyzer
from receipt_analyzer.core.config import Config
from receipt_analyzer.core.pdf_io import extract_embedded_images, rasterize_page_pymupdf, rasterize_page_pdf2image, get_page_images
from receipt_analyzer.core.detection_opencv import detect_receipts_opencv, pil_to_cv2, cv2_to_pil, check_opencv_available
from receipt_analyzer.core.detection_simple import detect_receipts_simple
from receipt_analyzer.core.ocr import perform_ocr, check_tesseract_available
from receipt_analyzer.core.processing import process_pdf_page, process_receipt, save_image
from receipt_analyzer.core.vendors import load_vendor_map
from receipt_analyzer.core.logging_utils import get_logger, configure_logging, log_info, log_debug, log_warn, log_fail, log_success

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="PDF Receipt Analyzer Diagnostics")
    parser.add_argument("pdf_file", help="Path to the PDF file to analyze")
    parser.add_argument("--page", type=int, help="Process only this page number (1-based)")
    parser.add_argument("--detection", choices=["opencv", "simple"], 
                        default="opencv", help="Detection method to use")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--quiet", action="store_true", help="Show only warnings and errors")
    parser.add_argument("--save-images", action="store_true", 
                        help="Save intermediate images for debugging")
    return parser.parse_args()

def get_config(args):
    """Create a configuration object from command line arguments."""
    config = Config()
    # Set detection method
    config.detection_method = args.detection
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

def test_pdf_extraction(pdf_path, page_num=0, output_dir=None, save_images=False):
    """Test extracting images from a PDF page."""
    log_info(f"Testing PDF extraction for {pdf_path}, page {page_num+1}")
    
    try:
        # Test embedded image extraction
        log_info("Testing embedded image extraction...")
        images = extract_embedded_images(Path(pdf_path), page_num)
        log_info(f"Extracted {len(images)} embedded images")
        
        for i, img in enumerate(images):
            log_info(f"Image {i+1}: {img.size[0]}x{img.size[1]}, mode: {img.mode}")
            
            if save_images and output_dir:
                try:
                    img_path = output_dir / f"page_{page_num+1}_embedded_{i+1}.jpg"
                    img.save(img_path, "JPEG")
                    log_info(f"Saved embedded image to {img_path}")
                except Exception as save_err:
                    log_fail(f"Failed to save embedded image: {save_err}")
            
        # If no embedded images, test PyMuPDF rasterization
        if not images:
            log_info("Testing PyMuPDF rasterization...")
            img = rasterize_page_pymupdf(Path(pdf_path), page_num)
            if img:
                log_info(f"PyMuPDF rasterization succeeded: {img.size[0]}x{img.size[1]}, mode: {img.mode}")
                
                if save_images and output_dir:
                    try:
                        img_path = output_dir / f"page_{page_num+1}_rasterized_pymupdf.jpg"
                        img.save(img_path, "JPEG")
                        log_info(f"Saved rasterized image to {img_path}")
                    except Exception as save_err:
                        log_fail(f"Failed to save rasterized image: {save_err}")
                
                images = [img]
            else:
                log_warn("PyMuPDF rasterization failed")
                
                # Test pdf2image rasterization
                log_info("Testing pdf2image rasterization...")
                img = rasterize_page_pdf2image(Path(pdf_path), page_num)
                if img:
                    log_info(f"pdf2image rasterization succeeded: {img.size[0]}x{img.size[1]}, mode: {img.mode}")
                    
                    if save_images and output_dir:
                        try:
                            img_path = output_dir / f"page_{page_num+1}_rasterized_pdf2image.jpg"
                            img.save(img_path, "JPEG")
                            log_info(f"Saved rasterized image to {img_path}")
                        except Exception as save_err:
                            log_fail(f"Failed to save rasterized image: {save_err}")
                    
                    images = [img]
                else:
                    log_fail("pdf2image rasterization failed")
        
        # Test complete get_page_images function
        log_info("Testing get_page_images function...")
        all_images = get_page_images(Path(pdf_path), page_num)
        log_info(f"get_page_images returned {len(all_images)} images")
        
        if save_images and output_dir:
            for i, img in enumerate(all_images):
                try:
                    img_path = output_dir / f"page_{page_num+1}_final_{i+1}.jpg"
                    img.save(img_path, "JPEG")
                    log_info(f"Saved final extracted image to {img_path}")
                except Exception as save_err:
                    log_fail(f"Failed to save final image: {save_err}")
        
        return all_images
    except Exception as e:
        log_fail(f"Error in PDF extraction: {e}")
        log_debug(f"Extraction error details: {traceback.format_exc()}")
        return []

def test_receipt_detection(images, pdf_path, page_num=0, config=None, output_dir=None, save_images=False):
    """Test receipt detection on images."""
    log_info("Testing receipt detection...")
    
    if not images:
        log_fail("No images to detect receipts from")
        return []
    
    try:
        # Create a default config if none provided
        if config is None:
            config = Config()
            config.opencv = Config()
            config.opencv.min_contour_area = 1000
            config.opencv.max_contour_area = 1000000
            config.opencv.epsilon_factor = 0.02
            config.opencv.area_threshold = 0.8
        
        # Test conversion to OpenCV format
        log_info("Testing image conversion to OpenCV format...")
        for i, img in enumerate(images):
            try:
                cv_img = pil_to_cv2(img)
                log_info(f"Successfully converted image {i+1} to OpenCV format, shape: {cv_img.shape}")
                
                # Test conversion back to PIL
                pil_img = cv2_to_pil(cv_img)
                log_info(f"Successfully converted image {i+1} back to PIL format, size: {pil_img.size}")
                
                if save_images and output_dir:
                    try:
                        img_path = output_dir / f"page_{page_num+1}_cv_converted_{i+1}.jpg"
                        pil_img.save(img_path, "JPEG")
                        log_info(f"Saved converted image to {img_path}")
                    except Exception as save_err:
                        log_fail(f"Failed to save converted image: {save_err}")
                
            except Exception as conv_err:
                log_fail(f"Image conversion failed for image {i+1}: {conv_err}")
                log_debug(f"Conversion error details: {traceback.format_exc()}")
        
        receipts = []
        detection_method = getattr(config, 'detection_method', 'opencv')
        
        # Test OpenCV detection
        if detection_method == 'opencv':
            log_info("Using OpenCV detection...")
            receipts = detect_receipts_opencv(images, str(pdf_path), page_num, config.opencv)
        else:
            # Use simple detection
            log_info("Using simple detection...")
            receipts = detect_receipts_simple(images, str(pdf_path), page_num)
        
        log_info(f"{detection_method} detection found {len(receipts)} receipts")
        
        if save_images and output_dir and receipts:
            # Save the detected receipts
            for i, receipt in enumerate(receipts):
                try:
                    img_path = output_dir / f"page_{page_num+1}_receipt_{i+1}.jpg"
                    receipt.save(img_path, "JPEG")
                    log_info(f"Saved receipt image to {img_path}")
                except Exception as save_err:
                    log_fail(f"Failed to save receipt image: {save_err}")
        
        return receipts
    except Exception as e:
        log_fail(f"Error in receipt detection: {e}")
        log_debug(f"Detection error details: {traceback.format_exc()}")
        return []

def test_ocr(receipt_images, pdf_path, page_num=0, config=None, output_dir=None):
    """Test OCR on receipt images."""
    if not receipt_images:
        log_warn("No receipt images to perform OCR on")
        return []
    
    if config is None:
        config = Config()
        config.ocr = Config()
        config.ocr.lang = 'eng'
        config.ocr.config = '--psm 4'
    
    results = []
    
    for i, receipt in enumerate(receipt_images):
        try:
            logger.info(f"OCR on receipt {i+1}...")
            text, metadata = perform_ocr(receipt, config.ocr, str(pdf_path), page_num, i, auto_orient=True)
            
            if not text:
                logger.warning(f"No text extracted from receipt {i+1}")
                continue
            
            logger.info(f"Successfully extracted {len(text)} characters from receipt {i+1}")
            
            # Save the OCR text
            if output_dir:
                text_path = output_dir / f"page_{page_num+1}_receipt_{i+1}_ocr.txt"
                with open(text_path, 'w', encoding='utf-8') as f:
                    f.write(text)
                logger.info(f"Saved OCR text to {text_path}")
            
            # Print a preview of the text
            preview = text.replace('\n', ' ').strip()[:200]
            logger.info(f"Text preview: {preview}...")
            
            results.append((text, metadata))
            
        except Exception as e:
            logger.error(f"OCR failed for receipt {i+1}: {e}")
            logger.debug(f"OCR error details: {traceback.format_exc()}")
    
    return results

def test_full_processing(pdf_path, page_num=0, config=None, output_dir=None):
    """Test the full processing pipeline on a PDF page."""
    logger = get_logger()
    logger.info(f"Testing full processing pipeline for {pdf_path}, page {page_num+1}")
    
    try:
        # Create a default config if none provided
        if config is None:
            config = Config()
            config.output = Config()
            config.output.format = 'jpg'
        
        # Load vendor map
        vendor_map = load_vendor_map()
        
        # Create a temporary output directory if none provided
        if output_dir is None:
            output_dir = Path("./diagnostic_output")
            output_dir.mkdir(exist_ok=True)
        
        # Process the PDF page
        logger.info("Running process_pdf_page...")
        records = process_pdf_page(Path(pdf_path), page_num, config, vendor_map, output_dir)
        
        logger.info(f"Processed {len(records)} receipts")
        
        # Print details of each record
        for i, record in enumerate(records):
            logger.info(f"Receipt {i+1}: Vendor={record.receipt.vendor}, "
                      f"Amount={record.receipt.amount}, Date={record.receipt.date}")
        
        return records
    except Exception as e:
        logger.error(f"Error in full processing: {e}")
        logger.debug(f"Processing error details: {traceback.format_exc()}")
        return []

def inspect_pdf_structure(pdf_path):
    """Inspect the structure of a PDF file."""
    logger = get_logger()
    logger.info(f"Inspecting PDF structure for {pdf_path}")
    
    try:
        doc = fitz.open(pdf_path)
        logger.info(f"PDF has {len(doc)} pages")
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            logger.info(f"Page {page_num+1}: {page.rect.width}x{page.rect.height} points")
            
            # Get page rotation
            logger.info(f"Page rotation: {page.rotation}")
            
            # Check for images
            image_list = page.get_images()
            logger.info(f"Page has {len(image_list)} embedded images")
            
            # Check for text
            text = page.get_text()
            text_preview = text[:100] + "..." if len(text) > 100 else text
            logger.info(f"Page text preview: {text_preview}")
            
        doc.close()
    except Exception as e:
        logger.error(f"Error inspecting PDF: {e}")
        logger.debug(f"Inspection error details: {traceback.format_exc()}")

def check_dependencies():
    """Check if all required dependencies are available."""
    from receipt_analyzer.core.logging_utils import log_info, log_fail
    
    all_ok = True
    
    # Check Tesseract
    tesseract_ok, tesseract_msg = check_tesseract_available()
    if not tesseract_ok:
        log_fail(f"Tesseract issue: {tesseract_msg}")
        all_ok = False
    else:
        log_info("✓ Tesseract OCR is available")
    
    # Check OpenCV
    if check_opencv_available():
        log_info("✓ OpenCV is available")
    else:
        log_fail("OpenCV is not available")
        all_ok = False
    
    return all_ok

def main():
    """Main function to run the diagnostics."""
    args = parse_args()
    
    # Configure logging based on arguments
    log_level = logging.DEBUG if args.debug else (logging.WARNING if args.quiet else logging.INFO)
    configure_logging(level=log_level)
    logger = get_logger()
    
    # Create timestamp for output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(f"diagnostic_output_{timestamp}")
    output_dir.mkdir(exist_ok=True)
    
    logger.info("=" * 50)
    logger.info(f"Running diagnostics on {args.pdf_file}")
    logger.info(f"Output directory: {output_dir}")
    logger.info("=" * 50)
    
    # Check that PDF exists
    pdf_path = args.pdf_file
    if not Path(pdf_path).exists():
        logger.error(f"PDF file not found: {pdf_path}")
        return 1
    
    # Check dependencies
    check_dependencies()
    
    # Get config
    config = get_config(args)
    
    # Inspect PDF structure
    inspect_pdf_structure(pdf_path)
    
    # Determine pages to process
    try:
        doc = fitz.open(pdf_path)
        page_count = len(doc)
        doc.close()
        
        if args.page:
            if 1 <= args.page <= page_count:
                pages = [args.page - 1]  # Convert to 0-based
            else:
                logger.error(f"Invalid page number {args.page}, PDF has {page_count} pages")
                return 1
        else:
            pages = range(page_count)
    except Exception as e:
        logger.error(f"Error determining page count: {e}")
        logger.debug(f"Page count error details: {traceback.format_exc()}")
        # Default to just first page if can't determine
        pages = [0]
    
    # Process each page
    for page_num in pages:
        logger.info("\n" + "=" * 50)
        logger.info(f"Processing page {page_num+1}")
        logger.info("=" * 50)
        
        # Extract images
        images = test_pdf_extraction(pdf_path, page_num, output_dir, args.save_images)
        
        # Detect receipts
        if images:
            receipts = test_receipt_detection(images, pdf_path, page_num, config, output_dir, args.save_images)
            
            # Perform OCR on receipts
            if receipts:
                test_ocr(receipts, pdf_path, page_num, config, output_dir)
        
        # Test full processing pipeline
        test_full_processing(pdf_path, page_num, config, output_dir)
    
    logger.info("\n" + "=" * 50)
    logger.info("Diagnostics complete")
    logger.info(f"Results saved to {output_dir}")
    logger.info("=" * 50)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
