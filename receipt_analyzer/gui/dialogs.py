"""Dialog boxes for Receipt Analyzer GUI."""

import tkinter as tk
from tkinter import ttk
import threading
import time


class ProcessingStatusDialog:
    """Dialog showing processing status and allowing cancellation."""
    
    def __init__(self, parent, app):
        """Initialize the dialog."""
        self.parent = parent
        self.app = app
        self.dialog = None
    # No update thread; all updates are now done from the main thread via queue polling
        
    def show(self):
        """Show the dialog."""
        if self.dialog:
            return  # Dialog already showing

        # Create dialog window
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Processing Status")
        self.dialog.geometry("500x300")
        self.dialog.minsize(400, 250)
        self.dialog.transient(self.parent)
        # Optionally make modal, but do not use grab_set to avoid deadlocks with messageboxes
        self.dialog.focus_set()

        # Set position relative to parent
        parent_x = self.parent.winfo_rootx()
        parent_y = self.parent.winfo_rooty()
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()

        dialog_width = 500
        dialog_height = 300

        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2

        self.dialog.geometry(f"+{x}+{y}")

        # Set up UI
        self.setup_ui()

        # Handle close button
        self.dialog.protocol("WM_DELETE_WINDOW", self.on_close)

        # No update thread; dialog is updated from main thread via queue polling
        
    def setup_ui(self):
        """Set up the dialog UI."""
        main_frame = ttk.Frame(self.dialog, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(
            main_frame, 
            text="Processing Files", 
            font=("Arial", 14, "bold")
        )
        title_label.pack(pady=(0, 20))
        
        # Progress frame
        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(fill=tk.X, pady=10)
        
        # Overall progress
        ttk.Label(progress_frame, text="Overall Progress:").pack(anchor=tk.W)
        
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(
            progress_frame, 
            variable=self.progress_var,
            mode="determinate",
            length=400
        )
        self.progress_bar.pack(fill=tk.X, pady=5)
        
        self.status_var = tk.StringVar(value="Starting...")
        status_label = ttk.Label(progress_frame, textvariable=self.status_var)
        status_label.pack(anchor=tk.W, pady=5)
        
        # File progress
        ttk.Label(progress_frame, text="Current File:").pack(anchor=tk.W, pady=(10, 0))
        
        self.file_var = tk.StringVar(value="")
        file_label = ttk.Label(progress_frame, textvariable=self.file_var)
        file_label.pack(anchor=tk.W, pady=5)
        
        # Details frame
        details_frame = ttk.LabelFrame(main_frame, text="Details")
        details_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Create text widget with scrollbar
        text_frame = ttk.Frame(details_frame)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.details_text = tk.Text(
            text_frame, 
            height=6, 
            wrap=tk.WORD,
            state=tk.DISABLED,
            font=("Consolas", 9)
        )
        
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.details_text.yview)
        self.details_text.configure(yscrollcommand=scrollbar.set)
        
        self.details_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        self.cancel_button = ttk.Button(
            button_frame, 
            text="Cancel Processing",
            command=self.cancel_processing
        )
        self.cancel_button.pack(side=tk.RIGHT)
        
    def add_detail(self, message):
        """Add a detail message to the text widget."""
        if not self.dialog or not self.details_text:
            return
            
        try:
            self.details_text.config(state=tk.NORMAL)
            self.details_text.insert(tk.END, message + "\n")
            self.details_text.see(tk.END)
            self.details_text.config(state=tk.DISABLED)
        except tk.TclError:
            # Dialog might be destroyed
            pass
    
    # No update_loop needed; dialog is updated from main thread via queue polling
    
    def cancel_processing(self):
        """Cancel the processing operation."""
        if self.app.is_processing:
            self.app.stop_processing()
            self.cancel_button.config(state=tk.DISABLED)
            self.status_var.set("Cancelling...")
            
    def on_close(self):
        """Handle dialog close button."""
        if self.app.is_processing:
            self.cancel_processing()
        self.close()
            
    def close(self):
        """Close the dialog."""
        self.should_close = True
        
        if self.dialog:
            try:
                self.dialog.grab_release()
                self.dialog.destroy()
            except tk.TclError:
                # Dialog might already be destroyed
                pass
                
        self.dialog = None
