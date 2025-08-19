"""Logs display tab."""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
import pyperclip


class LogsTab:
    """Logs display tab."""
    
    def __init__(self, parent, app):
        self.parent = parent
        self.app = app
        
        # Create main frame
        self.frame = ttk.Frame(parent)
        
        # Variables
        self.filter_var = tk.StringVar(value="ALL")
        self.auto_scroll_var = tk.BooleanVar(value=True)
        
        # Setup GUI
        self.setup_gui()
        
        # Set up log monitoring
        self.app.log_stream.add_listener(self.on_log_message)
        
                # Add throttling for log messages to prevent GUI overload
        self.last_log_update = 0
        self.log_update_throttle = 0.5  # Only update GUI every 500ms for debug messages
        
        # Initial load
        self.refresh_display()
    
    def setup_gui(self):
        """Setup the tab GUI."""
        # Title
        title_label = ttk.Label(self.frame, text="Processing Logs", font=("Arial", 14, "bold"))
        title_label.pack(pady=(10, 20))
        
        # Controls frame
        controls_frame = ttk.Frame(self.frame)
        controls_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Filter
        filter_frame = ttk.LabelFrame(controls_frame, text="Filter", padding=5)
        filter_frame.pack(side=tk.LEFT, padx=(0, 10))
        
        filter_combo = ttk.Combobox(
            filter_frame, textvariable=self.filter_var,
            values=["ALL", "INFO", "WARN", "FAIL", "SUCCESS"],
            width=10, state="readonly"
        )
        filter_combo.pack()
        filter_combo.bind("<<ComboboxSelected>>", self.on_filter_change)
        
        # Auto-scroll
        ttk.Checkbutton(
            controls_frame, text="Auto-scroll", 
            variable=self.auto_scroll_var
        ).pack(side=tk.LEFT, padx=10)
        
        # Buttons
        buttons_frame = ttk.Frame(controls_frame)
        buttons_frame.pack(side=tk.RIGHT)
        
        ttk.Button(buttons_frame, text="Refresh", command=self.refresh_display).pack(side=tk.LEFT, padx=2)
        ttk.Button(buttons_frame, text="Clear", command=self.clear_logs).pack(side=tk.LEFT, padx=2)
        ttk.Button(buttons_frame, text="Copy All", command=self.copy_to_clipboard).pack(side=tk.LEFT, padx=2)
        ttk.Button(buttons_frame, text="Save As...", command=self.save_logs).pack(side=tk.LEFT, padx=2)
        
        # Log display
        log_frame = ttk.LabelFrame(self.frame, text="Log Messages", padding=5)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Text widget with scrollbar
        text_frame = ttk.Frame(log_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = tk.Text(
            text_frame, wrap=tk.WORD, 
            font=("Consolas", 9), state=tk.DISABLED
        )
        
        log_scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Configure text tags for different log levels
        self.log_text.tag_configure("INFO", foreground="black")
        self.log_text.tag_configure("SUCCESS", foreground="green")
        self.log_text.tag_configure("WARN", foreground="orange")
        self.log_text.tag_configure("FAIL", foreground="red")
        
        # Status
        status_frame = ttk.Frame(self.frame)
        status_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.status_var = tk.StringVar()
        self.status_var.set("No logs")
        ttk.Label(status_frame, textvariable=self.status_var, foreground="blue").pack(side=tk.LEFT)
    
    def on_filter_change(self, event=None):
        """Handle filter change."""
        self.refresh_display()
    
    def on_log_message(self, log_record):
        """Handle new log message with throttling to prevent GUI overload."""
        import time
        current_time = time.time()
        
        # Only process important messages immediately
        is_important = log_record.level in ['INFO', 'SUCCESS', 'WARN', 'FAIL']
        
        # Throttle debug messages to prevent GUI overload
        if not is_important and (current_time - self.last_log_update) < self.log_update_throttle:
            return
            
        self.last_log_update = current_time
        
        # Update display on main thread
        self.app.root.after(0, lambda: self._add_log_record(log_record))
    
    def _add_log_record(self, log_record):
        """Add a single log record to the display."""
        filter_level = self.filter_var.get()
        
        # Apply filter
        if filter_level != "ALL" and log_record.level != filter_level:
            return
        
        # Add to display
        self.log_text.config(state=tk.NORMAL)
        
        # Insert with appropriate tag
        text = str(log_record) + "\n"
        self.log_text.insert(tk.END, text, log_record.level)
        
        # Auto-scroll if enabled
        if self.auto_scroll_var.get():
            self.log_text.see(tk.END)
        
        self.log_text.config(state=tk.DISABLED)
        
        # Update status
        self._update_status()
    
    def refresh_display(self):
        """Refresh the entire log display."""
        # Clear display
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
        
        # Get filtered records
        filter_level = self.filter_var.get()
        if filter_level == "ALL":
            records = self.app.log_stream.get_records()
        else:
            records = self.app.log_stream.get_records(filter_level)
        
        # Add records to display
        if records:
            self.log_text.config(state=tk.NORMAL)
            
            for record in records:
                text = str(record) + "\n"
                self.log_text.insert(tk.END, text, record.level)
            
            # Auto-scroll to end
            if self.auto_scroll_var.get():
                self.log_text.see(tk.END)
            
            self.log_text.config(state=tk.DISABLED)
        
        self._update_status()
    
    def clear_logs(self):
        """Clear all logs."""
        if messagebox.askyesno("Clear Logs", "Clear all log entries?"):
            self.app.log_stream.clear()
            self.refresh_display()
    
    def copy_to_clipboard(self):
        """Copy all visible logs to clipboard."""
        try:
            content = self.log_text.get(1.0, tk.END).strip()
            if content:
                pyperclip.copy(content)
                messagebox.showinfo("Success", "Logs copied to clipboard.")
            else:
                messagebox.showwarning("No Content", "No logs to copy.")
        
        except Exception as e:
            # Fallback if pyperclip not available
            try:
                content = self.log_text.get(1.0, tk.END).strip()
                self.app.root.clipboard_clear()
                self.app.root.clipboard_append(content)
                messagebox.showinfo("Success", "Logs copied to clipboard.")
            except Exception:
                messagebox.showerror("Error", f"Failed to copy to clipboard: {e}")
    
    def save_logs(self):
        """Save logs to a file."""
        filename = filedialog.asksaveasfilename(
            title="Save Logs",
            defaultextension=".log",
            filetypes=[("Log files", "*.log"), ("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                content = self.log_text.get(1.0, tk.END).strip()
                
                if not content:
                    messagebox.showwarning("No Content", "No logs to save.")
                    return
                
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                messagebox.showinfo("Success", f"Logs saved to {filename}")
            
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save logs: {e}")
    
    def _update_status(self):
        """Update the status display."""
        filter_level = self.filter_var.get()
        
        if filter_level == "ALL":
            total_records = len(self.app.log_stream.get_records())
            self.status_var.set(f"Total: {total_records} records")
        else:
            filtered_records = len(self.app.log_stream.get_records(filter_level))
            total_records = len(self.app.log_stream.get_records())
            self.status_var.set(f"Showing: {filtered_records}/{total_records} records ({filter_level})")


# Try to import pyperclip, create a fallback if not available
try:
    import pyperclip
except ImportError:
    # Create a dummy pyperclip module
    class pyperclip:
        @staticmethod
        def copy(text):
            raise ImportError("pyperclip not available")