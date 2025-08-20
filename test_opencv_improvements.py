#!/usr/bin/env python3
"""Test the improved OpenCV detection robustness."""

import sys
import os

# Add the project root to the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def test_opencv_improvements():
    """Test the improved OpenCV detection."""
    print("Testing improved OpenCV detection robustness...")
    
    try:
        from receipt_analyzer.core.detection_opencv import check_opencv_available, detect_receipts_opencv
        from receipt_analyzer.core.config import OpenCVConfig
        from receipt_analyzer.core.pdf_io import extract_embedded_images
        from pathlib import Path
        
        if not check_opencv_available():
            print("❌ OpenCV not available")
            return False
        
        print("✅ OpenCV available")
        
        # Test with the sample PDF
        pdf_path = os.path.join(project_root, "sample_receipt.pdf")
        if not os.path.exists(pdf_path):
            print(f"❌ Sample PDF not found at {pdf_path}")
            return False
        
        print(f"✅ Sample PDF found: {pdf_path}")
        
        # Extract images from first page
        print("Extracting images from PDF...")
        images = extract_embedded_images(Path(pdf_path), page_num=0)
        
        if not images:
            print("❌ No images extracted from PDF")
            return False
        
        print(f"✅ Extracted {len(images)} images")
        
        # Test OpenCV detection with new parameters
        config = OpenCVConfig()
        print(f"Using config: min_area={config.min_area_ratio}, max_area={config.max_area_ratio}")
        print(f"              min_aspect={config.min_aspect}, max_aspect={config.max_aspect}")
        
        receipts = detect_receipts_opencv(images, pdf_path, 0, config)
        
        if not receipts:
            print("❌ No receipts detected")
            return False
        
        print(f"✅ Detected {len(receipts)} receipt(s)")
        for i, receipt in enumerate(receipts):
            print(f"   Receipt {i+1}: {receipt.size[0]}x{receipt.size[1]}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_opencv_improvements()
    print(f"\nTest {'PASSED' if success else 'FAILED'}")
    sys.exit(0 if success else 1)
