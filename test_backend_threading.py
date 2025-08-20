#!/usr/bin/env python3
"""Test backend processing and threading logic without GUI components."""

import threading
import queue
import time
from pathlib import Path
import tempfile
import os


def test_worker_thread_logic():
    """Test the worker thread logic without GUI."""
    print("Testing worker thread logic...")
    
    try:
        # Mock the processing components
        class MockApp:
            def __init__(self):
                self.cancel_processing = False
                self.config = None
                self.vendor_map = None
        
        app = MockApp()
        test_queue = queue.Queue()
        
        # Create a temporary directory with test files
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create some dummy PDF files for testing
            test_pdf1 = temp_path / "test1.pdf"
            test_pdf2 = temp_path / "test2.pdf"
            
            # Create simple dummy files (not real PDFs, but for testing structure)
            test_pdf1.write_text("dummy pdf content")
            test_pdf2.write_text("dummy pdf content")
            
            def mock_find_pdf_files(input_dir):
                """Mock PDF file finder."""
                return [test_pdf1, test_pdf2]
            
            def mock_process_pdf_files(pdf_files, output_dir, config, vendor_map):
                """Mock PDF processor that simulates work."""
                time.sleep(0.1)  # Simulate processing time
                return len(pdf_files)  # Return number of receipts found
            
            def mock_worker_process(input_dir, output_dir, q):
                """Mock worker process."""
                try:
                    # Find PDF files
                    pdf_files = mock_find_pdf_files(input_dir)
                    if not pdf_files:
                        q.put(("error", "No PDF files found"))
                        return
                    
                    q.put(("detail", f"Found {len(pdf_files)} PDF files to process"))
                    q.put(("progress", (0, len(pdf_files))))
                    
                    total_receipts = 0
                    success_count = 0
                    
                    for i, pdf_path in enumerate(pdf_files):
                        if app.cancel_processing:
                            q.put(("cancelled", None))
                            return
                        
                        q.put(("progress", (i+1, len(pdf_files))))
                        q.put(("file", pdf_path.name))
                        q.put(("detail", f"Processing file {i+1}/{len(pdf_files)}: {pdf_path.name}"))
                        
                        try:
                            receipt_count = mock_process_pdf_files([pdf_path], temp_path, None, None)
                            success_count += 1
                            total_receipts += receipt_count
                            q.put(("detail", f"Extracted {receipt_count} receipts from {pdf_path.name}"))
                        except Exception as e:
                            q.put(("detail", f"Error processing {pdf_path.name}: {e}"))
                    
                    summary = f"Processing completed! Files processed: {success_count}/{len(pdf_files)} Total receipts: {total_receipts}"
                    q.put(("done", summary))
                    
                except Exception as e:
                    q.put(("error", f"Unexpected error: {e}"))
            
            # Start worker thread
            worker = threading.Thread(
                target=mock_worker_process,
                args=(temp_path, temp_path, test_queue),
                daemon=True
            )
            worker.start()
            
            # Collect messages
            messages = []
            timeout = 5.0
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                try:
                    msg = test_queue.get(timeout=0.5)
                    messages.append(msg)
                    print(f"  Received: {msg}")
                    
                    # Stop if we get completion message
                    if msg[0] in ['done', 'error', 'cancelled']:
                        break
                        
                except queue.Empty:
                    continue
            
            worker.join(timeout=1.0)
            
            # Verify we got expected messages
            assert len(messages) > 0, "Should have received at least one message"
            
            # Check for key message types
            message_types = [msg[0] for msg in messages]
            assert 'detail' in message_types, "Should have detail messages"
            assert 'progress' in message_types, "Should have progress messages"
            assert 'file' in message_types, "Should have file messages"
            assert 'done' in message_types, "Should have completion message"
            
            print("✅ Worker thread logic working correctly")
            return True
            
    except Exception as e:
        print(f"❌ Worker thread logic failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_cancellation_logic():
    """Test cancellation logic."""
    print("\nTesting cancellation logic...")
    
    try:
        class MockApp:
            def __init__(self):
                self.cancel_processing = False
                self.config = None
                self.vendor_map = None
        
        app = MockApp()
        test_queue = queue.Queue()
        
        def cancellable_worker(q):
            """Worker that checks for cancellation."""
            for i in range(10):
                if app.cancel_processing:
                    q.put(("cancelled", None))
                    return
                
                q.put(("progress", (i+1, 10)))
                time.sleep(0.05)
            
            q.put(("done", "Completed without cancellation"))
        
        # Start worker
        worker = threading.Thread(target=cancellable_worker, args=(test_queue,), daemon=True)
        worker.start()
        
        # Let it run for a bit
        time.sleep(0.1)
        
        # Cancel it
        app.cancel_processing = True
        
        # Collect messages
        messages = []
        timeout = 2.0
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                msg = test_queue.get(timeout=0.2)
                messages.append(msg)
                
                if msg[0] in ['done', 'cancelled']:
                    break
                    
            except queue.Empty:
                break
        
        worker.join(timeout=1.0)
        
        # Verify cancellation worked
        final_message = messages[-1] if messages else None
        assert final_message is not None, "Should have received at least one message"
        assert final_message[0] == 'cancelled', f"Expected cancellation, got {final_message}"
        
        print("✅ Cancellation logic working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Cancellation logic failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_error_propagation():
    """Test error propagation from worker to main thread."""
    print("\nTesting error propagation...")
    
    try:
        test_queue = queue.Queue()
        
        def error_worker(q):
            """Worker that generates an error."""
            try:
                # Simulate some work
                q.put(("detail", "Starting work"))
                
                # Generate an error
                raise ValueError("Test error from worker thread")
                
            except Exception as e:
                q.put(("error", f"Worker error: {e}"))
        
        # Start worker
        worker = threading.Thread(target=error_worker, args=(test_queue,), daemon=True)
        worker.start()
        
        # Collect messages
        messages = []
        timeout = 2.0
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                msg = test_queue.get(timeout=0.5)
                messages.append(msg)
                print(f"  Received: {msg}")
                
                if msg[0] == 'error':
                    break
                    
            except queue.Empty:
                break
        
        worker.join(timeout=1.0)
        
        # Verify error was propagated
        assert len(messages) >= 2, "Should have detail and error messages"
        
        error_msg = [msg for msg in messages if msg[0] == 'error']
        assert len(error_msg) == 1, "Should have exactly one error message"
        assert "Test error from worker thread" in error_msg[0][1], "Error message should contain original error"
        
        print("✅ Error propagation working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Error propagation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_message_queue_robustness():
    """Test queue robustness under various conditions."""
    print("\nTesting message queue robustness...")
    
    try:
        test_queue = queue.Queue(maxsize=100)  # Limited size queue
        
        def rapid_sender(q):
            """Send many messages rapidly."""
            for i in range(50):
                q.put(("detail", f"Message {i}"))
                time.sleep(0.01)
            q.put(("done", "All messages sent"))
        
        # Start sender
        sender = threading.Thread(target=rapid_sender, args=(test_queue,), daemon=True)
        sender.start()
        
        # Receive messages (simulating GUI processing)
        received_count = 0
        timeout = 3.0
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                msg = test_queue.get(timeout=0.1)
                received_count += 1
                
                if msg[0] == 'done':
                    break
                    
            except queue.Empty:
                continue
        
        sender.join(timeout=1.0)
        
        # Should have received all 50 detail messages + 1 done message
        assert received_count == 51, f"Expected 51 messages, got {received_count}"
        
        print("✅ Message queue robustness working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Message queue robustness failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=== Testing Backend Threading Logic ===")
    
    tests = [
        test_worker_thread_logic,
        test_cancellation_logic,
        test_error_propagation,
        test_message_queue_robustness,
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
        print("🎉 All backend threading tests passed!")
    else:
        print("⚠️ Some tests failed - check the output above")
