#!/usr/bin/env python3
"""
Script to test the threading aspects of the application
"""

import sys
import traceback
import threading
import time
from pathlib import Path
import signal

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

from receipt_analyzer.core.config import load_config
from receipt_analyzer.core.vendors import load_vendor_map
from receipt_analyzer.core.logging_utils import init_logger, get_logger, LogStream

# Set up a global cancel flag for signal handling
cancel_processing = False

def signal_handler(sig, frame):
    """Handle Ctrl+C to cancel processing"""
    global cancel_processing
    print("\nCancelling processing...")
    cancel_processing = True

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

def simulate_gui_processing():
    """Simulate the GUI processing workflow with threading"""
    logger = get_logger()
    
    try:
        # Load config and vendor map
        config = load_config()
        vendor_map = load_vendor_map()
        
        # Find a sample PDF to process
        sample_pdf = Path(__file__).parent / "sample_receipt.pdf"
        if not sample_pdf.exists():
            sample_pdf = Path(__file__).parent / "input_receipts" / "sample_receipt.pdf"
        
        if not sample_pdf.exists():
            logger.fail("Could not find a sample PDF to process")
            return False
        
        # Create output directory
        output_dir = Path(__file__).parent / "test_threading_output"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Testing processing of {sample_pdf}")
        logger.info(f"Output will be saved to {output_dir}")
        
        # Count PDF files for progress tracking
        total_count = 1
        progress_count = 0
        
        # Create the processing thread
        processing_thread = threading.Thread(
            target=process_files_thread,
            args=(sample_pdf, output_dir, config, vendor_map),
            daemon=True
        )
        
        # Start the thread
        logger.info("Starting processing thread")
        processing_thread.start()
        
        # Monitor the thread and simulate GUI updates
        while processing_thread.is_alive():
            # Check for cancellation
            if cancel_processing:
                logger.info("Cancellation detected, waiting for thread to complete")
                break
                
            # Simulate other GUI operations by doing periodic updates
            logger.debug("Main thread: Simulating GUI update")
            time.sleep(0.1)
        
        # Wait for the thread to complete
        logger.info("Waiting for processing thread to complete")
        processing_thread.join(timeout=10)
        
        if processing_thread.is_alive():
            logger.warn("Processing thread did not complete within timeout")
            return False
        
        logger.info("Processing thread completed")
        return True
    
    except Exception as e:
        logger.fail(f"Error in GUI simulation: {e}")
        logger.debug(f"Error details: {traceback.format_exc()}")
        return False

def process_files_thread(pdf_path, output_dir, config, vendor_map):
    """Process files in a thread to simulate GUI background processing"""
    logger = get_logger()
    
    try:
        logger.info(f"Thread: Processing {pdf_path.name}")
        
        # Import processing module
        from receipt_analyzer.core.processing import process_pdf_files
        
        # Process the PDF
        receipt_count = process_pdf_files([pdf_path], output_dir, config, vendor_map)
        
        logger.info(f"Thread: Processed {receipt_count} receipts")
        return receipt_count
    except Exception as e:
        logger.fail(f"Thread: Error processing {pdf_path.name}: {e}")
        logger.debug(f"Thread: Error details: {traceback.format_exc()}")
        return 0

def main():
    """Run the threading test"""
    # Set up signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    
    logger = setup_logging()
    
    logger.info("Starting GUI threading simulation test")
    
    if simulate_gui_processing():
        logger.info("Threading test completed successfully")
        return 0
    else:
        logger.fail("Threading test failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
