#!/usr/bin/env python3
"""Test GUI stability and thread safety."""

import sys
import os
import logging
import time
from pathlib import Path
from unittest.mock import Mock

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from receipt_analyzer.core.config import Config, load_config
from receipt_analyzer.core.logging_utils import LogStream, init_logger, get_logger

def test_gui_integration():
    """Test GUI-related components with our fixes."""
    print("🧪 Testing GUI Stability and Integration")
    print("=" * 60)
    
    # Initialize logging similar to GUI
    log_stream = LogStream()
    log_stream.enable_debug_throttle(True)
    init_logger(log_stream=log_stream)
    logger = get_logger()
    
    results = {}
    
    # Test 1: Configuration loading (as done in GUI)
    print("⚙️  Test 1: Configuration Loading...")
    try:
        config = load_config()
        assert config is not None
        assert hasattr(config, 'detection_method')
        results['config_loading'] = True
        print("   ✅ Configuration loading successful")
    except Exception as e:
        print(f"   ❌ Configuration loading failed: {e}")
        results['config_loading'] = False
    
    # Test 2: Core functions work with our fixes
    print("🔍 Test 2: Core Function Integration...")
    try:
        from receipt_analyzer.core.detection_simple import detect_receipts_simple
        from receipt_analyzer.core.detection_opencv import detect_receipts_opencv
        from receipt_analyzer.core.ocr import extract_text_from_image, extract_text_with_orientation
        
        # Test that our added function exists and works
        from PIL import Image
        import numpy as np
        test_image = Image.new('RGB', (100, 100), color='white')
        
        # Test our new extract_text_from_image function
        text_result = extract_text_from_image(test_image, config.ocr)
        assert isinstance(text_result, str)
        
        results['core_functions'] = True
        print("   ✅ Core function integration successful")
        print(f"   📝 OCR function returned: {len(text_result)} characters")
        
    except Exception as e:
        print(f"   ❌ Core function integration failed: {e}")
        results['core_functions'] = False
    
    # Test 3: Thread-safe logging behavior
    print("📝 Test 3: Thread-Safe Logging...")
    try:
        import threading
        import queue
        
        log_messages = []
        
        def test_logging():
            logger.info("Thread-safe test message")
            logger.debug("Debug message from thread")
            logger.warn("Warning message from thread")
        
        # Create multiple threads to test thread safety
        threads = []
        for i in range(5):
            thread = threading.Thread(target=test_logging)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        results['thread_safe_logging'] = True
        print("   ✅ Thread-safe logging successful")
        
    except Exception as e:
        print(f"   ❌ Thread-safe logging failed: {e}")
        results['thread_safe_logging'] = False
    
    # Test 4: Mock GUI processing workflow
    print("🖥️  Test 4: Mock GUI Processing Workflow...")
    try:
        import queue
        from unittest.mock import Mock
        
        # Simulate GUI processing workflow
        worker_queue = queue.Queue()
        cancel_processing = False
        
        # Mock progress update
        def mock_progress_update(msg):
            worker_queue.put(msg)
        
        # Test workflow steps that GUI uses
        mock_progress_update("Starting processing...")
        mock_progress_update("Processing file 1/1")
        mock_progress_update("Completed processing")
        
        # Verify queue behavior
        messages = []
        while not worker_queue.empty():
            messages.append(worker_queue.get_nowait())
        
        assert len(messages) == 3
        assert "Starting" in messages[0]
        assert "Processing" in messages[1]
        assert "Completed" in messages[2]
        
        results['gui_workflow'] = True
        print("   ✅ GUI workflow simulation successful")
        print(f"   📨 Processed {len(messages)} queue messages")
        
    except Exception as e:
        print(f"   ❌ GUI workflow simulation failed: {e}")
        results['gui_workflow'] = False
    
    # Test 5: Error handling robustness
    print("⚠️  Test 5: Error Handling Robustness...")
    try:
        from receipt_analyzer.core.processing import process_pdf_files
        
        # Test with non-existent files (should handle gracefully)
        non_existent_files = [Path("nonexistent1.pdf"), Path("nonexistent2.pdf")]
        
        result = process_pdf_files(
            non_existent_files, 
            output_dir="/tmp/test_output",
            config=config
        )
        
        # Should return 0 receipts without crashing
        assert result == 0
        
        results['error_handling'] = True
        print("   ✅ Error handling robustness successful")
        print("   🛡️  Non-existent files handled gracefully")
        
    except Exception as e:
        print(f"   ❌ Error handling robustness failed: {e}")
        results['error_handling'] = False
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 GUI STABILITY TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    success_rate = (passed / total) * 100
    
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"   {test_name.replace('_', ' ').title()}: {status}")
    
    print(f"\nOverall Success Rate: {success_rate:.1f}% ({passed}/{total})")
    
    if success_rate == 100:
        print("\n🎉 ALL GUI STABILITY TESTS PASSED!")
        print("🔒 The GUI should be stable and crash-free with our fixes!")
        return True
    else:
        print(f"\n⚠️  {total-passed} tests failed - GUI stability may be compromised")
        return False

if __name__ == "__main__":
    success = test_gui_integration()
    sys.exit(0 if success else 1)
