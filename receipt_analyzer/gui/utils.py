"""Utility functions and widgets for the GUI."""

import tkinter as tk
from tkinter import ttk
from typing import Optional, Callable
import time
import threading


class BusyIndicator:
    """A utility class to show a busy indicator during long operations."""
    
    def __init__(self, parent, text="Please wait..."):
        """Initialize the busy indicator."""
        self.parent = parent
        self.text = text
        self.overlay = None
        self.close_callback = None
        
    def show(self, text=None):
        """Show the busy indicator."""
        if text:
            self.text = text
            
        if self.overlay:
            return  # Already showing
            
        # Get parent dimensions
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()
        
        # Create overlay
        self.overlay = tk.Toplevel(self.parent)
        self.overlay.title("")
        self.overlay.transient(self.parent)
        
        # Remove window decorations
        self.overlay.overrideredirect(True)
        
        # Make semi-transparent
        self.overlay.attributes("-alpha", 0.85)
        
        # Position over parent
        x = self.parent.winfo_rootx()
        y = self.parent.winfo_rooty()
        self.overlay.geometry(f"{parent_width}x{parent_height}+{x}+{y}")
        
        # Fill with content
        frame = ttk.Frame(self.overlay, style="Busy.TFrame")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Create custom style
        style = ttk.Style()
        style.configure("Busy.TFrame", background="#f0f0f0")
        style.configure("Busy.TLabel", background="#f0f0f0", font=("Arial", 12))
        
        # Center content
        content_frame = ttk.Frame(frame, style="Busy.TFrame")
        content_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        
        # Add spinner (progress bar in indeterminate mode)
        spinner = ttk.Progressbar(
            content_frame, 
            mode="indeterminate", 
            length=200
        )
        spinner.pack(pady=10)
        spinner.start()
        
        # Add text
        label = ttk.Label(
            content_frame, 
            text=self.text,
            style="Busy.TLabel"
        )
        label.pack(pady=10)
        
        # Prevent interaction with parent
        self.overlay.grab_set()
        
    def hide(self):
        """Hide the busy indicator."""
        if self.overlay:
            try:
                self.overlay.grab_release()
                self.overlay.destroy()
            except tk.TclError:
                # Widget might already be destroyed
                pass
                
        self.overlay = None
        
        # Call the close callback if defined
        if self.close_callback:
            try:
                self.close_callback()
            except Exception:
                pass


def run_with_busy_indicator(parent, operation: Callable, text="Please wait...", 
                          done_callback: Optional[Callable] = None):
    """
    Run an operation with a busy indicator.
    
    Args:
        parent: The parent widget
        operation: The function to run
        text: The text to display
        done_callback: Function to call when operation completes
    """
    indicator = BusyIndicator(parent, text)
    
    def thread_func():
        try:
            result = operation()
            
            # Ensure we're on the main thread for UI updates
            parent.after(0, lambda: handle_completion(result))
        except Exception as e:
            # Handle exception
            parent.after(0, lambda: handle_completion(None, e))
    
    def handle_completion(result, error=None):
        # Hide the indicator
        indicator.hide()
        
        # Call the done callback if provided
        if done_callback:
            done_callback(result, error)
    
    # Show the indicator
    indicator.show()
    
    # Start the thread
    thread = threading.Thread(target=thread_func, daemon=True)
    thread.start()
    
    return indicator
