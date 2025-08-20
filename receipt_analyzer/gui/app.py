"""Main GUI application using Tkinter with tabbed interface."""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import queue
from pathlib import Path
from typing import Optional, Dict, Any

from ..core.config import Config, load_config, save_config
from ..core.logging_utils import LogStream, init_logger, get_logger
from ..core.vendors import load_vendor_map, save_vendor_map
from .tabs.tab_input_run import InputRunTab
from .tabs.tab_detection import DetectionTab
from .tabs.tab_ocr import OCRTab
from .tabs.tab_parsing_naming import ParsingNamingTab
from .tabs.tab_vendors import VendorsTab
from .tabs.tab_outputs import OutputsTab
from .tabs.tab_logs import LogsTab
from .dialogs import ProcessingStatusDialog
from .utils import BusyIndicator, run_with_busy_indicator


class ReceiptAnalyzerApp:
    """Main GUI application for Receipt Analyzer."""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Receipt Analyzer v1.0.0")
        self.root.geometry("1000x700")
        self.root.minsize(800, 600)
        
        # Application state with thread safety
        self.config = load_config()
        self.vendor_map = load_vendor_map()
        self.log_stream = LogStream()
        
        # Enable debug throttling to prevent GUI overload during processing
        self.log_stream.enable_debug_throttle(True)
        
        # Thread-safe state management
        self.state_lock = threading.Lock()
        self.processing_thread: Optional[threading.Thread] = None
        self.is_processing = False
        self.cancel_processing = False
        self.progress_count = 0
        self.total_count = 0
        
        # Communication queue for worker thread
        self.worker_queue: Optional[queue.Queue] = None
        
        # Log batching for GUI performance
        self.log_batch = []
        self.log_batch_lock = threading.Lock()
        self.last_log_update = 0
        
        # Initialize logging with GUI stream
        init_logger(log_stream=self.log_stream)
        
        # Setup GUI
        self.setup_gui()
        self.setup_menu()
        
        # Configure window closing
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Setup periodic UI updates to keep the GUI responsive
        self.setup_keep_alive()
        
        # Setup log batching
        self.setup_log_batching()
    
    def setup_gui(self):
        """Setup the main GUI components."""
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create tabs
        self.tabs = {}
        
        # Input & Run tab
        self.tabs['input_run'] = InputRunTab(self.notebook, self)
        self.notebook.add(self.tabs['input_run'].frame, text="Input & Run")
        
        # Detection tab
        self.tabs['detection'] = DetectionTab(self.notebook, self)
        self.notebook.add(self.tabs['detection'].frame, text="Detection")
        
        # OCR tab
        self.tabs['ocr'] = OCRTab(self.notebook, self)
        self.notebook.add(self.tabs['ocr'].frame, text="OCR")
        
        # Parsing & Naming tab
        self.tabs['parsing_naming'] = ParsingNamingTab(self.notebook, self)
        self.notebook.add(self.tabs['parsing_naming'].frame, text="Parsing & Naming")
        
        # Vendors tab
        self.tabs['vendors'] = VendorsTab(self.notebook, self)
        self.notebook.add(self.tabs['vendors'].frame, text="Vendors")
        
        # Outputs tab
        self.tabs['outputs'] = OutputsTab(self.notebook, self)
        self.notebook.add(self.tabs['outputs'].frame, text="Outputs")
        
        # Logs tab
        self.tabs['logs'] = LogsTab(self.notebook, self)
        self.notebook.add(self.tabs['logs'].frame, text="Logs")
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        self.status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def setup_menu(self):
        """Setup the application menu."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Load Config...", command=self.load_config_file)
        file_menu.add_command(label="Save Config...", command=self.save_config_file)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_closing)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)
    
    def setup_keep_alive(self):
        """Setup a periodic task to keep the GUI responsive."""
        def keep_alive():
            # Process any pending events
            self.root.update_idletasks()
            
            # Update progress indicator if processing
            if self.is_processing:
                self.update_progress_indicator()
                
            # Schedule the next keep_alive call
            self.root.after(100, keep_alive)
            
        # Start the keep-alive loop
        self.root.after(100, keep_alive)
    
    def setup_log_batching(self):
        """Setup log message batching to prevent GUI overload."""
        def process_log_batch():
            import time
            current_time = time.time()
            
            # Process log batch if enough time has passed
            if current_time - self.last_log_update >= 0.2:  # 200ms batching
                with self.log_batch_lock:
                    if self.log_batch:
                        # Update log displays with batched messages
                        for tab in self.tabs.values():
                            if hasattr(tab, 'on_log_batch'):
                                tab.on_log_batch(self.log_batch.copy())
                        
                        self.log_batch.clear()
                        self.last_log_update = current_time
            
            # Schedule next batch processing
            self.root.after(100, process_log_batch)
        
        # Start batch processing
        self.root.after(100, process_log_batch)
    
    def update_progress_indicator(self):
        """Update the progress indicator during processing."""
        with self.state_lock:
            progress_count = self.progress_count
            total_count = self.total_count
            
        if total_count > 0:
            progress_text = f"Processing file {progress_count}/{total_count}"
            if 'input_run' in self.tabs:
                self.tabs['input_run'].progress_text_var.set(progress_text)
    
    def load_config_file(self):
        """Load configuration from a file."""
        filepath = filedialog.askopenfilename(
            title="Load Configuration",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            defaultextension=".json"
        )
        
        if filepath:
            try:
                self.config = load_config(Path(filepath))
                self.update_gui_from_config()
                messagebox.showinfo("Success", "Configuration loaded successfully!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load configuration:\n{str(e)}")
    
    def save_config_file(self):
        """Save current configuration to a file."""
        filepath = filedialog.asksaveasfilename(
            title="Save Configuration",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            defaultextension=".json"
        )
        
        if filepath:
            try:
                # Update config from current GUI state
                self.update_config_from_gui()
                save_config(self.config, Path(filepath))
                messagebox.showinfo("Success", "Configuration saved successfully!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save configuration:\n{str(e)}")
    
    def show_about(self):
        """Show about dialog."""
        about_text = (
            "Receipt Analyzer v1.0.0\n\n"
            "A comprehensive tool for extracting and analyzing receipts from PDF files.\n\n"
            "Features:\n"
            "• Advanced receipt detection using OpenCV\n"
            "• OCR text extraction with multiple orientations\n"
            "• Intelligent parsing and vendor recognition\n"
            "• Multiple export formats (images, CSV, JSON)\n"
            "• Batch processing with progress tracking\n\n"
            "Built with Python, Tkinter, OpenCV, and Tesseract OCR."
        )
        messagebox.showinfo("About Receipt Analyzer", about_text)
    
    def update_gui_from_config(self):
        """Update GUI components from current config."""
        try:
            # Update all tabs from config
            for tab in self.tabs.values():
                if hasattr(tab, 'update_from_config'):
                    tab.update_from_config(self.config)
        except Exception as e:
            get_logger().warn(f"Error updating GUI from config: {e}")
    
    def update_config_from_gui(self):
        """Update config from current GUI state."""
        try:
            # Update config from all tabs
            for tab in self.tabs.values():
                if hasattr(tab, 'update_config'):
                    # Check if the method takes config parameter
                    import inspect
                    sig = inspect.signature(tab.update_config)
                    if len(sig.parameters) > 0:  # Takes config parameter
                        tab.update_config(self.config)
                    else:  # No config parameter
                        tab.update_config()
        except Exception as e:
            get_logger().warn(f"Error updating config from GUI: {e}")
    
    def set_processing_state(self, is_processing: bool):
        """Thread-safe method to set processing state."""
        try:
            with self.state_lock:
                self.is_processing = is_processing
                
            # Update tabs
            for tab in self.tabs.values():
                if hasattr(tab, 'set_processing_state'):
                    tab.set_processing_state(is_processing)
                    
        except Exception as e:
            # If state setting fails, log but don't crash
            get_logger().warn(f"Error setting processing state: {e}")
            # Ensure we at least set the basic state
            with self.state_lock:
                self.is_processing = is_processing
    
    def start_processing(self, input_dir: Path, output_dir: Path):
        """Start processing in a background thread with thread-safe communication."""
        with self.state_lock:
            if self.is_processing:
                return

        # Initialize worker communication
        self.worker_queue = queue.Queue()
        with self.state_lock:
            self.cancel_processing = False
            self.progress_count = 0
            self.total_count = 0
        
        self.set_processing_state(True)

        # Update config from GUI BEFORE starting the background thread
        try:
            self.update_config_from_gui()
        except Exception as e:
            get_logger().warn(f"Failed to update config from GUI: {e}")

        # Show busy cursor for the entire application
        self.root.config(cursor="watch")
        for tab in self.tabs.values():
            if hasattr(tab, 'frame'):
                tab.frame.config(cursor="watch")

        # Start the worker thread
        self.processing_thread = threading.Thread(
            target=self._worker_process_wrapper,
            args=(input_dir, output_dir),
            daemon=True
        )
        self.processing_thread.start()

        # Start a watchdog timer to detect hanging
        self._start_processing_watchdog()

        # Show processing status dialog
        try:
            self.processing_dialog = ProcessingStatusDialog(self.root, self)
            self.processing_dialog.show()
        except Exception as e:
            get_logger().warn(f"Failed to create processing dialog: {e}")
            self.processing_dialog = None

        # Start polling the queue for updates
        self._poll_worker_queue()

    def _poll_worker_queue(self):
        """Poll the worker queue for messages and update the GUI accordingly."""
        if not self.worker_queue:
            return
            
        try:
            # Process all available messages
            message_count = 0
            while True:
                try:
                    msg = self.worker_queue.get_nowait()
                    self._handle_worker_message(msg)
                    message_count += 1
                    if message_count > 50:  # Prevent infinite loop
                        break
                except queue.Empty:
                    break  # No more messages
        except Exception as e:
            get_logger().warn(f"Error processing worker message: {e}")
        
        # Continue polling if still processing
        with self.state_lock:
            still_processing = self.is_processing
        
        if still_processing:
            # Use a shorter interval for more responsive UI
            self.root.after(50, self._poll_worker_queue)
        else:
            get_logger().debug("Stopping queue polling - processing complete")

    def _handle_worker_message(self, msg: tuple):
        """Handle a message from the worker thread."""
        try:
            msg_type, data = msg
            
            if msg_type == "progress":
                current, total = data
                with self.state_lock:
                    self.progress_count = current
                    self.total_count = total
                if self.processing_dialog:
                    self.processing_dialog.update_progress(current, total)
                    
            elif msg_type == "file":
                if self.processing_dialog:
                    self.processing_dialog.update_current_file(data)
                    
            elif msg_type == "detail":
                if self.processing_dialog:
                    self.processing_dialog.add_detail(data)
                    
            elif msg_type == "status":
                self.status_var.set(data)
                
            elif msg_type == "done":
                self._processing_complete(data)
                
            elif msg_type == "cancelled":
                self._processing_cancelled()
                
            elif msg_type == "error":
                self._processing_error(data)
                
        except Exception as e:
            get_logger().warn(f"Error handling worker message: {e}")

    def _processing_complete(self, summary: Dict[str, Any]):
        """Handle processing completion."""
        get_logger().debug("Processing completion handler called")
        
        self.set_processing_state(False)
        
        if self.processing_dialog:
            try:
                self.processing_dialog.close()
            except Exception as e:
                get_logger().warn(f"Error closing processing dialog: {e}")
            
        self._reset_cursor()
        
        # Create completion message
        message = (
            f"Processing completed successfully!\n\n"
            f"Files processed: {summary.get('success_files', 0)}/{summary.get('total_files', 0)}\n"
            f"Total receipts extracted: {summary.get('total_receipts', 0)}\n\n"
            f"Output saved to: {summary.get('output_dir', '')}"
        )
        
        # Show completion message after a brief delay to ensure dialog closes
        self.root.after(200, lambda: messagebox.showinfo("Processing Complete", message))

    def _processing_cancelled(self):
        """Handle processing cancellation."""
        get_logger().debug("Processing cancellation handler called")
        
        self.set_processing_state(False)
        
        if self.processing_dialog:
            try:
                self.processing_dialog.close()
            except Exception as e:
                get_logger().warn(f"Error closing processing dialog: {e}")
            
        self._reset_cursor()
        
        self.root.after(200, lambda: messagebox.showinfo(
            "Processing Cancelled",
            "Processing was cancelled by the user."
        ))

    def _processing_error(self, error_data):
        """Handle processing error."""
        get_logger().debug("Processing error handler called")
        
        self.set_processing_state(False)
        
        if self.processing_dialog:
            try:
                self.processing_dialog.close()
            except Exception as e:
                get_logger().warn(f"Error closing processing dialog: {e}")
            
        self._reset_cursor()
        
        if isinstance(error_data, dict):
            message = error_data.get("message", "Unknown error occurred")
            show_dialog = error_data.get("show_dialog", True)
        else:
            message = str(error_data)
            show_dialog = True
            
        if show_dialog:
            self.root.after(200, lambda: messagebox.showerror("Processing Error", message))

    def _reset_cursor(self):
        """Reset cursor for all widgets."""
        self.root.config(cursor="")
        for tab in self.tabs.values():
            if hasattr(tab, 'frame'):
                tab.frame.config(cursor="")

    def stop_processing(self):
        """Request cancellation of the current processing."""
        with self.state_lock:
            if not self.is_processing:
                return
            self.cancel_processing = True
        
        # UI update: show cancelling status
        self.status_var.set("Cancelling processing...")
        if 'input_run' in self.tabs:
            self.tabs['input_run'].progress_text_var.set("Cancelling...")

    def _start_processing_watchdog(self):
        """Start a watchdog timer to detect if processing hangs."""
        import time
        self._last_worker_activity = time.time()
        self._check_worker_activity()

    def _check_worker_activity(self):
        """Check if the worker thread is still active."""
        import time
        
        with self.state_lock:
            still_processing = self.is_processing
            
        if not still_processing:
            return  # Processing completed normally
            
        current_time = time.time()
        time_since_activity = current_time - self._last_worker_activity
        
        # If no activity for more than 30 seconds, consider it hung
        if time_since_activity > 30:
            get_logger().error("Worker thread appears to be hung - forcing termination")
            self.worker_queue.put(("error", {
                "message": "Processing appears to be stuck. This might be due to a corrupted PDF or system issue. Please try again with a different file.",
                "show_dialog": True
            }))
            return
            
        # Continue monitoring
        self.root.after(5000, self._check_worker_activity)  # Check every 5 seconds

    def _update_worker_activity(self):
        """Update the last worker activity timestamp."""
        import time
        self._last_worker_activity = time.time()

    def _worker_process_wrapper(self, input_dir: Path, output_dir: Path):
        """Wrapper that tracks activity and handles timeouts."""
        import time
        self._last_worker_activity = time.time()
        
        try:
            self._worker_process(input_dir, output_dir)
        except Exception as e:
            import traceback
            error_msg = f"Worker process crashed: {str(e)}"
            tb = traceback.format_exc()
            get_logger().error(f"{error_msg}\nTraceback: {tb}")
            self.worker_queue.put(("error", {"message": error_msg, "show_dialog": True}))
        finally:
            get_logger().debug("Worker process wrapper finished")

    def _worker_process(self, input_dir: Path, output_dir: Path):
        """
        Worker thread: does all blocking work and communicates with the GUI via queue.
        Never calls Tkinter widgets or messagebox directly.
        """
        try:
            from ..core.processing import process_pdf_files
            from ..core.pdf_io import find_pdf_files
            
            get_logger().debug(f"Worker process started: input={input_dir}, output={output_dir}")
            self._update_worker_activity()
            
            # Find PDF files
            pdf_files = find_pdf_files(input_dir)
            self._update_worker_activity()
            
            if not pdf_files:
                self.worker_queue.put(("status", f"No PDF files found in {input_dir}"))
                self.worker_queue.put(("error", {"message": f"No PDF files found in {input_dir}", "show_dialog": True}))
                return
            
            # Send initial status
            self.worker_queue.put(("status", f"Processing {len(pdf_files)} PDF files..."))
            self.worker_queue.put(("detail", f"Found {len(pdf_files)} PDF files to process"))
            get_logger().debug(f"Found {len(pdf_files)} PDF files to process")
            
            # Process files
            total_receipts = 0
            success_count = 0
            
            for i, pdf_path in enumerate(pdf_files):
                # Check for cancellation
                with self.state_lock:
                    cancelled = self.cancel_processing
                if cancelled:
                    self.worker_queue.put(("detail", "Processing cancelled by user"))
                    self.worker_queue.put(("cancelled", None))
                    return
                    
                try:
                    get_logger().debug(f"Starting to process file {i+1}/{len(pdf_files)}: {pdf_path.name}")
                    self._update_worker_activity()
                    
                    # Update progress
                    self.worker_queue.put(("progress", (i + 1, len(pdf_files))))
                    self.worker_queue.put(("status", f"Processing file {i+1}/{len(pdf_files)}: {pdf_path.name}"))
                    self.worker_queue.put(("file", pdf_path.name))
                    self.worker_queue.put(("detail", f"Processing file {i+1}/{len(pdf_files)}: {pdf_path.name}"))
                    
                    # Process file with error handling
                    get_logger().debug(f"Calling process_pdf_files for {pdf_path.name}")
                    self._update_worker_activity()
                    
                    # Create a progress callback to keep activity updated
                    def activity_callback():
                        self._update_worker_activity()
                    
                    receipt_count = process_pdf_files([pdf_path], output_dir, self.config, self.vendor_map)
                    
                    self._update_worker_activity()
                    get_logger().debug(f"Finished process_pdf_files for {pdf_path.name}, got {receipt_count} receipts")
                    
                    if receipt_count > 0:
                        success_count += 1
                        total_receipts += receipt_count
                        self.worker_queue.put(("detail", f"✅ {pdf_path.name}: {receipt_count} receipts extracted"))
                    else:
                        self.worker_queue.put(("detail", f"⚠️ {pdf_path.name}: No receipts found"))
                        
                except Exception as e:
                    import traceback
                    error_msg = f"❌ Error processing {pdf_path.name}: {str(e)}"
                    tb = traceback.format_exc()
                    get_logger().error(f"{error_msg}\nTraceback: {tb}")
                    self.worker_queue.put(("detail", error_msg))
            
            # Check for final cancellation
            with self.state_lock:
                cancelled = self.cancel_processing
            if cancelled:
                self.worker_queue.put(("cancelled", None))
                return
            
            # Send completion summary
            summary = {
                "total_files": len(pdf_files),
                "success_files": success_count,
                "total_receipts": total_receipts,
                "output_dir": output_dir
            }
            
            self.worker_queue.put(("done", summary))
            get_logger().debug("Worker process completed successfully")
            
        except Exception as e:
            import traceback
            error_msg = f"Critical error during processing: {str(e)}"
            tb = traceback.format_exc()
            get_logger().error(f"{error_msg}\nTraceback: {tb}")
            self.worker_queue.put(("error", {"message": error_msg, "show_dialog": True}))
        finally:
            get_logger().debug("Worker process finished (finally block)")

    def check_processing_status(self):
        """Check if processing is still running and update UI accordingly."""
        with self.state_lock:
            is_proc = self.is_processing
            
        if not is_proc:
            return
        
        try:
            # Check if the thread is still alive
            if self.processing_thread and self.processing_thread.is_alive():
                # Schedule another check
                self.root.after(500, self.check_processing_status)
            else:
                # Processing has finished or been cancelled
                # But don't change state here - let the completion handlers do it
                pass
        except Exception as e:
            get_logger().warn(f"Error checking processing status: {e}")
    
    def on_closing(self):
        """Handle window closing event."""
        # Check if processing is running
        with self.state_lock:
            is_proc = self.is_processing
            
        if is_proc:
            result = messagebox.askquestion(
                "Processing in Progress",
                "Processing is still running. Do you want to cancel it and exit?",
                icon='warning'
            )
            if result != 'yes':
                return
            
            # Cancel processing
            self.stop_processing()
            
            # Give it a moment to cancel gracefully
            if self.processing_thread and self.processing_thread.is_alive():
                self.processing_thread.join(timeout=2.0)
        
        # Save configuration
        try:
            self.update_config_from_gui()
            save_config(self.config)
            save_vendor_map(self.vendor_map)
        except Exception:
            pass  # Don't prevent closing if save fails
            
        self.root.quit()
    
    def run(self):
        """Start the GUI application."""
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self.on_closing()
