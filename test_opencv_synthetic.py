#!/usr/bin/env python3
"""Test OpenCV detection improvements with synthetic data."""

import sys
import os
import numpy as np
from PIL import Image

# Add the project root to the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def create_test_receipt_image():
    """Create a synthetic receipt image for testing."""
    # Create a 600x800 white background
    img = np.ones((800, 600, 3), dtype=np.uint8) * 255
    
    # Add a dark border (receipt outline)
    img[50:750, 100:500] = [200, 200, 200]  # Gray background
    img[60:740, 110:490] = [255, 255, 255]  # White interior
    
    # Add some dark lines (receipt text simulation)
    for i in range(80, 700, 40):
        img[i:i+3, 120:480] = [0, 0, 0]  # Black horizontal lines
    
    # Add vertical edges
    img[60:740, 110:113] = [0, 0, 0]  # Left edge
    img[60:740, 487:490] = [0, 0, 0]  # Right edge
    img[60:63, 110:490] = [0, 0, 0]   # Top edge
    img[737:740, 110:490] = [0, 0, 0] # Bottom edge
    
    return Image.fromarray(img)

def test_opencv_detection_improvements():
    """Test the improved OpenCV detection with synthetic data."""
    print("Testing improved OpenCV detection with synthetic receipt...")
    
    try:
        from receipt_analyzer.core.detection_opencv import check_opencv_available, detect_receipts_opencv
        from receipt_analyzer.core.config import OpenCVConfig
        
        if not check_opencv_available():
            print("❌ OpenCV not available")
            return False
        
        print("✅ OpenCV available")
        
        # Create test image
        test_image = create_test_receipt_image()
        print(f"✅ Created test image: {test_image.size[0]}x{test_image.size[1]}")
        
        # Test with default config
        config = OpenCVConfig()
        print(f"Using default config:")
        print(f"  min_area_ratio: {config.min_area_ratio}")
        print(f"  max_area_ratio: {config.max_area_ratio}")
        print(f"  min_aspect: {config.min_aspect}")
        print(f"  max_aspect: {config.max_aspect}")
        
        receipts = detect_receipts_opencv([test_image], "test_synthetic.pdf", 0, config)
        
        if not receipts:
            print("❌ No receipts detected from synthetic image")
            return False
        
        print(f"✅ Detected {len(receipts)} receipt(s) from synthetic image")
        for i, receipt in enumerate(receipts):
            print(f"   Receipt {i+1}: {receipt.size[0]}x{receipt.size[1]}")
        
        # Test with very restrictive config to ensure fallback works
        print("\nTesting with restrictive config (should fallback to whole page)...")
        restrictive_config = OpenCVConfig()
        restrictive_config.min_area_ratio = 0.9  # Very high minimum
        restrictive_config.max_area_ratio = 1.0  # Very high maximum
        
        receipts2 = detect_receipts_opencv([test_image], "test_synthetic_restrictive.pdf", 0, restrictive_config)
        
        if not receipts2:
            print("❌ No receipts detected with restrictive config")
            return False
        
        print(f"✅ Fallback working: detected {len(receipts2)} receipt(s)")
        
        # Test error handling with invalid image
        print("\nTesting error handling with None image...")
        try:
            receipts3 = detect_receipts_opencv([], "test_empty.pdf", 0, config)
            if len(receipts3) == 0:
                print("✅ Empty image list handled correctly")
            else:
                print("❌ Empty image list should return empty results")
                return False
        except Exception as e:
            print(f"❌ Error handling failed: {e}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_opencv_detection_improvements()
    print(f"\nOpenCV improvements test {'PASSED' if success else 'FAILED'}")
    sys.exit(0 if success else 1)
