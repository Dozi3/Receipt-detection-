"""Standardized threading utilities for consistent patterns across all modules."""

import threading
import time
from typing import Optional, Callable, Any
from pathlib import Path

from .logging_utils import get_logger


class CancellationToken:
    """Thread-safe cancellation token for long-running operations."""
    
    def __init__(self):
        self._cancelled = False
        self._lock = threading.Lock()
    
    def cancel(self):
        """Mark the operation as cancelled."""
        with self._lock:
            self._cancelled = True
    
    def is_cancelled(self) -> bool:
        """Check if the operation has been cancelled."""
        with self._lock:
            return self._cancelled
    
    def check_cancelled(self, operation_name: str = "Operation"):
        """Check cancellation and raise exception if cancelled."""
        if self.is_cancelled():
            raise OperationCancelledException(f"{operation_name} was cancelled")


class OperationCancelledException(Exception):
    """Exception raised when an operation is cancelled."""
    pass


class TimeoutException(Exception):
    """Exception raised when an operation times out."""
    pass


def with_timeout(func: Callable, timeout: float, *args, **kwargs) -> Any:
    """
    Execute a function with a timeout using threading.
    
    Args:
        func: Function to execute
        timeout: Timeout in seconds
        *args, **kwargs: Arguments for the function
        
    Returns:
        Function result
        
    Raises:
        TimeoutException: If operation times out
        Any exception raised by the function
    """
    logger = get_logger()
    
    result = None
    exception = None
    
    def target():
        nonlocal result, exception
        try:
            result = func(*args, **kwargs)
        except Exception as e:
            exception = e
    
    thread = threading.Thread(target=target, daemon=True)
    thread.start()
    thread.join(timeout=timeout)
    
    if thread.is_alive():
        logger.debug(f"Operation timed out after {timeout} seconds")
        raise TimeoutException(f"Operation timed out after {timeout} seconds")
    
    if exception:
        raise exception
    
    return result


def with_cancellation_check(func: Callable, token: CancellationToken, check_interval: float = 0.1) -> Callable:
    """
    Decorator to add cancellation checking to a function.
    
    Args:
        func: Function to wrap
        token: Cancellation token to check
        check_interval: How often to check for cancellation (seconds)
        
    Returns:
        Wrapped function that checks for cancellation
    """
    def wrapper(*args, **kwargs):
        # Check cancellation before starting
        token.check_cancelled(func.__name__)
        
        # For simple functions, just execute
        if not hasattr(func, '__code__') or func.__code__.co_argcount == 0:
            return func(*args, **kwargs)
        
        # For more complex operations, we'd need to modify the function itself
        # For now, just check before execution
        return func(*args, **kwargs)
    
    return wrapper


class ProgressCallback:
    """Standardized progress callback for long-running operations."""
    
    def __init__(self, callback: Optional[Callable] = None):
        self.callback = callback
        self.last_update = 0
        self.update_interval = 0.1  # Minimum 100ms between updates
    
    def update(self, current: int, total: int, message: str = ""):
        """Update progress if enough time has passed."""
        current_time = time.time()
        if current_time - self.last_update >= self.update_interval or current == total:
            self.last_update = current_time
            if self.callback:
                try:
                    self.callback(current, total, message)
                except Exception as e:
                    # Don't let callback errors break the main operation
                    logger = get_logger()
                    logger.debug(f"Progress callback error: {e}")


class StandardWorkerThread:
    """Standardized worker thread with consistent patterns."""
    
    def __init__(self, target: Callable, name: str = "Worker"):
        self.target = target
        self.name = name
        self.thread = None
        self.cancellation_token = CancellationToken()
        self.result = None
        self.exception = None
        self._completed = False
    
    def start(self, *args, **kwargs):
        """Start the worker thread."""
        def worker():
            try:
                self.result = self.target(self.cancellation_token, *args, **kwargs)
            except Exception as e:
                self.exception = e
            finally:
                self._completed = True
        
        self.thread = threading.Thread(target=worker, name=self.name, daemon=True)
        self.thread.start()
    
    def cancel(self):
        """Cancel the operation."""
        self.cancellation_token.cancel()
    
    def join(self, timeout: Optional[float] = None) -> bool:
        """Wait for the thread to complete."""
        if self.thread:
            self.thread.join(timeout=timeout)
            return not self.thread.is_alive()
        return True
    
    def is_completed(self) -> bool:
        """Check if the operation is completed."""
        return self._completed
    
    def get_result(self):
        """Get the result, raising any exception that occurred."""
        if self.exception:
            raise self.exception
        return self.result
