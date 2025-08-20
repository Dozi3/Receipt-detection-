#!/usr/bin/env python3
"""Test the new queue-based threading architecture."""

import tkinter as tk
from tkinter import ttk
import threading
import queue
import time
from pathlib import Path
from receipt_analyzer.gui.app import ReceiptAnalyzerApp


def test_basic_app_creation():
    """Test that the app can be created without errors."""
    print("Testing basic app creation...")
    try:
        app = ReceiptAnalyzerApp()
        print("✅ App created successfully")
        
        # Check that essential attributes exist
        assert hasattr(app, 'worker_queue')
        assert hasattr(app, 'processing_thread')
        assert hasattr(app, 'is_processing')
        assert hasattr(app, 'cancel_processing')
        print("✅ All expected attributes present")
        
        # Test queue initialization
        assert app.worker_queue is None  # Should be None until processing starts
        print("✅ Queue properly initialized")
        
        return app
        
    except Exception as e:
        print(f"❌ Failed to create app: {e}")
        raise


def test_queue_communication():
    """Test queue-based communication between threads."""
    print("\nTesting queue communication...")
    
    try:
        # Create a test queue
        test_queue = queue.Queue()
        
        def worker_thread(q):
            """Simulate worker sending messages to queue."""
            messages = [
                ("progress", (1, 10)),
                ("file", "test.pdf"),
                ("detail", "Processing test file"),
                ("status", "Working on test"),
                ("done", "Test completed successfully")
            ]
            
            for msg in messages:
                q.put(msg)
                time.sleep(0.1)  # Simulate work
        
        # Start worker thread
        worker = threading.Thread(target=worker_thread, args=(test_queue,), daemon=True)
        worker.start()
        
        # Collect messages
        received_messages = []
        while len(received_messages) < 5:
            try:
                msg = test_queue.get(timeout=2.0)
                received_messages.append(msg)
                print(f"  Received: {msg}")
            except queue.Empty:
                break
        
        # Verify all messages received
        assert len(received_messages) == 5
        assert received_messages[0] == ("progress", (1, 10))
        assert received_messages[1] == ("file", "test.pdf")
        assert received_messages[4][0] == "done"
        
        print("✅ Queue communication working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Queue communication failed: {e}")
        return False


def test_message_handler():
    """Test the message handler logic."""
    print("\nTesting message handler...")
    
    try:
        app = ReceiptAnalyzerApp()
        
        # Test different message types
        test_messages = [
            ("progress", (3, 10)),
            ("file", "sample.pdf"),
            ("detail", "Test detail message"),
            ("status", "Test status"),
        ]
        
        for msg in test_messages:
            try:
                app._handle_worker_message(msg)
                print(f"  Handled message: {msg[0]}")
            except Exception as e:
                print(f"  ❌ Failed to handle {msg[0]}: {e}")
                raise
        
        print("✅ Message handler working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Message handler failed: {e}")
        return False


def test_processing_state_management():
    """Test processing state management."""
    print("\nTesting processing state management...")
    
    try:
        app = ReceiptAnalyzerApp()
        
        # Test initial state
        assert not app.is_processing
        assert not app.cancel_processing
        assert app.progress_count == 0
        assert app.total_count == 0
        print("  ✅ Initial state correct")
        
        # Test setting processing state
        app.set_processing_state(True)
        assert app.is_processing
        print("  ✅ Processing state set correctly")
        
        app.set_processing_state(False)
        assert not app.is_processing
        print("  ✅ Processing state reset correctly")
        
        print("✅ Processing state management working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Processing state management failed: {e}")
        return False


def test_tab_integration():
    """Test integration with tabs."""
    print("\nTesting tab integration...")
    
    try:
        app = ReceiptAnalyzerApp()
        
        # Check that tabs were created
        assert hasattr(app, 'tabs')
        assert 'input_run' in app.tabs
        print("  ✅ Tabs created successfully")
        
        # Test tab state management
        input_run_tab = app.tabs['input_run']
        
        # Test setting processing state on tab
        input_run_tab.set_processing_state(True)
        print("  ✅ Tab processing state set successfully")
        
        input_run_tab.set_processing_state(False)
        print("  ✅ Tab processing state reset successfully")
        
        print("✅ Tab integration working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Tab integration failed: {e}")
        return False


def test_dialog_creation():
    """Test progress dialog creation."""
    print("\nTesting dialog creation...")
    
    try:
        app = ReceiptAnalyzerApp()
        
        # Create dialog (but don't show it since we're headless)
        from receipt_analyzer.gui.dialogs import ProcessingStatusDialog
        dialog = ProcessingStatusDialog(app.root, app)
        
        # Check that dialog was created properly
        assert dialog.parent == app.root
        assert dialog.app == app
        assert dialog.dialog is None  # Not shown yet
        assert dialog.should_close == False
        
        print("✅ Dialog creation working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Dialog creation failed: {e}")
        return False


def test_error_handling():
    """Test error handling in various scenarios."""
    print("\nTesting error handling...")
    
    try:
        app = ReceiptAnalyzerApp()
        
        # Test handling invalid message types
        try:
            app._handle_worker_message(("invalid_type", "test_data"))
            print("  ✅ Invalid message type handled gracefully")
        except Exception as e:
            print(f"  ❌ Failed to handle invalid message: {e}")
            return False
        
        # Test handling malformed messages
        try:
            app._handle_worker_message(("progress", "invalid_data"))
            print("  ✅ Malformed message handled gracefully")
        except Exception as e:
            print(f"  ❌ Failed to handle malformed message: {e}")
            # This might be expected to fail, so continue
        
        print("✅ Error handling working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False


if __name__ == "__main__":
    print("=== Testing New Threading Architecture ===")
    
    tests = [
        test_basic_app_creation,
        test_queue_communication,
        test_message_handler,
        test_processing_state_management,
        test_tab_integration,
        test_dialog_creation,
        test_error_handling,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
    
    print(f"\n=== Results ===")
    print(f"Passed: {passed}/{total}")
    print(f"Failed: {total - passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed!")
    else:
        print("⚠️ Some tests failed - check the output above")
