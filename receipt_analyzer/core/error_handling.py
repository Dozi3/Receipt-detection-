"""Standardized error handling utilities for consistent patterns across all modules."""

import functools
import traceback
from typing import Callable, Any, Optional, Union, TypeVar, Type
from pathlib import Path

from .logging_utils import get_logger

T = TypeVar('T')


class ReceiptAnalyzerError(Exception):
    """Base exception for all Receipt Analyzer errors."""
    pass


class ConfigurationError(ReceiptAnalyzerError):
    """Raised when configuration is invalid or missing."""
    pass


class ProcessingError(ReceiptAnalyzerError):
    """Raised when processing operations fail."""
    pass


class ResourceError(ReceiptAnalyzerError):
    """Raised when resource operations fail (file I/O, memory, etc.)."""
    pass


class ValidationError(ReceiptAnalyzerError):
    """Raised when input validation fails."""
    pass


def with_error_handling(
    operation_name: str = "Operation",
    fallback_value: Any = None,
    reraise: bool = False,
    log_level: str = "warn"
):
    """
    Decorator to add consistent error handling to functions.
    
    Args:
        operation_name: Name of the operation for logging
        fallback_value: Value to return on error (if not re-raising)
        reraise: Whether to re-raise exceptions after logging
        log_level: Log level for errors ("debug", "warn", "fail")
    """
    def decorator(func: Callable[..., T]) -> Callable[..., Union[T, Any]]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Union[T, Any]:
            logger = get_logger()
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_msg = f"{operation_name} failed: {e}"
                
                # Log based on specified level
                if log_level == "debug":
                    logger.debug(error_msg)
                    logger.debug(f"{operation_name} error details: {traceback.format_exc()}")
                elif log_level == "warn":
                    logger.warn(error_msg)
                    logger.debug(f"{operation_name} error details: {traceback.format_exc()}")
                elif log_level == "fail":
                    logger.fail(error_msg)
                    logger.debug(f"{operation_name} error details: {traceback.format_exc()}")
                
                if reraise:
                    raise
                return fallback_value
        return wrapper
    return decorator


def with_resource_cleanup(cleanup_func: Callable, *cleanup_args, **cleanup_kwargs):
    """
    Decorator to ensure resource cleanup even on exceptions.
    
    Args:
        cleanup_func: Function to call for cleanup
        cleanup_args: Arguments for cleanup function
        cleanup_kwargs: Keyword arguments for cleanup function
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            try:
                return func(*args, **kwargs)
            finally:
                try:
                    cleanup_func(*cleanup_args, **cleanup_kwargs)
                except Exception as cleanup_error:
                    logger = get_logger()
                    logger.debug(f"Cleanup error in {func.__name__}: {cleanup_error}")
        return wrapper
    return decorator


def validate_input(
    validator_func: Callable[[Any], bool],
    error_message: str = "Input validation failed"
):
    """
    Decorator to validate function inputs.
    
    Args:
        validator_func: Function that returns True if input is valid
        error_message: Error message if validation fails
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            # Validate all arguments
            all_args = list(args) + list(kwargs.values())
            for arg in all_args:
                if not validator_func(arg):
                    raise ValidationError(f"{error_message}: {arg}")
            return func(*args, **kwargs)
        return wrapper
    return decorator


def safe_execute(
    func: Callable[..., T],
    *args,
    operation_name: str = "Operation",
    fallback_value: Any = None,
    timeout: Optional[float] = None,
    **kwargs
) -> Union[T, Any]:
    """
    Safely execute a function with comprehensive error handling.
    
    Args:
        func: Function to execute
        *args: Arguments for the function
        operation_name: Name of the operation for logging
        fallback_value: Value to return on error
        timeout: Optional timeout for the operation
        **kwargs: Keyword arguments for the function
    
    Returns:
        Function result or fallback_value on error
    """
    logger = get_logger()
    
    try:
        if timeout:
            from .threading_utils import with_timeout
            return with_timeout(func, timeout, *args, **kwargs)
        else:
            return func(*args, **kwargs)
    except Exception as e:
        logger.warn(f"{operation_name} failed: {e}")
        logger.debug(f"{operation_name} error details: {traceback.format_exc()}")
        return fallback_value


def create_error_context(operation_name: str, **context_data):
    """
    Create an error context manager for consistent error handling.
    
    Args:
        operation_name: Name of the operation
        **context_data: Additional context data to include in error messages
    """
    class ErrorContext:
        def __init__(self, name: str, **data):
            self.name = name
            self.context_data = data
            self.logger = get_logger()
        
        def __enter__(self):
            self.logger.debug(f"Starting {self.name}")
            return self
        
        def __exit__(self, exc_type, exc_val, exc_tb):
            if exc_type is not None:
                context_str = ", ".join(f"{k}={v}" for k, v in self.context_data.items())
                error_msg = f"{self.name} failed"
                if context_str:
                    error_msg += f" ({context_str})"
                error_msg += f": {exc_val}"
                
                self.logger.warn(error_msg)
                self.logger.debug(f"{self.name} error details: {traceback.format_exc()}")
            else:
                self.logger.debug(f"Completed {self.name}")
    
    return ErrorContext(operation_name, **context_data)


def handle_pdf_errors(func: Callable[..., T]) -> Callable[..., Union[T, None]]:
    """Decorator specifically for PDF processing operations."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Union[T, None]:
        logger = get_logger()
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Extract PDF path if available in args
            pdf_path = "unknown"
            for arg in args:
                if isinstance(arg, (str, Path)) and str(arg).endswith('.pdf'):
                    pdf_path = Path(arg).name
                    break
            
            logger.warn(f"PDF processing error in {func.__name__} for {pdf_path}: {e}")
            logger.debug(f"PDF error details: {traceback.format_exc()}")
            return None
    return wrapper


def handle_image_errors(func: Callable[..., T]) -> Callable[..., Union[T, None]]:
    """Decorator specifically for image processing operations."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Union[T, None]:
        logger = get_logger()
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.warn(f"Image processing error in {func.__name__}: {e}")
            logger.debug(f"Image error details: {traceback.format_exc()}")
            return None
    return wrapper


def handle_ocr_errors(func: Callable[..., T]) -> Callable[..., tuple]:
    """Decorator specifically for OCR operations."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> tuple:
        logger = get_logger()
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.warn(f"OCR error in {func.__name__}: {e}")
            logger.debug(f"OCR error details: {traceback.format_exc()}")
            return "", {}  # Return empty text and metadata
    return wrapper


def propagate_errors(*exception_types: Type[Exception]):
    """
    Decorator to convert internal exceptions to standard types.
    
    Args:
        exception_types: Exception types to catch and convert
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            try:
                return func(*args, **kwargs)
            except exception_types as e:
                # Convert to appropriate Receipt Analyzer exception
                if isinstance(e, (FileNotFoundError, PermissionError, IOError)):
                    raise ResourceError(f"Resource error in {func.__name__}: {e}") from e
                elif isinstance(e, (ValueError, TypeError)):
                    raise ValidationError(f"Validation error in {func.__name__}: {e}") from e
                else:
                    raise ProcessingError(f"Processing error in {func.__name__}: {e}") from e
        return wrapper
    return decorator
