"""Resource management utilities for consistent cleanup across all modules."""

import contextlib
import gc
import psutil
import os
from typing import Optional, Any, Generator, List
from pathlib import Path

from .logging_utils import get_logger


class MemoryMonitor:
    """Monitor memory usage for long-running operations."""
    
    def __init__(self, operation_name: str = "Operation", warning_threshold_mb: int = 1024):
        self.operation_name = operation_name
        self.warning_threshold_mb = warning_threshold_mb
        self.start_memory = None
        self.peak_memory = None
        self.logger = get_logger()
    
    def start_monitoring(self):
        """Start monitoring memory usage."""
        self.start_memory = self._get_memory_usage()
        self.peak_memory = self.start_memory
        self.logger.debug(f"{self.operation_name}: Started with {self.start_memory:.1f} MB memory")
    
    def check_memory(self, stage: str = ""):
        """Check current memory usage and warn if high."""
        current_memory = self._get_memory_usage()
        if current_memory > self.peak_memory:
            self.peak_memory = current_memory
        
        if current_memory > self.warning_threshold_mb:
            stage_str = f" ({stage})" if stage else ""
            self.logger.warn(f"{self.operation_name}{stage_str}: High memory usage: {current_memory:.1f} MB")
            
        return current_memory
    
    def finish_monitoring(self):
        """Finish monitoring and report memory usage."""
        final_memory = self._get_memory_usage()
        if self.start_memory:
            memory_delta = final_memory - self.start_memory
            self.logger.debug(f"{self.operation_name}: Finished with {final_memory:.1f} MB "
                            f"(peak: {self.peak_memory:.1f} MB, delta: {memory_delta:+.1f} MB)")
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            process = psutil.Process(os.getpid())
            return process.memory_info().rss / 1024 / 1024
        except:
            return 0.0


@contextlib.contextmanager
def pdf_document(pdf_path: Path, operation_name: str = "PDF Operation") -> Generator[Any, None, None]:
    """Context manager for PDF document operations with automatic cleanup."""
    import fitz
    
    logger = get_logger()
    doc = None
    
    try:
        logger.debug(f"{operation_name}: Opening PDF {pdf_path}")
        doc = fitz.open(pdf_path)
        yield doc
    except Exception as e:
        logger.warn(f"{operation_name}: Error with PDF {pdf_path}: {e}")
        raise
    finally:
        if doc:
            try:
                doc.close()
                logger.debug(f"{operation_name}: Closed PDF {pdf_path}")
            except Exception as cleanup_error:
                logger.debug(f"{operation_name}: Error closing PDF: {cleanup_error}")


@contextlib.contextmanager
def memory_managed_operation(operation_name: str, warning_threshold_mb: int = 1024) -> Generator[MemoryMonitor, None, None]:
    """Context manager for operations that need memory monitoring."""
    monitor = MemoryMonitor(operation_name, warning_threshold_mb)
    
    try:
        monitor.start_monitoring()
        yield monitor
    finally:
        monitor.finish_monitoring()
        # Force garbage collection
        gc.collect()


@contextlib.contextmanager
def temp_directory_cleanup(temp_dir: Path, keep_on_error: bool = False) -> Generator[Path, None, None]:
    """Context manager for temporary directory operations with cleanup."""
    import shutil
    
    logger = get_logger()
    
    try:
        temp_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Created temporary directory: {temp_dir}")
        yield temp_dir
    except Exception as e:
        logger.warn(f"Error in temporary directory operation: {e}")
        if not keep_on_error and temp_dir.exists():
            try:
                shutil.rmtree(temp_dir)
                logger.debug(f"Cleaned up temporary directory after error: {temp_dir}")
            except Exception as cleanup_error:
                logger.debug(f"Failed to cleanup temporary directory: {cleanup_error}")
        raise
    else:
        # Normal cleanup
        if temp_dir.exists():
            try:
                shutil.rmtree(temp_dir)
                logger.debug(f"Cleaned up temporary directory: {temp_dir}")
            except Exception as cleanup_error:
                logger.debug(f"Failed to cleanup temporary directory: {cleanup_error}")


class ResourcePool:
    """Pool for managing expensive resources like PDF documents."""
    
    def __init__(self, max_size: int = 10):
        self.max_size = max_size
        self.pool = {}
        self.usage_count = {}
        self.logger = get_logger()
    
    def get_pdf_document(self, pdf_path: Path):
        """Get a PDF document from the pool or create new one."""
        import fitz
        
        path_str = str(pdf_path)
        
        if path_str in self.pool:
            self.usage_count[path_str] += 1
            self.logger.debug(f"Reusing PDF document from pool: {pdf_path}")
            return self.pool[path_str]
        
        # Check if pool is full
        if len(self.pool) >= self.max_size:
            self._evict_least_used()
        
        # Create new document
        doc = fitz.open(pdf_path)
        self.pool[path_str] = doc
        self.usage_count[path_str] = 1
        self.logger.debug(f"Added PDF document to pool: {pdf_path}")
        
        return doc
    
    def release_pdf_document(self, pdf_path: Path):
        """Release a PDF document (decrease usage count)."""
        path_str = str(pdf_path)
        
        if path_str in self.usage_count:
            self.usage_count[path_str] -= 1
            if self.usage_count[path_str] <= 0:
                self._remove_document(path_str)
    
    def _evict_least_used(self):
        """Remove the least used document from the pool."""
        if not self.pool:
            return
        
        least_used = min(self.usage_count.keys(), key=lambda k: self.usage_count[k])
        self._remove_document(least_used)
    
    def _remove_document(self, path_str: str):
        """Remove a document from the pool."""
        if path_str in self.pool:
            try:
                self.pool[path_str].close()
            except Exception as e:
                self.logger.debug(f"Error closing pooled document: {e}")
            
            del self.pool[path_str]
            del self.usage_count[path_str]
            self.logger.debug(f"Removed document from pool: {path_str}")
    
    def clear(self):
        """Clear the entire pool."""
        for path_str in list(self.pool.keys()):
            self._remove_document(path_str)


# Global resource pool instance
_resource_pool = ResourcePool()


def get_resource_pool() -> ResourcePool:
    """Get the global resource pool instance."""
    return _resource_pool


@contextlib.contextmanager
def file_lock(file_path: Path, operation_name: str = "File Operation") -> Generator[Path, None, None]:
    """Context manager for file locking during operations."""
    import fcntl
    
    logger = get_logger()
    lock_file = None
    
    try:
        # Create lock file
        lock_path = file_path.with_suffix(file_path.suffix + '.lock')
        lock_file = open(lock_path, 'w')
        
        # Try to acquire lock
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        logger.debug(f"{operation_name}: Acquired lock for {file_path}")
        
        yield file_path
        
    except BlockingIOError:
        logger.warn(f"{operation_name}: File {file_path} is locked by another process")
        raise
    except Exception as e:
        logger.warn(f"{operation_name}: Error acquiring lock for {file_path}: {e}")
        raise
    finally:
        if lock_file:
            try:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
                lock_file.close()
                lock_path.unlink(missing_ok=True)
                logger.debug(f"{operation_name}: Released lock for {file_path}")
            except Exception as cleanup_error:
                logger.debug(f"{operation_name}: Error releasing lock: {cleanup_error}")


class ResourceTracker:
    """Track resource usage across the application."""
    
    def __init__(self):
        self.open_files: List[str] = []
        self.open_pdfs: List[str] = []
        self.temp_dirs: List[str] = []
        self.logger = get_logger()
    
    def track_file(self, file_path: str):
        """Track an open file."""
        self.open_files.append(file_path)
        self.logger.debug(f"Tracking file: {file_path}")
    
    def untrack_file(self, file_path: str):
        """Stop tracking a file."""
        if file_path in self.open_files:
            self.open_files.remove(file_path)
            self.logger.debug(f"Untracking file: {file_path}")
    
    def track_pdf(self, pdf_path: str):
        """Track an open PDF."""
        self.open_pdfs.append(pdf_path)
        self.logger.debug(f"Tracking PDF: {pdf_path}")
    
    def untrack_pdf(self, pdf_path: str):
        """Stop tracking a PDF."""
        if pdf_path in self.open_pdfs:
            self.open_pdfs.remove(pdf_path)
            self.logger.debug(f"Untracking PDF: {pdf_path}")
    
    def get_summary(self) -> str:
        """Get a summary of tracked resources."""
        return (f"Open files: {len(self.open_files)}, "
                f"Open PDFs: {len(self.open_pdfs)}, "
                f"Temp directories: {len(self.temp_dirs)}")


# Global resource tracker
_resource_tracker = ResourceTracker()


def get_resource_tracker() -> ResourceTracker:
    """Get the global resource tracker."""
    return _resource_tracker
