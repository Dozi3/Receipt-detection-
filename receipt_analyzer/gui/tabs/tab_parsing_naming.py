"""Parsing & Naming settings tab."""

import tkinter as tk
from tkinter import ttk


class ParsingNamingTab:
    """Parsing & Naming settings tab."""
    
    def __init__(self, parent, app):
        self.parent = parent
        self.app = app
        
        # Create main frame
        self.frame = ttk.Frame(parent)
        
        # Setup GUI
        self.setup_gui()
    
    def setup_gui(self):
        """Setup the tab GUI."""
        # Title
        title_label = ttk.Label(self.frame, text="Parsing & Naming", font=("Arial", 14, "bold"))
        title_label.pack(pady=(10, 20))
        
        # Date parsing
        date_frame = ttk.LabelFrame(self.frame, text="Date Parsing", padding=10)
        date_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(date_frame, text="Supported Date Formats:", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(0, 5))
        
        date_formats = [
            "DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY",
            "DD/MM/YY, DD-MM-YY, DD.MM.YY (assumes 20xx)",
            "DD Mon YYYY, DD Month YYYY",
            "Examples: 25/12/2023, 25-Dec-2023, 25 December 2023"
        ]
        
        for fmt in date_formats:
            ttk.Label(date_frame, text=f"• {fmt}", foreground="blue").pack(anchor=tk.W, padx=10)
        
        ttk.Label(date_frame, text="Output Format: DD-MM-YYYY (fixed)", 
                 font=("Arial", 9, "bold"), foreground="green").pack(anchor=tk.W, pady=(5, 0))
        
        # Amount parsing
        amount_frame = ttk.LabelFrame(self.frame, text="Amount Parsing", padding=10)
        amount_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(amount_frame, text="Amount Detection Rules:", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(0, 5))
        
        amount_rules = [
            "£12.34, £1,234.56 (with GBP symbol)",
            "12.34, 1,234.56 (decimal amounts)",
            "Largest plausible value is selected",
            "Range: £0.01 - £10,000.00"
        ]
        
        for rule in amount_rules:
            ttk.Label(amount_frame, text=f"• {rule}", foreground="blue").pack(anchor=tk.W, padx=10)
        
        ttk.Label(amount_frame, text="Filename Token: 12.34 → 12-34", 
                 font=("Arial", 9, "bold"), foreground="green").pack(anchor=tk.W, pady=(5, 0))
        
        # Vendor parsing
        vendor_frame = ttk.LabelFrame(self.frame, text="Vendor Parsing", padding=10)
        vendor_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(vendor_frame, text="Vendor Detection Priority:", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(0, 5))
        
        vendor_methods = [
            "1. Email domain extraction (highest priority)",
            "2. Keyword mapping from vendor database",
            "3. First clean line of text (fallback)",
            "Generic email domains (gmail.com, etc.) are ignored"
        ]
        
        for method in vendor_methods:
            ttk.Label(vendor_frame, text=f"• {method}", foreground="blue").pack(anchor=tk.W, padx=10)
        
        # Filename template
        naming_frame = ttk.LabelFrame(self.frame, text="Filename Template", padding=10)
        naming_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(naming_frame, text="Template (Read-Only):", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        
        template_text = "Vendor_GBP-12-34_DD-MM-YYYY.png"
        template_label = ttk.Label(
            naming_frame, text=template_text, 
            font=("Consolas", 12, "bold"), foreground="darkgreen",
            background="lightgray", relief=tk.SUNKEN
        )
        template_label.pack(pady=10, padx=20, fill=tk.X)
        
        # Examples
        examples_frame = ttk.Frame(naming_frame)
        examples_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(examples_frame, text="Examples:", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        
        examples = [
            "Tesco_GBP-23-45_25-12-2023.png",
            "Costa_Coffee_GBP-04-50_01-01-2024.png",
            "Shell_GBP-67-89_15-03-2023.png",
            "Unknown_GBP-00-00_01-01-2024.png"
        ]
        
        for example in examples:
            ttk.Label(examples_frame, text=f"• {example}", 
                     font=("Consolas", 9), foreground="darkblue").pack(anchor=tk.W, padx=10)
        
        # Safety features
        safety_frame = ttk.LabelFrame(self.frame, text="Filename Safety", padding=10)
        safety_frame.pack(fill=tk.X, padx=10, pady=5)
        
        safety_features = [
            "Illegal characters replaced with underscores",
            "Reserved names (CON, PRN, etc.) are modified",
            "Trailing dots and spaces removed",
            "Maximum length enforced",
            "Unique filenames guaranteed (_2, _3, etc.)"
        ]
        
        for feature in safety_features:
            ttk.Label(safety_frame, text=f"• {feature}", foreground="blue").pack(anchor=tk.W, padx=10)
    
    def update_from_config(self):
        """Update GUI from configuration."""
        # This tab is mostly informational
        pass
    
    def update_config(self):
        """Update configuration from GUI."""
        # This tab doesn't modify config
        pass