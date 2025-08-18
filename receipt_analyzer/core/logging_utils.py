"""Logging utilities for receipt analyzer."""

import logging
import sys
from pathlib import Path
from typing import Optional, List, IO
from datetime import datetime
from threading import Lock
import queue


class LogLevel:
    """Log level constants."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    FAIL = "FAIL"
    SUCCESS = "SUCCESS"


class LogRecord:
    """A log record with timestamp and level."""
    
    def __init__(self, level: str, message: str, timestamp: Optional[datetime] = None):
        self.level = level
        self.message = message
        self.timestamp = timestamp or datetime.now()
    
    def __str__(self) -> str:
        return f"{self.timestamp.strftime('%Y-%m-%d %H:%M:%S')} [{self.level}] {self.message}"


class LogStream:
    """Thread-safe log stream that can be monitored by GUI."""
    
    def __init__(self, max_records: int = 1000):
        self.records: List[LogRecord] = []
        self.max_records = max_records
        self.lock = Lock()
        self.listeners = []
    
    def add_listener(self, callback):
        """Add a callback function to be called when new log records are added."""
        with self.lock:
            self.listeners.append(callback)
    
    def remove_listener(self, callback):
        """Remove a listener callback."""
        with self.lock:
            if callback in self.listeners:
                self.listeners.remove(callback)
    
    def add_record(self, record: LogRecord):
        """Add a log record."""
        with self.lock:
            self.records.append(record)
            # Keep only the most recent records
            if len(self.records) > self.max_records:
                self.records = self.records[-self.max_records:]
            
            # Notify listeners
            for listener in self.listeners:
                try:
                    listener(record)
                except Exception as e:
                    print(f"Error in log listener: {e}", file=sys.stderr)
    
    def get_records(self, level_filter: Optional[str] = None) -> List[LogRecord]:
        """Get all records, optionally filtered by level."""
        with self.lock:
            if level_filter:
                return [r for r in self.records if r.level == level_filter]
            return self.records.copy()
    
    def clear(self):
        """Clear all records."""
        with self.lock:
            self.records.clear()


class Logger:
    """Receipt analyzer logger with file and stream output."""
    
    def __init__(self, log_file: Optional[Path] = None, log_stream: Optional[LogStream] = None):
        self.log_file = log_file
        self.log_stream = log_stream or LogStream()
        self.file_handle: Optional[IO] = None
        self.lock = Lock()
        
        if self.log_file:
            self._open_log_file()
    
    def _open_log_file(self):
        """Open the log file for writing."""
        try:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            self.file_handle = open(self.log_file, 'a', encoding='utf-8')
        except OSError as e:
            print(f"Warning: Could not open log file {self.log_file}: {e}", file=sys.stderr)
            self.file_handle = None
    
    def _write_to_file(self, record: LogRecord):
        """Write a record to the log file."""
        if self.file_handle:
            try:
                self.file_handle.write(str(record) + '\n')
                self.file_handle.flush()
            except OSError as e:
                print(f"Warning: Could not write to log file: {e}", file=sys.stderr)
    
    def log(self, level: str, message: str):
        """Log a message with the specified level."""
        record = LogRecord(level, message)
        
        with self.lock:
            # Write to file
            if self.file_handle:
                self._write_to_file(record)
            
            # Add to stream
            self.log_stream.add_record(record)
            
            # Also print to console
            print(str(record))
    
    def info(self, message: str):
        """Log an info message."""
        self.log(LogLevel.INFO, message)
    
    def debug(self, message: str):
        """Log a debug message."""
        self.log(LogLevel.DEBUG, message)
    
    def warn(self, message: str):
        """Log a warning message."""
        self.log(LogLevel.WARN, message)
    
    def fail(self, message: str):
        """Log a failure message."""
        self.log(LogLevel.FAIL, message)
    
    def success(self, message: str):
        """Log a success message."""
        self.log(LogLevel.SUCCESS, message)
    
    def close(self):
        """Close the log file."""
        with self.lock:
            if self.file_handle:
                self.file_handle.close()
                self.file_handle = None
    
    def __del__(self):
        """Cleanup when logger is destroyed."""
        try:
            self.close()
        except:
            pass


# Global logger instance
_logger: Optional[Logger] = None


def init_logger(log_file: Optional[Path] = None, log_stream: Optional[LogStream] = None) -> Logger:
    """Initialize the global logger."""
    global _logger
    _logger = Logger(log_file, log_stream)
    return _logger


def get_logger() -> Logger:
    """Get the global logger instance."""
    global _logger
    if _logger is None:
        _logger = Logger()
    return _logger


def log_info(message: str):
    """Log an info message using the global logger."""
    get_logger().info(message)


def log_warn(message: str):
    """Log a warning message using the global logger."""
    get_logger().warn(message)


def log_fail(message: str):
    """Log a failure message using the global logger."""
    get_logger().fail(message)


def log_success(message: str):
    """Log a success message using the global logger."""
    get_logger().success(message)


def log_debug(message: str):
    """Log a debug message using the global logger."""
    get_logger().debug(message)


def format_pdf_log(pdf_path: str, page_num: int, message: str) -> str:
    """Format a log message for PDF processing."""
    pdf_name = Path(pdf_path).name
    return f"{pdf_name} page {page_num}: {message}"


def format_receipt_log(pdf_path: str, page_num: int, receipt_num: int, message: str) -> str:
    """Format a log message for receipt processing."""
    pdf_name = Path(pdf_path).name
    return f"{pdf_name} page {page_num} receipt {receipt_num}: {message}"