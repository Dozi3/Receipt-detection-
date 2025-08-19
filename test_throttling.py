"""Test throttling functionality."""

import time
from receipt_analyzer.core.logging_utils import LogStream, LogRecord, LogLevel

def test_throttling():
    """Test that debug message throttling works correctly."""
    print("Testing LogStream debug message throttling...")
    
    log_stream = LogStream()
    log_stream.enable_debug_throttle(True)
    
    # Track received messages
    received_messages = []
    
    def listener(record):
        received_messages.append(record)
        print(f"Listener received: {record.level} - {record.message}")
    
    log_stream.add_listener(listener)
    
    print(f"Debug throttle interval: {log_stream.debug_throttle_interval}s")
    print("\nSending rapid debug messages...")
    
    start_time = time.time()
    
    # Send rapid debug messages
    for i in range(10):
        debug_record = LogRecord(LogLevel.DEBUG, f"Debug message {i}")
        log_stream.add_record(debug_record)
        time.sleep(0.05)  # 50ms between messages
    
    # Send an INFO message (should always go through)
    info_record = LogRecord(LogLevel.INFO, "Important info message")
    log_stream.add_record(info_record)
    
    end_time = time.time()
    elapsed = end_time - start_time
    
    print(f"\nTest completed in {elapsed:.2f} seconds")
    print(f"Sent 10 debug messages + 1 info message")
    print(f"Listener received {len(received_messages)} messages")
    
    # Count message types
    debug_count = sum(1 for r in received_messages if r.level == LogLevel.DEBUG)
    info_count = sum(1 for r in received_messages if r.level == LogLevel.INFO)
    
    print(f"Debug messages received: {debug_count} (should be < 10 due to throttling)")
    print(f"Info messages received: {info_count} (should be 1)")
    
    if debug_count < 10 and info_count == 1:
        print("✅ Throttling working correctly!")
    else:
        print("❌ Throttling not working as expected")

if __name__ == "__main__":
    test_throttling()
