"""Main GUI application using Tkinter with tabbed interface."""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
from pathlib import Path
from typing import Optional

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
        
        # Application state
        self.config = load_config()
        self.vendor_map = load_vendor_map()
        self.log_stream = LogStream()
        self.processing_thread: Optional[threading.Thread] = None
        self.is_processing = False
        self.cancel_processing = False
        self.progress_count = 0
        self.total_count = 0
        
        # Initialize logging with GUI stream
        init_logger(log_stream=self.log_stream)
        
        # Setup GUI
        self.setup_gui()
        self.setup_menu()
        
        # Configure window closing
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Setup periodic UI updates to keep the GUI responsive
        self.setup_keep_alive()
    
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
        
        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Check Dependencies", command=self.check_dependencies)
        tools_menu.add_command(label="Clear All Logs", command=self.clear_logs)
        
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
    
    def update_progress_indicator(self):
        """Update the progress indicator during processing."""
        if hasattr(self, 'progress_count') and hasattr(self, 'total_count'):
            if self.total_count > 0:
                progress_text = f"Processing file {self.progress_count}/{self.total_count}"
                self.status_var.set(progress_text)
                
                # Update progress in input_run tab if it exists
                if 'input_run' in self.tabs:
                    progress_pct = (self.progress_count / self.total_count) * 100
                    self.tabs['input_run'].update_progress(progress_pct, progress_text)
    
    def load_config_file(self):
        """Load configuration from file."""
        filename = filedialog.askopenfilename(
            title="Load Configuration",
            filetypes=[("YAML files", "*.yaml *.yml"), ("All files", "*.*")]
        )
        
        if filename:
            def load_operation():
                try:
                    return load_config(Path(filename)), None
                except Exception as e:
                    return None, e
            
            def done_callback(result, error):
                if error:
                    messagebox.showerror("Error", f"Failed to load configuration:\n{error}")
                else:
                    self.config = result
                    self.update_gui_from_config()
                    messagebox.showinfo("Success", f"Configuration loaded from {filename}")
            
            # Run the operation with a busy indicator
            run_with_busy_indicator(
                self.root,
                operation=load_operation,
                text="Loading configuration...",
                done_callback=done_callback
            )
    
    def save_config_file(self):
        """Save configuration to file."""
        filename = filedialog.asksaveasfilename(
            title="Save Configuration",
            defaultextension=".yaml",
            filetypes=[("YAML files", "*.yaml"), ("All files", "*.*")]
        )
        
        if filename:
            # Update config from GUI before saving
            self.update_config_from_gui()
            
            def save_operation():
                try:
                    save_config(self.config, Path(filename))
                    return True, None
                except Exception as e:
                    return False, e
            
            def done_callback(result, error):
                if error:
                    messagebox.showerror("Error", f"Failed to save configuration:\n{error}")
                else:
                    messagebox.showinfo("Success", f"Configuration saved to {filename}")
            
            # Run the operation with a busy indicator
            run_with_busy_indicator(
                self.root,
                operation=save_operation,
                text="Saving configuration...",
                done_callback=done_callback
            )
    
    def check_dependencies(self):
        """Check and display dependency status."""
        from ..core.processing import check_processing_requirements
        
        def check_operation():
            try:
                return check_processing_requirements(self.config), None
            except Exception as e:
                return None, e
        
        def done_callback(result, error):
            if error:
                messagebox.showerror("Error", f"Error checking dependencies:\n{error}")
            else:
                requirements_met, errors = result
                if requirements_met:
                    messagebox.showinfo("Dependencies", "All required dependencies are available.")
                else:
                    error_msg = "Missing dependencies:\n\n" + "\n".join(f"• {error}" for error in errors)
                    messagebox.showerror("Dependencies", error_msg)
        
        # Run the operation with a busy indicator
        run_with_busy_indicator(
            self.root,
            operation=check_operation,
            text="Checking dependencies...",
            done_callback=done_callback
        )
    
    def clear_logs(self):
        """Clear all log entries."""
        self.log_stream.clear()
        if 'logs' in self.tabs:
            self.tabs['logs'].refresh_display()
        messagebox.showinfo("Logs", "All logs cleared.")
    
    def show_about(self):
        """Show about dialog."""
        about_text = """Receipt Analyzer v1.0.0

A comprehensive receipt detection and processing application

Features:
• PDF processing with embedded image extraction
• OpenCV-based receipt detection
• OCR with automatic orientation detection
• Smart parsing for vendor, amount, and date
• Self-learning vendor mapping system
• Multiple output formats and CSV reports

Built with Python, PyMuPDF, Tesseract OCR, OpenCV, and Tkinter."""
        
        messagebox.showinfo("About Receipt Analyzer", about_text)
    
    def update_gui_from_config(self):
        """Update GUI controls from current configuration."""
        for tab in self.tabs.values():
            if hasattr(tab, 'update_from_config'):
                tab.update_from_config()
    
    def update_config_from_gui(self):
        """Update configuration from GUI controls."""
        for tab in self.tabs.values():
            if hasattr(tab, 'update_config'):
                tab.update_config()
    
    def set_processing_state(self, is_processing: bool):
        """Update the processing state and UI."""
        try:
            self.is_processing = is_processing
            
            # Update status
            if is_processing:
                self.status_var.set("Processing...")
            else:
                self.status_var.set("Ready")
                
                # Reset cursor
                self.root.config(cursor="")
                for tab in self.tabs.values():
                    if hasattr(tab, 'frame'):
                        tab.frame.config(cursor="")
            
            # Update tabs
            for tab in self.tabs.values():
                if hasattr(tab, 'set_processing_state'):
                    tab.set_processing_state(is_processing)
                    
        except Exception as e:
            # If state setting fails, log but don't crash
            get_logger().warn(f"Error setting processing state: {e}")
            # Ensure we at least set the basic state
            self.is_processing = is_processing
    
    def start_processing(self, input_dir: Path, output_dir: Path):
        """Start processing in a separate thread."""
        if self.is_processing:
            return
        
        # Reset cancellation flag
        self.cancel_processing = False
        
        # Set progress counters
        self.progress_count = 0
        self.total_count = 0
        
        # Count PDF files for progress tracking
        try:
            from ..core.pdf_io import find_pdf_files
            pdf_files = find_pdf_files(input_dir)
            self.total_count = len(pdf_files)
        except Exception:
            self.total_count = 0

        # Update config from GUI BEFORE starting the background thread
        self.update_config_from_gui()
        
        self.set_processing_state(True)
        
        # Show busy cursor for the entire application
        self.root.config(cursor="watch")
        for tab in self.tabs.values():
            if hasattr(tab, 'frame'):
                tab.frame.config(cursor="watch")
        
        # Create and start processing thread
        self.processing_thread = threading.Thread(
            target=self._process_files,
            args=(input_dir, output_dir),
            daemon=True
        )
        self.processing_thread.start()
        
        # Show processing status dialog (with error handling)
        try:
            self.processing_dialog = ProcessingStatusDialog(self.root, self)
            self.processing_dialog.show()
            
            # Update processing dialog
            self.root.after(1000, self.check_processing_status)
        except Exception as e:
            # If dialog fails, continue without it but log the error
            get_logger().warn(f"Failed to create processing dialog: {e}")
            self.processing_dialog = None
    
    def stop_processing(self):
        """Stop the current processing."""
        if not self.is_processing:
            return
            
        self.cancel_processing = True
        
        # Update UI to indicate cancellation is in progress
        self.status_var.set("Cancelling processing...")
        if 'input_run' in self.tabs:
            self.tabs['input_run'].progress_text_var.set("Cancelling...")
        
        # Show an info message about cancellation
        messagebox.showinfo(
            "Cancelling", 
            "Processing will be cancelled after the current file completes.\n"
            "Please wait a moment..."
        )
    
    def check_processing_status(self):
        """Check if processing is still running and update UI accordingly."""
        if not self.is_processing:
            return
        
        try:
            # Check if the thread is still alive
            if self.processing_thread and self.processing_thread.is_alive():
                # Schedule another check
                self.root.after(500, self.check_processing_status)
            else:
                # Processing has finished or been cancelled
                self.root.after(0, lambda: self.set_processing_state(False))
                
                # Restore normal cursor
        except Exception as e:
            # If status checking fails, try to clean up gracefully
            get_logger().warn(f"Error in processing status check: {e}")
            self.root.after(0, lambda: self.set_processing_state(False))
            self.root.config(cursor="")
            for tab in self.tabs.values():
                if hasattr(tab, 'frame'):
                    tab.frame.config(cursor="")
    
    def _process_files(self, input_dir: Path, output_dir: Path):
        """Process files in background thread."""
        try:
            from ..core.processing import process_pdf_files
            from ..core.pdf_io import find_pdf_files
            
            # Find PDF files
            pdf_files = find_pdf_files(input_dir)
            if not pdf_files:
                self.root.after(0, lambda: get_logger().warn(f"No PDF files found in {input_dir}"))
                self.root.after(0, lambda: messagebox.showwarning("No PDFs", f"No PDF files found in {input_dir}"))
                self.root.after(0, lambda: self.set_processing_state(False))
                return
            
            # Set initial status
            self.root.after(0, lambda: self.status_var.set(f"Processing {len(pdf_files)} PDF files..."))
            
            # Add initial status to dialog if it exists
            if hasattr(self, 'processing_dialog') and self.processing_dialog and self.processing_dialog.dialog:
                self.root.after(0, lambda: self.processing_dialog.add_detail(f"Found {len(pdf_files)} PDF files to process"))
            
            # Process files with exception handling for each file
            total_receipts = 0
            success_count = 0
            
            for i, pdf_path in enumerate(pdf_files):
                # Check for cancellation
                if self.cancel_processing:
                    self.root.after(0, lambda: get_logger().info("Processing cancelled by user"))
                    
                    # Add cancellation status to dialog
                    if hasattr(self, 'processing_dialog') and self.processing_dialog and self.processing_dialog.dialog:
                        self.root.after(0, lambda: self.processing_dialog.add_detail("Processing cancelled by user"))
                        
                    break
                    
                try:
                    # Update progress counter
                    self.progress_count = i + 1
                    
                    # Add debug logging
                    self.root.after(0, lambda i=i, total=len(pdf_files), path=pdf_path: 
                                   get_logger().debug(f"Starting processing of file {i+1}/{total}: {path.name}"))
                    
                    # Update status on main thread
                    self.root.after(0, lambda i=i, total=len(pdf_files), 
                                    path=pdf_path: self.status_var.set(
                                    f"Processing file {i+1}/{total}: {path.name}"))
                    
                    # Update file info in dialog
                    if hasattr(self, 'processing_dialog') and self.processing_dialog and self.processing_dialog.dialog:
                        self.root.after(0, lambda path=pdf_path: self.processing_dialog.file_var.set(path.name))
                        self.root.after(0, lambda i=i, total=len(pdf_files): 
                                      self.processing_dialog.add_detail(f"Processing file {i+1}/{total}: {pdf_path.name}"))
                    
                    # Force GUI update before starting intensive processing
                    import time
                    time.sleep(0.1)  # Small delay to allow GUI updates
                    
                    # Log before processing starts
                    self.root.after(0, lambda path=pdf_path: 
                                   get_logger().debug(f"About to call process_pdf_files for {path.name}"))
                    
                    # Process file with better error handling
                    receipt_count = process_pdf_files([pdf_path], output_dir, self.config, self.vendor_map)
                    
                    # Log after processing completes
                    self.root.after(0, lambda path=pdf_path, count=receipt_count: 
                                   get_logger().debug(f"process_pdf_files completed for {path.name}, found {count} receipts"))
                    
                    if receipt_count > 0:
                        success_count += 1
                        total_receipts += receipt_count
                        
                        # Add success status to dialog
                        if hasattr(self, 'processing_dialog') and self.processing_dialog and self.processing_dialog.dialog:
                            self.root.after(0, lambda path=pdf_path, count=receipt_count: 
                                          self.processing_dialog.add_detail(f"Extracted {count} receipts from {path.name}"))
                except Exception as e:
                    # Log error but continue with next file
                    self.root.after(0, lambda pdf=pdf_path, err=e: get_logger().fail(
                        f"Failed to process {pdf.name}: {err}"))
                        
                    # Add error status to dialog
                    if hasattr(self, 'processing_dialog') and self.processing_dialog and self.processing_dialog.dialog:
                        self.root.after(0, lambda pdf=pdf_path, err=e: 
                                      self.processing_dialog.add_detail(f"Error processing {pdf.name}: {err}"))
            
            # Skip completion message if cancelled
            if not self.cancel_processing:
                # Show completion message on main thread
                self.root.after(0, lambda: messagebox.showinfo(
                    "Processing Complete", 
                    f"Processing completed!\n\n"
                    f"Files processed: {success_count}/{len(pdf_files)}\n"
                    f"Total receipts: {total_receipts}\n"
                    f"Output saved to: {output_dir}"
                ))
            else:
                # Show cancellation message
                self.root.after(0, lambda: messagebox.showinfo(
                    "Processing Cancelled", 
                    f"Processing was cancelled.\n\n"
                    f"Files processed: {success_count}/{len(pdf_files)}\n"
                    f"Total receipts: {total_receipts}\n"
                    f"Output saved to: {output_dir}"
                ))
        
        except Exception as e:
            # Show error on main thread
            self.root.after(0, lambda err=e: messagebox.showerror(
                "Processing Error", 
                f"An error occurred during processing:\n\n{err}"
            ))
        
        finally:
            # Reset processing state on main thread
            self.root.after(0, lambda: self.set_processing_state(False))
    
    def on_closing(self):
        """Handle application closing."""
        if self.is_processing:
            response = messagebox.askyesnocancel(
                "Quit", 
                "Processing is in progress.\n\n"
                "• Click 'Yes' to cancel processing and quit\n"
                "• Click 'No' to quit immediately (may cause data loss)\n"
                "• Click 'Cancel' to return to the application",
                icon=messagebox.WARNING
            )
            
            if response is None:  # Cancel
                return
                
            if response:  # Yes - cancel and quit
                self.cancel_processing = True
                self.status_var.set("Cancelling and preparing to exit...")
                
                # Give the processing a moment to respond to cancellation
                def delayed_quit():
                    # Save configuration and vendor map
                    try:
                        self.update_config_from_gui()
                        save_config(self.config)
                        save_vendor_map(self.vendor_map)
                    except Exception:
                        pass  # Don't prevent closing if save fails
                    
                    self.root.quit()
                
                self.root.after(1000, delayed_quit)
                return
                
            # No - force quit immediately
            self.root.quit()
        else:
            # Save configuration and vendor map
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