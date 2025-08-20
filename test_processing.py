#!/usr/bin/env python3
"""
Script to test the processing functionality without requiring the GUI
"""

import sys
import traceback
from pathlib import Path
import threading
import time

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

from receipt_analyzer.core.config import load_config
from receipt_analyzer.core.vendors import load_vendor_map
from receipt_analyzer.core.logging_utils import init_logger, get_logger, LogStream

def setup_logging():
    """Set up logging for the test"""
    log_stream = LogStream()
    init_logger(log_stream=log_stream)
    logger = get_logger()
    
    # Add a listener to print logs to console
    def log_listener(log_record):
        print(f"{log_record.timestamp} [{log_record.level}] {log_record.message}")
    
    log_stream.add_listener(log_listener)
    return logger

def test_processing(input_pdf, output_dir):
    """Test the processing functionality"""
    logger = get_logger()
    
    try:
        # Import processing module
        from receipt_analyzer.core.processing import process_pdf_files
        
        # Load config and vendor map
        config = load_config()
        vendor_map = load_vendor_map()
        
        # Ensure input and output paths are Paths
        input_path = Path(input_pdf)
        output_path = Path(output_dir)
        
        # Ensure output directory exists
        output_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Processing {input_path.name}")
        
        # Start processing in a thread to mimic the GUI behavior
        processing_thread = threading.Thread(
            target=process_pdf_with_exception_handling,
            args=(input_path, output_path, config, vendor_map),
            daemon=True
        )
        processing_thread.start()
        
        # Wait for processing to complete
        while processing_thread.is_alive():
            time.sleep(0.1)
            
        logger.info("Processing completed")
        return True
    
    except Exception as e:
        logger.fail(f"Processing failed: {e}")
        logger.debug(f"Error details: {traceback.format_exc()}")
        return False

def process_pdf_with_exception_handling(pdf_path, output_path, config, vendor_map):
    """Process a PDF file with exception handling"""
    logger = get_logger()
    
    try:
        from receipt_analyzer.core.processing import process_pdf_files
        receipt_count = process_pdf_files([pdf_path], output_path, config, vendor_map)
        logger.info(f"Processed {receipt_count} receipts")
    except Exception as e:
        logger.fail(f"Error processing {pdf_path.name}: {e}")
        logger.debug(f"Error details: {traceback.format_exc()}")

def main():
    """Run the processing test"""
    logger = setup_logging()
    
    # Find a sample PDF to process
    sample_pdf = Path(__file__).parent / "sample_receipt.pdf"
    if not sample_pdf.exists():
        sample_pdf = Path(__file__).parent / "input_receipts" / "sample_receipt.pdf"
    
    if not sample_pdf.exists():
        logger.fail("Could not find a sample PDF to process")
        return 1
    
    # Create output directory
    output_dir = Path(__file__).parent / "test_processing_output"
    
    logger.info(f"Testing processing of {sample_pdf}")
    logger.info(f"Output will be saved to {output_dir}")
    
    if test_processing(sample_pdf, output_dir):
        logger.info("Processing test completed successfully")
        return 0
    else:
        logger.fail("Processing test failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
