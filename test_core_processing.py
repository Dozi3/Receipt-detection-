#!/usr/bin/env python3
"""Test script to isolate the processing hang issue."""

import sys
import os
from pathlib import Path
import traceback

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_core_processing_only():
    """Test the core processing without GUI."""
    print("🔍 Testing Core Processing Pipeline")
    print("=" * 50)
    
    try:
        from receipt_analyzer.core.config import load_config
        from receipt_analyzer.core.pdf_io import find_pdf_files
        from receipt_analyzer.core.processing import process_pdf_files
        from receipt_analyzer.core.logging_utils import init_logger
        
        # Initialize logging
        init_logger()
        print("✅ Core modules imported successfully")
        
        # Test with the sample PDF
        test_pdf = Path("1097986001_expense_30712700.pdf")
        if not test_pdf.exists():
            test_pdf = Path("sample_receipt.pdf") 
            
        if not test_pdf.exists():
            print("❌ No test PDF found")
            return False
            
        print(f"📄 Testing with: {test_pdf.name}")
        
        # Load config
        config = load_config()
        print("✅ Config loaded")
        
        # Find PDF files
        pdf_files = [test_pdf]
        print(f"✅ PDF file list: {[str(p) for p in pdf_files]}")
        
        # Create output directory
        output_dir = Path("test_processing_isolated")
        output_dir.mkdir(exist_ok=True)
        print(f"✅ Output directory: {output_dir}")
        
        print("\n🚀 Starting processing (this is where it might hang)...")
        print("If this hangs, the issue is in the core processing, not GUI threading.")
        
        # Process with timeout simulation
        import signal
        
        class TimeoutException(Exception):
            pass
        
        def timeout_handler(signum, frame):
            raise TimeoutException("Processing timed out after 60 seconds")
            
        # Set timeout for 60 seconds (only on Unix systems)
        if hasattr(signal, 'SIGALRM'):
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(60)
        
        try:
            result = process_pdf_files(pdf_files, output_dir, config)
            
            if hasattr(signal, 'SIGALRM'):
                signal.alarm(0)  # Cancel timeout
                
            print(f"✅ Processing completed! Result: {result} receipts")
            return True
            
        except TimeoutException:
            print("❌ Processing timed out - there's likely a hang in the core processing")
            return False
            
    except Exception as e:
        tb = traceback.format_exc()
        print(f"❌ Processing failed with exception: {e}")
        print(f"Traceback:\n{tb}")
        return False

def test_pdf_io_only():
    """Test just the PDF I/O operations."""
    print("\n🔍 Testing PDF I/O Operations")
    print("=" * 50)
    
    try:
        from receipt_analyzer.core.pdf_io import find_pdf_files, get_pdf_page_count, get_page_images
        
        # Test finding files
        test_pdf = Path("1097986001_expense_30712700.pdf")
        if not test_pdf.exists():
            test_pdf = Path("sample_receipt.pdf")
            
        if not test_pdf.exists():
            print("❌ No test PDF found")
            return False
            
        print(f"📄 Testing PDF I/O with: {test_pdf.name}")
        
        # Test page count
        page_count = get_pdf_page_count(test_pdf)
        print(f"✅ Page count: {page_count}")
        
        # Test getting images from first page
        print("🖼️  Testing image extraction from page 1...")
        images = get_page_images(test_pdf, 1)
        print(f"✅ Extracted {len(images)} images from page 1")
        
        return True
        
    except Exception as e:
        tb = traceback.format_exc()
        print(f"❌ PDF I/O test failed: {e}")
        print(f"Traceback:\n{tb}")
        return False

if __name__ == "__main__":
    print("🔧 RECEIPT ANALYZER - CORE PROCESSING TEST")
    print("=" * 60)
    print("This test runs the processing pipeline without GUI to isolate hang issues.")
    print()
    
    # Test PDF I/O first
    io_success = test_pdf_io_only()
    
    if io_success:
        # Test full processing
        processing_success = test_core_processing_only()
        
        print("\n" + "=" * 60)
        print("📊 TEST RESULTS")
        print("=" * 60)
        
        if processing_success:
            print("✅ CORE PROCESSING WORKS!")
            print("🎯 The hang is likely a GUI threading issue, not core processing.")
            print("💡 The GUI fixes should resolve the problem.")
        else:
            print("❌ CORE PROCESSING HANGS!")
            print("🎯 The issue is in the core processing pipeline, not GUI threading.")
            print("💡 Need to investigate PDF processing, OCR, or OpenCV components.")
    else:
        print("\n❌ PDF I/O operations failed - check PDF file accessibility.")
