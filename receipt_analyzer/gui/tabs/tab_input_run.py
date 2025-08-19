"""Input & Run tab for selecting directories and controlling processing."""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import os


class InputRunTab:
    """Input & Run tab for the Receipt Analyzer GUI."""
    
    def __init__(self, parent, app):
        self.parent = parent
        self.app = app
        
        # Create main frame
        self.frame = ttk.Frame(parent)
        
        # Variables
        self.input_dir_var = tk.StringVar()
        self.output_dir_var = tk.StringVar()
        self.progress_var = tk.DoubleVar()
        self.progress_text_var = tk.StringVar()
        self.progress_text_var.set("Ready to process")
        
        # Setup GUI
        self.setup_gui()
    
    def setup_gui(self):
        """Setup the tab GUI."""
        # Title
        title_label = ttk.Label(self.frame, text="Input & Run", font=("Arial", 14, "bold"))
        title_label.pack(pady=(10, 20))
        
        # Input section
        input_frame = ttk.LabelFrame(self.frame, text="Input Settings", padding=10)
        input_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Input directory
        ttk.Label(input_frame, text="Input Directory (PDFs):").pack(anchor=tk.W)
        
        input_dir_frame = ttk.Frame(input_frame)
        input_dir_frame.pack(fill=tk.X, pady=(5, 10))
        
        self.input_dir_entry = ttk.Entry(input_dir_frame, textvariable=self.input_dir_var)
        self.input_dir_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        ttk.Button(
            input_dir_frame, text="Browse...", 
            command=self.browse_input_dir
        ).pack(side=tk.RIGHT, padx=(5, 0))
        
        # Output directory
        ttk.Label(input_frame, text="Output Directory:").pack(anchor=tk.W)
        
        output_dir_frame = ttk.Frame(input_frame)
        output_dir_frame.pack(fill=tk.X, pady=5)
        
        self.output_dir_entry = ttk.Entry(output_dir_frame, textvariable=self.output_dir_var)
        self.output_dir_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        ttk.Button(
            output_dir_frame, text="Browse...", 
            command=self.browse_output_dir
        ).pack(side=tk.RIGHT, padx=(5, 0))
        
        # Control section
        control_frame = ttk.LabelFrame(self.frame, text="Processing Control", padding=10)
        control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Buttons
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(fill=tk.X, pady=5)
        
        self.run_button = ttk.Button(
            button_frame, text="Run Processing", 
            command=self.start_processing
        )
        self.run_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.stop_button = ttk.Button(
            button_frame, text="Stop", 
            command=self.stop_processing, 
            state=tk.DISABLED
        )
        self.stop_button.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(
            button_frame, text="Open Output", 
            command=self.open_output_dir
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        # Progress section
        progress_frame = ttk.LabelFrame(self.frame, text="Progress", padding=10)
        progress_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Progress bar
        self.progress_bar = ttk.Progressbar(
            progress_frame, variable=self.progress_var, 
            mode='determinate', maximum=100.0
        )
        self.progress_bar.pack(fill=tk.X, pady=5)
        
        # Progress text
        self.progress_label = ttk.Label(
            progress_frame, textvariable=self.progress_text_var
        )
        self.progress_label.pack(anchor=tk.W, pady=5)
        
        # Status text area
        status_frame = ttk.Frame(progress_frame)
        status_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.status_text = tk.Text(
            status_frame, height=8, wrap=tk.WORD, 
            state=tk.DISABLED, font=("Consolas", 9)
        )
        
        status_scrollbar = ttk.Scrollbar(status_frame, orient=tk.VERTICAL, command=self.status_text.yview)
        self.status_text.configure(yscrollcommand=status_scrollbar.set)
        
        self.status_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        status_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Set up log monitoring
        self.app.log_stream.add_listener(self.on_log_message)
        
        # Add throttling for log messages
        self.last_log_update = 0
        self.log_update_throttle = 0.5  # Only update GUI every 500ms for debug messages
        
        # Set default directories
        self.set_default_directories()
    
    def set_default_directories(self):
        """Set default input and output directories."""
        # Default to user's Documents folder or home directory
        home_dir = Path.home()
        
        # Try to find a good default input directory
        possible_inputs = [
            home_dir / "Documents" / "Receipts",
            home_dir / "Documents",
            home_dir / "Downloads",
            home_dir
        ]
        
        for dir_path in possible_inputs:
            if dir_path.exists():
                self.input_dir_var.set(str(dir_path))
                break
        
        # Default output directory
        output_dir = home_dir / "Documents" / "Receipt_Output"
        self.output_dir_var.set(str(output_dir))
    
    def browse_input_dir(self):
        """Browse for input directory."""
        directory = filedialog.askdirectory(
            title="Select Input Directory (containing PDFs)",
            initialdir=self.input_dir_var.get() or Path.home()
        )
        
        if directory:
            self.input_dir_var.set(directory)
    
    def browse_output_dir(self):
        """Browse for output directory."""
        directory = filedialog.askdirectory(
            title="Select Output Directory",
            initialdir=self.output_dir_var.get() or Path.home()
        )
        
        if directory:
            self.output_dir_var.set(directory)
    
    def validate_directories(self) -> tuple[bool, str]:
        """Validate input and output directories."""
        input_dir = self.input_dir_var.get().strip()
        output_dir = self.output_dir_var.get().strip()
        
        if not input_dir:
            return False, "Please select an input directory"
        
        if not output_dir:
            return False, "Please select an output directory"
        
        input_path = Path(input_dir)
        if not input_path.exists():
            return False, f"Input directory does not exist: {input_dir}"
        
        if not input_path.is_dir():
            return False, f"Input path is not a directory: {input_dir}"
        
        # Check for PDF files in input directory
        from ...core.pdf_io import find_pdf_files
        pdf_files = find_pdf_files(input_path)
        if not pdf_files:
            return False, f"No PDF files found in input directory: {input_dir}"
        
        return True, f"Found {len(pdf_files)} PDF files to process"
    
    def start_processing(self):
        """Start the processing operation."""
        # Validate directories
        is_valid, message = self.validate_directories()
        if not is_valid:
            messagebox.showerror("Validation Error", message)
            return
        
        # Create output directory if it doesn't exist
        output_path = Path(self.output_dir_var.get())
        try:
            output_path.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            messagebox.showerror("Error", f"Could not create output directory:\n{e}")
            return
        
        # Clear status display and reset progress
        self.clear_status()
        self.progress_var.set(0)
        self.progress_bar["value"] = 0
        self.progress_text_var.set("Starting processing...")
        
        # Show busy cursor for this tab
        self.frame.config(cursor="watch")
        
        # Start processing via app
        self.app.start_processing(Path(self.input_dir_var.get()), output_path)
    
    def stop_processing(self):
        """Stop the current processing."""
        self.progress_text_var.set("Cancelling processing...")
        self.app.stop_processing()
    
    def open_output_dir(self):
        """Open the output directory in the file manager."""
        output_dir = self.output_dir_var.get().strip()
        if not output_dir:
            messagebox.showwarning("No Directory", "No output directory selected")
            return
        
        output_path = Path(output_dir)
        if not output_path.exists():
            messagebox.showwarning("Directory Not Found", f"Output directory does not exist: {output_dir}")
            return
        
        # Open directory in file manager (cross-platform)
        try:
            if os.name == 'nt':  # Windows
                os.startfile(output_path)
            elif os.name == 'posix':  # macOS and Linux
                import subprocess
                if 'darwin' in os.sys.platform:  # macOS
                    subprocess.run(['open', str(output_path)])
                else:  # Linux
                    subprocess.run(['xdg-open', str(output_path)])
        except Exception as e:
            messagebox.showerror("Error", f"Could not open directory:\n{e}")
    
    def clear_status(self):
        """Clear the status text display."""
        self.status_text.config(state=tk.NORMAL)
        self.status_text.delete(1.0, tk.END)
        self.status_text.config(state=tk.DISABLED)
    
    def on_log_message(self, log_record):
        """Handle new log messages with throttling to prevent GUI overload."""
        import time
        current_time = time.time()
        
        # Only process important messages immediately
        is_important = log_record.level in ['INFO', 'SUCCESS', 'WARN', 'FAIL']
        
        # Throttle debug messages to prevent GUI overload
        if not is_important and (current_time - self.last_log_update) < self.log_update_throttle:
            return
            
        self.last_log_update = current_time
        
        # Update status display on main thread
        self.app.root.after(0, lambda: self._add_status_message(str(log_record)))
        
        # Update progress text for important messages
        if log_record.level in ['INFO', 'SUCCESS']:
            self.app.root.after(0, lambda: self.progress_text_var.set(log_record.message))
    
    def _add_status_message(self, message):
        """Add a message to the status display."""
        self.status_text.config(state=tk.NORMAL)
        self.status_text.insert(tk.END, message + '\n')
        self.status_text.see(tk.END)
        self.status_text.config(state=tk.DISABLED)
    
    def set_processing_state(self, is_processing: bool):
        """Update the processing state."""
        if is_processing:
            self.run_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.progress_bar["value"] = 0
            self.progress_bar["mode"] = "determinate"
            
            # Disable input fields during processing
            self.input_dir_entry.config(state=tk.DISABLED)
            self.output_dir_entry.config(state=tk.DISABLED)
        else:
            self.run_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.progress_bar["value"] = 0
            self.progress_text_var.set("Processing complete")
            
            # Re-enable input fields
            self.input_dir_entry.config(state=tk.NORMAL)
            self.output_dir_entry.config(state=tk.NORMAL)
    
    def update_progress(self, percentage, message=None):
        """Update the progress bar and message."""
        try:
            self.progress_var.set(percentage)
            self.progress_bar["value"] = percentage
            
            if message:
                self.progress_text_var.set(message)
                
            # Force update of progress UI
            self.progress_bar.update_idletasks()
            self.progress_label.update_idletasks()
        except Exception:
            # Ignore errors during UI updates
            pass
    
    def update_from_config(self):
        """Update GUI from configuration."""
        # This tab doesn't have config-specific settings
        pass
    
    def update_config(self):
        """Update configuration from GUI."""
        # This tab doesn't modify config directly
        pass