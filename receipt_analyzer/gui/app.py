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
        
        # Initialize logging with GUI stream
        init_logger(log_stream=self.log_stream)
        
        # Setup GUI
        self.setup_gui()
        self.setup_menu()
        
        # Configure window closing
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
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
    
    def load_config_file(self):
        """Load configuration from file."""
        filename = filedialog.askopenfilename(
            title="Load Configuration",
            filetypes=[("YAML files", "*.yaml *.yml"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                self.config = load_config(Path(filename))
                self.update_gui_from_config()
                messagebox.showinfo("Success", f"Configuration loaded from {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load configuration:\n{e}")
    
    def save_config_file(self):
        """Save configuration to file."""
        filename = filedialog.asksaveasfilename(
            title="Save Configuration",
            defaultextension=".yaml",
            filetypes=[("YAML files", "*.yaml"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                self.update_config_from_gui()
                save_config(self.config, Path(filename))
                messagebox.showinfo("Success", f"Configuration saved to {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save configuration:\n{e}")
    
    def check_dependencies(self):
        """Check and display dependency status."""
        from ..core.processing import check_processing_requirements
        
        requirements_met, errors = check_processing_requirements(self.config)
        
        if requirements_met:
            messagebox.showinfo("Dependencies", "All required dependencies are available.")
        else:
            error_msg = "Missing dependencies:\n\n" + "\n".join(f"• {error}" for error in errors)
            messagebox.showerror("Dependencies", error_msg)
    
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
        self.is_processing = is_processing
        
        # Update status
        if is_processing:
            self.status_var.set("Processing...")
        else:
            self.status_var.set("Ready")
        
        # Update tabs
        for tab in self.tabs.values():
            if hasattr(tab, 'set_processing_state'):
                tab.set_processing_state(is_processing)
    
    def start_processing(self, input_dir: Path, output_dir: Path):
        """Start processing in a separate thread."""
        if self.is_processing:
            return
        
        self.set_processing_state(True)
        
        # Create and start processing thread
        self.processing_thread = threading.Thread(
            target=self._process_files,
            args=(input_dir, output_dir),
            daemon=True
        )
        self.processing_thread.start()
    
    def stop_processing(self):
        """Stop the current processing (not implemented - would need process cancellation)."""
        # Note: Actual implementation would require thread-safe cancellation mechanism
        messagebox.showwarning("Stop Processing", "Processing cannot be stopped once started.")
    
    def _process_files(self, input_dir: Path, output_dir: Path):
        """Process files in background thread."""
        try:
            from ..core.processing import process_pdf_files
            from ..core.pdf_io import find_pdf_files
            
            # Update config from GUI before starting processing
            self.update_config_from_gui()
            
            # Find PDF files
            pdf_files = find_pdf_files(input_dir)
            if not pdf_files:
                self.root.after(0, lambda: get_logger().warn(f"No PDF files found in {input_dir}"))
                self.root.after(0, lambda: messagebox.showwarning("No PDFs", f"No PDF files found in {input_dir}"))
                self.root.after(0, lambda: self.set_processing_state(False))
                return
            
            # Set initial status
            self.root.after(0, lambda: self.status_var.set(f"Processing {len(pdf_files)} PDF files..."))
            
            # Process files with exception handling for each file
            total_receipts = 0
            success_count = 0
            
            for i, pdf_path in enumerate(pdf_files):
                try:
                    # Update status on main thread
                    self.root.after(0, lambda i=i, total=len(pdf_files), 
                                    path=pdf_path: self.status_var.set(
                                    f"Processing file {i+1}/{total}: {path.name}"))
                    
                    # Process file
                    receipt_count = process_pdf_files([pdf_path], output_dir, self.config, self.vendor_map)
                    
                    if receipt_count > 0:
                        success_count += 1
                        total_receipts += receipt_count
                except Exception as e:
                    # Log error but continue with next file
                    self.root.after(0, lambda pdf=pdf_path, err=e: get_logger().fail(
                        f"Failed to process {pdf.name}: {err}"))
            
            # Show completion message on main thread
            self.root.after(0, lambda: messagebox.showinfo(
                "Processing Complete", 
                f"Processing completed!\n\n"
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
            if messagebox.askokcancel("Quit", "Processing is in progress. Really quit?"):
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