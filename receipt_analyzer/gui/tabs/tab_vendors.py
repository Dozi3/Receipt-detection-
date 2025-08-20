"""Vendors management tab."""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path

from ..utils import run_with_busy_indicator


class VendorsTab:
    """Vendors management tab."""
    
    def __init__(self, parent, app):
        self.parent = parent
        self.app = app
        
        # Create main frame
        self.frame = ttk.Frame(parent)
        
        # Variables
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self.on_search_change)
        
        # Setup GUI
        self.setup_gui()
        self.refresh_vendor_list()
    
    def setup_gui(self):
        """Setup the tab GUI."""
        # Title
        title_label = ttk.Label(self.frame, text="Vendor Management", font=("Arial", 14, "bold"))
        title_label.pack(pady=(10, 20))
        
        # Controls frame
        controls_frame = ttk.Frame(self.frame)
        controls_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Search
        search_frame = ttk.LabelFrame(controls_frame, text="Search", padding=5)
        search_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        ttk.Entry(search_frame, textvariable=self.search_var).pack(fill=tk.X)
        
        # Buttons
        buttons_frame = ttk.Frame(controls_frame)
        buttons_frame.pack(side=tk.RIGHT)
        
        ttk.Button(buttons_frame, text="Add", command=self.add_vendor).pack(side=tk.LEFT, padx=2)
        ttk.Button(buttons_frame, text="Edit", command=self.edit_vendor).pack(side=tk.LEFT, padx=2)
        ttk.Button(buttons_frame, text="Delete", command=self.delete_vendor).pack(side=tk.LEFT, padx=2)
        
        # Vendor list
        list_frame = ttk.LabelFrame(self.frame, text="Keyword → Vendor Mappings", padding=5)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Treeview
        columns = ("keyword", "vendor", "type")
        self.vendor_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=12)
        
        self.vendor_tree.heading("keyword", text="Keyword")
        self.vendor_tree.heading("vendor", text="Vendor")
        self.vendor_tree.heading("type", text="Type")
        
        self.vendor_tree.column("keyword", width=200)
        self.vendor_tree.column("vendor", width=250)
        self.vendor_tree.column("type", width=100)
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.vendor_tree.yview)
        h_scrollbar = ttk.Scrollbar(list_frame, orient=tk.HORIZONTAL, command=self.vendor_tree.xview)
        
        self.vendor_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        self.vendor_tree.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)
        
        # Import/Export
        io_frame = ttk.LabelFrame(self.frame, text="Import / Export", padding=10)
        io_frame.pack(fill=tk.X, padx=10, pady=5)
        
        io_buttons = ttk.Frame(io_frame)
        io_buttons.pack()
        
        ttk.Button(io_buttons, text="Import JSON", command=self.import_json).pack(side=tk.LEFT, padx=5)
        ttk.Button(io_buttons, text="Export JSON", command=self.export_json).pack(side=tk.LEFT, padx=5)
        ttk.Button(io_buttons, text="Import CSV", command=self.import_csv).pack(side=tk.LEFT, padx=5)
        ttk.Button(io_buttons, text="Export CSV", command=self.export_csv).pack(side=tk.LEFT, padx=5)
        
        # Save button
        save_frame = ttk.Frame(self.frame)
        save_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(
            save_frame, text="Save & Apply Changes", 
            command=self.save_changes
        ).pack()
    
    def refresh_vendor_list(self):
        """Refresh the vendor list display."""
        # Clear existing items
        for item in self.vendor_tree.get_children():
            self.vendor_tree.delete(item)
        
        # Get search term
        search_term = self.search_var.get().lower()
        
        # Add vendors
        vendor_map = self.app.vendor_map
        
        for keyword, vendor in sorted(vendor_map.keywords.items()):
            # Apply search filter
            if search_term and search_term not in keyword.lower() and search_term not in vendor.lower():
                continue
            
            # Determine type
            if keyword in vendor_map.manual_entries:
                entry_type = "Manual"
            elif keyword in vendor_map.auto_learned:
                entry_type = "Auto"
            else:
                entry_type = "Built-in"
            
            self.vendor_tree.insert("", tk.END, values=(keyword, vendor, entry_type))
    
    def on_search_change(self, *args):
        """Handle search term change."""
        self.refresh_vendor_list()
    
    def add_vendor(self):
        """Add a new vendor mapping."""
        dialog = VendorDialog(self.frame, "Add Vendor Mapping")
        if dialog.result:
            keyword, vendor = dialog.result
            self.app.vendor_map.add_keyword(keyword, vendor, is_manual=True)
            self.refresh_vendor_list()
    
    def edit_vendor(self):
        """Edit selected vendor mapping."""
        selection = self.vendor_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a vendor mapping to edit.")
            return
        
        item = selection[0]
        values = self.vendor_tree.item(item, "values")
        keyword, vendor, entry_type = values
        
        dialog = VendorDialog(self.frame, "Edit Vendor Mapping", keyword, vendor)
        if dialog.result:
            new_keyword, new_vendor = dialog.result
            
            # Remove old mapping
            self.app.vendor_map.remove_keyword(keyword)
            
            # Add new mapping
            self.app.vendor_map.add_keyword(new_keyword, new_vendor, is_manual=True)
            
            self.refresh_vendor_list()
    
    def delete_vendor(self):
        """Delete selected vendor mapping."""
        selection = self.vendor_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a vendor mapping to delete.")
            return
        
        item = selection[0]
        values = self.vendor_tree.item(item, "values")
        keyword, vendor, entry_type = values
        
        if messagebox.askyesno("Confirm Delete", f"Delete mapping '{keyword}' → '{vendor}'?"):
            self.app.vendor_map.remove_keyword(keyword)
            self.refresh_vendor_list()
    
    def import_json(self):
        """Import vendor mappings from JSON."""
        filename = filedialog.askopenfilename(
            title="Import Vendor Mappings",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            from ...core.vendors import load_vendor_map, merge_vendor_maps
            
            def import_operation():
                try:
                    imported_map = load_vendor_map(Path(filename))
                    merged_map = merge_vendor_maps(self.app.vendor_map, imported_map)
                    return merged_map, None
                except Exception as e:
                    return None, e
            
            def done_callback(result, error):
                if error:
                    messagebox.showerror("Error", f"Failed to import vendor mappings:\n{error}")
                else:
                    self.app.vendor_map = result
                    self.refresh_vendor_list()
                    messagebox.showinfo("Success", f"Vendor mappings imported from {filename}")
            
            # Run the operation with a busy indicator
            run_with_busy_indicator(
                self.app.root,
                operation=import_operation,
                text="Importing vendor mappings...",
                done_callback=done_callback
            )
    
    def export_json(self):
        """Export vendor mappings to JSON."""
        filename = filedialog.asksaveasfilename(
            title="Export Vendor Mappings",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            from ...core.vendors import save_vendor_map
            
            def export_operation():
                try:
                    save_vendor_map(self.app.vendor_map, Path(filename))
                    return True, None
                except Exception as e:
                    return False, e
            
            def done_callback(result, error):
                if error:
                    messagebox.showerror("Error", f"Failed to export vendor mappings:\n{error}")
                else:
                    messagebox.showinfo("Success", f"Vendor mappings exported to {filename}")
            
            # Run the operation with a busy indicator
            run_with_busy_indicator(
                self.app.root,
                operation=export_operation,
                text="Exporting vendor mappings...",
                done_callback=done_callback
            )
    
    def import_csv(self):
        """Import vendor mappings from CSV."""
        filename = filedialog.askopenfilename(
            title="Import Vendor Mappings",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if filename:
            from ...core.vendors import import_vendor_map_csv, merge_vendor_maps
            
            def import_operation():
                try:
                    imported_map = import_vendor_map_csv(Path(filename))
                    merged_map = merge_vendor_maps(self.app.vendor_map, imported_map)
                    return merged_map, None
                except Exception as e:
                    return None, e
            
            def done_callback(result, error):
                if error:
                    messagebox.showerror("Error", f"Failed to import vendor mappings:\n{error}")
                else:
                    self.app.vendor_map = result
                    self.refresh_vendor_list()
                    messagebox.showinfo("Success", f"Vendor mappings imported from {filename}")
            
            # Run the operation with a busy indicator
            run_with_busy_indicator(
                self.app.root,
                operation=import_operation,
                text="Importing vendor mappings...",
                done_callback=done_callback
            )
    
    def export_csv(self):
        """Export vendor mappings to CSV."""
        filename = filedialog.asksaveasfilename(
            title="Export Vendor Mappings",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if filename:
            from ...core.vendors import export_vendor_map_csv
            
            def export_operation():
                try:
                    export_vendor_map_csv(self.app.vendor_map, Path(filename))
                    return True, None
                except Exception as e:
                    return False, e
            
            def done_callback(result, error):
                if error:
                    messagebox.showerror("Error", f"Failed to export vendor mappings:\n{error}")
                else:
                    messagebox.showinfo("Success", f"Vendor mappings exported to {filename}")
            
            # Run the operation with a busy indicator
            run_with_busy_indicator(
                self.app.root,
                operation=export_operation,
                text="Exporting vendor mappings...",
                done_callback=done_callback
            )
    
    def save_changes(self):
        """Save vendor mappings to persistent storage."""
        from ...core.vendors import save_vendor_map
        
        def save_operation():
            try:
                save_vendor_map(self.app.vendor_map)
                return True, None
            except Exception as e:
                return False, e
        
        def done_callback(result, error):
            if error:
                messagebox.showerror("Error", f"Failed to save vendor mappings:\n{error}")
            else:
                messagebox.showinfo("Success", "Vendor mappings saved successfully.")
        
        # Run the operation with a busy indicator
        run_with_busy_indicator(
            self.app.root,
            operation=save_operation,
            text="Saving vendor mappings...",
            done_callback=done_callback
        )


class VendorDialog:
    """Dialog for adding/editing vendor mappings."""
    
    def __init__(self, parent, title, keyword="", vendor=""):
        self.result = None
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("400x200")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center dialog
        self.dialog.geometry("+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50))
        
        # Variables
        self.keyword_var = tk.StringVar(value=keyword)
        self.vendor_var = tk.StringVar(value=vendor)
        
        # Setup GUI
        self.setup_gui()
        
        # Wait for dialog to close
        self.dialog.wait_window()
    
    def setup_gui(self):
        """Setup dialog GUI."""
        main_frame = ttk.Frame(self.dialog, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Keyword
        ttk.Label(main_frame, text="Keyword:").pack(anchor=tk.W)
        ttk.Entry(main_frame, textvariable=self.keyword_var).pack(fill=tk.X, pady=(0, 10))
        
        # Vendor
        ttk.Label(main_frame, text="Vendor:").pack(anchor=tk.W)
        ttk.Entry(main_frame, textvariable=self.vendor_var).pack(fill=tk.X, pady=(0, 20))
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(button_frame, text="OK", command=self.ok_clicked).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Cancel", command=self.cancel_clicked).pack(side=tk.LEFT)
    
    def ok_clicked(self):
        """Handle OK button click."""
        keyword = self.keyword_var.get().strip()
        vendor = self.vendor_var.get().strip()
        
        if not keyword:
            messagebox.showerror("Validation Error", "Keyword cannot be empty.")
            return
        
        if not vendor:
            messagebox.showerror("Validation Error", "Vendor cannot be empty.")
            return
        
        self.result = (keyword, vendor)
        self.dialog.destroy()
    
    def cancel_clicked(self):
        """Handle Cancel button click."""
        self.dialog.destroy()