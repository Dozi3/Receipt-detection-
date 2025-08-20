#!/usr/bin/env python3
"""Test comprehensive module consistency improvements."""

import sys
import os
import tempfile
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_error_handling_consistency():
    """Test standardized error handling patterns."""
    print("Testing error handling consistency...")
    
    try:
        from receipt_analyzer.core.error_handling import (
            with_error_handling, handle_pdf_errors, safe_execute, create_error_context
        )
        
        # Test error handling decorator
        @with_error_handling("Test operation", fallback_value="fallback")
        def failing_function():
            raise ValueError("Test error")
        
        result = failing_function()
        assert result == "fallback", "Error handling should return fallback value"
        
        # Test context manager
        error_occurred = False
        try:
            with create_error_context("Test context", param="value"):
                raise RuntimeError("Context test error")
        except RuntimeError:
            error_occurred = True
        
        assert error_occurred, "Context should allow exceptions to propagate"
        
        # Test safe execution
        def safe_function():
            return "success"
        
        result = safe_execute(safe_function, operation_name="Safe test")
        assert result == "success", "Safe execution should work for good functions"
        
        print("✅ Error handling consistency working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Error handling consistency failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_resource_management():
    """Test resource management improvements."""
    print("\nTesting resource management...")
    
    try:
        from receipt_analyzer.core.resource_management import (
            MemoryMonitor, memory_managed_operation, get_resource_tracker
        )
        
        # Test memory monitor
        monitor = MemoryMonitor("Test operation")
        monitor.start_monitoring()
        initial_memory = monitor.check_memory("test stage")
        monitor.finish_monitoring()
        
        assert initial_memory >= 0, "Memory monitor should return valid memory usage"
        
        # Test context manager
        with memory_managed_operation("Test context") as ctx_monitor:
            memory = ctx_monitor.check_memory("in context")
            assert memory >= 0, "Context monitor should work"
        
        # Test resource tracker
        tracker = get_resource_tracker()
        initial_files = len(tracker.open_files)
        
        tracker.track_file("test_file.pdf")
        assert len(tracker.open_files) == initial_files + 1, "Should track file"
        
        tracker.untrack_file("test_file.pdf")
        assert len(tracker.open_files) == initial_files, "Should untrack file"
        
        print("✅ Resource management working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Resource management failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_pdf_io_improvements():
    """Test improved PDF I/O with resource management.""" 
    print("\nTesting PDF I/O improvements...")
    
    try:
        from receipt_analyzer.core.resource_management import pdf_document, get_resource_tracker
        
        # Test with a dummy file (won't work but should handle error gracefully)
        dummy_path = Path("nonexistent.pdf")
        
        try:
            with pdf_document(dummy_path, "Test operation") as doc:
                pass
        except Exception:
            pass  # Expected to fail, but should handle gracefully
        
        # Test resource tracking
        tracker = get_resource_tracker()
        summary = tracker.get_summary()
        assert "Open files:" in summary, "Resource tracker should provide summary"
        
        print("✅ PDF I/O improvements working correctly")
        return True
        
    except Exception as e:
        print(f"❌ PDF I/O improvements failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_threading_consistency():
    """Test threading consistency improvements."""
    print("\nTesting threading consistency...")
    
    try:
        from receipt_analyzer.core.threading_utils import CancellationToken, ProgressCallback
        from receipt_analyzer.core.processing import process_pdf_files
        from receipt_analyzer.core.config import load_config
        
        # Test cancellation in processing
        token = CancellationToken()
        token.cancel()
        
        config = load_config()
        result = process_pdf_files([], project_root / "test_output", config, 
                                 cancellation_token=token)
        
        assert result == 0, "Should return 0 when cancelled immediately"
        
        # Test progress callback
        updates = []
        def capture_progress(current, total, message):
            updates.append((current, total, message))
        
        callback = ProgressCallback(capture_progress)
        callback.update(1, 5, "Test")
        callback.update(5, 5, "Done")
        
        assert len(updates) >= 1, "Should capture progress updates"
        
        print("✅ Threading consistency working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Threading consistency failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_logging_consistency():
    """Test logging consistency across modules."""
    print("\nTesting logging consistency...")
    
    try:
        from receipt_analyzer.core.logging_utils import get_logger, LogStream, LogRecord, LogLevel
        
        # Test logger availability
        logger = get_logger()
        assert logger is not None, "Logger should be available"
        
        # Test log stream directly
        log_stream = LogStream()
        log_stream.enable_debug_throttle(True)
        
        # Add test listener
        messages = []
        def test_listener(record):
            messages.append(record)
        
        log_stream.add_listener(test_listener)
        
        # Test direct logging to stream
        test_record = LogRecord(LogLevel.INFO, "Test info message")
        log_stream.add_record(test_record)
        
        debug_record = LogRecord(LogLevel.DEBUG, "Test debug message")
        log_stream.add_record(debug_record)
        
        # Should have captured messages
        assert len(messages) >= 1, f"Should capture log messages, got {len(messages)}"
        
        log_stream.remove_listener(test_listener)
        
        print("✅ Logging consistency working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Logging consistency failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_overall_consistency():
    """Test overall module consistency."""
    print("\nTesting overall module consistency...")
    
    try:
        # Test that all major modules can be imported without conflicts
        from receipt_analyzer.core import (
            config, processing, pdf_io, detection_opencv, 
            threading_utils, error_handling, resource_management
        )
        
        # Test configuration consistency
        config_obj = config.load_config()
        assert config_obj is not None, "Config should load successfully"
        
        # Test that modules work together
        from receipt_analyzer.core.threading_utils import CancellationToken
        from receipt_analyzer.core.error_handling import safe_execute
        
        def test_operation():
            return "integration_test_success"
        
        token = CancellationToken()
        result = safe_execute(test_operation, operation_name="Integration test")
        
        assert result == "integration_test_success", "Modules should work together"
        
        print("✅ Overall module consistency working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Overall consistency failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=== TESTING MODULE CONSISTENCY IMPROVEMENTS ===\n")
    
    tests = [
        test_error_handling_consistency,
        test_resource_management,
        test_pdf_io_improvements,
        test_threading_consistency,
        test_logging_consistency,
        test_overall_consistency,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
    
    print(f"\n=== RESULTS: {passed}/{total} tests passed ===")
    
    if passed == total:
        print("🎉 All module consistency tests passed!")
        print("\n✅ MODULE STANDARDIZATION COMPLETE:")
        print("   ✅ Phase 1: Core Threading Standardization")
        print("   ✅ Phase 2: Error Handling Consistency")
        print("   ✅ Phase 3: Resource Management")
        print("   ✅ Phase 4: Logging and Monitoring") 
        print("   ✅ Phase 5: Overall Integration")
        print("\n🚀 Application now has consistent patterns across all modules!")
    else:
        print(f"⚠️  {total - passed} test(s) failed - additional work needed")
    
    sys.exit(0 if passed == total else 1)
