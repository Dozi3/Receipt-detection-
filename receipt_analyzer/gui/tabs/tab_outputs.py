"""Outputs settings tab."""

import tkinter as tk
from tkinter import ttk, messagebox
import os
from pathlib import Path


class OutputsTab:
    """Outputs settings tab."""
    
    def __init__(self, parent, app):
        self.parent = parent
        self.app = app
        
        # Create main frame
        self.frame = ttk.Frame(parent)
        
        # Variables
        self.format_var = tk.StringVar(value="png")
        self.jpeg_quality_var = tk.IntVar(value=85)
        self.per_page_zip_var = tk.BooleanVar(value=False)
        self.max_edge_var = tk.IntVar(value=1000)
        
        # Setup GUI
        self.setup_gui()
    
    def setup_gui(self):
        """Setup the tab GUI."""
        # Title
        title_label = ttk.Label(self.frame, text="Output Settings", font=("Arial", 14, "bold"))
        title_label.pack(pady=(10, 20))
        
        # Format settings
        format_frame = ttk.LabelFrame(self.frame, text="Image Format", padding=10)
        format_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Radiobutton(
            format_frame, text="PNG (lossless, larger files)", 
            variable=self.format_var, value="png"
        ).pack(anchor=tk.W, pady=2)
        
        ttk.Radiobutton(
            format_frame, text="JPEG (compressed, smaller files)", 
            variable=self.format_var, value="jpeg"
        ).pack(anchor=tk.W, pady=2)
        
        # JPEG quality
        quality_frame = ttk.Frame(format_frame)
        quality_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(quality_frame, text="JPEG Quality:", width=15).pack(side=tk.LEFT)
        
        quality_scale = ttk.Scale(
            quality_frame, from_=1, to=100, 
            variable=self.jpeg_quality_var, orient=tk.HORIZONTAL
        )
        quality_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        self.quality_label = ttk.Label(quality_frame, text="85", width=3)
        self.quality_label.pack(side=tk.RIGHT)
        
        # Update quality label
        quality_scale.configure(command=self.update_quality_label)
        
        # Size settings
        size_frame = ttk.LabelFrame(self.frame, text="Image Size", padding=10)
        size_frame.pack(fill=tk.X, padx=10, pady=5)
        
        max_edge_frame = ttk.Frame(size_frame)
        max_edge_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(max_edge_frame, text="Max Edge (pixels):", width=15).pack(side=tk.LEFT)
        
        ttk.Entry(max_edge_frame, textvariable=self.max_edge_var, width=10).pack(side=tk.LEFT, padx=(5, 10))
        
        ttk.Label(max_edge_frame, text="Maximum width or height for output images", foreground="blue").pack(side=tk.LEFT)
        
        # Archive settings
        archive_frame = ttk.LabelFrame(self.frame, text="Archive Options", padding=10)
        archive_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Checkbutton(
            archive_frame, text="Create per-page ZIP files",
            variable=self.per_page_zip_var
        ).pack(anchor=tk.W, pady=5)
        
        ttk.Label(
            archive_frame, 
            text="When enabled, all receipts from each page are packaged into a ZIP file",
            foreground="blue"
        ).pack(anchor=tk.W, padx=20)
        
        # Output files info
        files_frame = ttk.LabelFrame(self.frame, text="Generated Files", padding=10)
        files_frame.pack(fill=tk.X, padx=10, pady=5)
        
        files_info = [
            "Receipt images: Vendor_GBP-amount_date.png/jpg",
            "freeagent.csv: For accounting software import",
            "receipts_index.csv: Detailed processing index",
            "processing_summary.csv: Statistics and summary",
            "processing.log: Detailed processing log",
            "page_N.zip: Per-page archives (if enabled)"
        ]
        
        for info in files_info:
            ttk.Label(files_frame, text=f"• {info}", foreground="blue").pack(anchor=tk.W, padx=10, pady=1)
        
        # Quick actions
        actions_frame = ttk.LabelFrame(self.frame, text="Quick Actions", padding=10)
        actions_frame.pack(fill=tk.X, padx=10, pady=5)
        
        actions_buttons = ttk.Frame(actions_frame)
        actions_buttons.pack()
        
        ttk.Button(
            actions_buttons, text="Open FreeAgent CSV", 
            command=self.open_freeagent_csv
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            actions_buttons, text="Open Receipts Index", 
            command=self.open_receipts_index
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            actions_buttons, text="Open Processing Log", 
            command=self.open_processing_log
        ).pack(side=tk.LEFT, padx=5)
    
    def update_quality_label(self, value):
        """Update the quality label."""
        self.quality_label.config(text=str(int(float(value))))
    
    def open_freeagent_csv(self):
        """Open the FreeAgent CSV file."""
        self._open_output_file("freeagent.csv")
    
    def open_receipts_index(self):
        """Open the receipts index CSV file."""
        self._open_output_file("receipts_index.csv")
    
    def open_processing_log(self):
        """Open the processing log file."""
        self._open_output_file("processing.log")
    
    def _open_output_file(self, filename):
        """Open an output file."""
        # Get output directory from input tab
        if 'input_run' in self.app.tabs:
            output_dir = self.app.tabs['input_run'].output_dir_var.get().strip()
            
            if not output_dir:
                messagebox.showwarning("No Output Directory", "No output directory selected.")
                return
            
            file_path = Path(output_dir) / filename
            
            if not file_path.exists():
                messagebox.showwarning("File Not Found", f"File does not exist: {filename}\\n\\nRun processing first.")
                return
            
            # Open file with system default application
            try:
                if os.name == 'nt':  # Windows
                    os.startfile(file_path)
                elif os.name == 'posix':  # macOS and Linux
                    import subprocess
                    if 'darwin' in os.sys.platform:  # macOS
                        subprocess.run(['open', str(file_path)])
                    else:  # Linux
                        subprocess.run(['xdg-open', str(file_path)])
            except Exception as e:
                messagebox.showerror("Error", f"Could not open file:\\n{e}")
        else:
            messagebox.showwarning("Error", "Cannot access output directory.")
    
    def update_from_config(self):
        """Update GUI from configuration."""
        config = self.app.config
        output = config.output
        
        self.format_var.set(output.format)
        self.jpeg_quality_var.set(output.jpeg_quality)
        self.per_page_zip_var.set(output.per_page_zip)
        self.max_edge_var.set(output.max_edge)
        
        # Update quality label
        self.quality_label.config(text=str(output.jpeg_quality))
    
    def update_config(self):
        """Update configuration from GUI."""
        config = self.app.config
        output = config.output
        
        output.format = self.format_var.get()
        output.jpeg_quality = self.jpeg_quality_var.get()
        output.per_page_zip = self.per_page_zip_var.get()
        output.max_edge = self.max_edge_var.get()