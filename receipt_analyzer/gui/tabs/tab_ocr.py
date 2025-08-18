"""OCR settings tab."""

import tkinter as tk
from tkinter import ttk


class OCRTab:
    """OCR settings tab."""
    
    def __init__(self, parent, app):
        self.parent = parent
        self.app = app
        
        # Create main frame
        self.frame = ttk.Frame(parent)
        
        # Variables
        self.language_var = tk.StringVar(value="eng")
        self.max_edge_var = tk.IntVar(value=1000)
        self.psm_var = tk.IntVar(value=6)
        self.oem_var = tk.IntVar(value=3)
        
        # Setup GUI
        self.setup_gui()
    
    def setup_gui(self):
        """Setup the tab GUI."""
        # Title
        title_label = ttk.Label(self.frame, text="OCR Settings", font=("Arial", 14, "bold"))
        title_label.pack(pady=(10, 20))
        
        # Basic settings
        basic_frame = ttk.LabelFrame(self.frame, text="Basic OCR Settings", padding=10)
        basic_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Language
        lang_frame = ttk.Frame(basic_frame)
        lang_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(lang_frame, text="Language:", width=15).pack(side=tk.LEFT)
        
        lang_combo = ttk.Combobox(
            lang_frame, textvariable=self.language_var, 
            values=["eng", "fra", "deu", "spa", "ita", "por", "nld", "swe", "dan", "nor"],
            width=10
        )
        lang_combo.pack(side=tk.LEFT, padx=(5, 10))
        
        ttk.Label(lang_frame, text="Tesseract language code", foreground="blue").pack(side=tk.LEFT)
        
        # Max edge
        edge_frame = ttk.Frame(basic_frame)
        edge_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(edge_frame, text="Max Edge (px):", width=15).pack(side=tk.LEFT)
        
        ttk.Entry(edge_frame, textvariable=self.max_edge_var, width=10).pack(side=tk.LEFT, padx=(5, 10))
        
        ttk.Label(edge_frame, text="Maximum image edge size before OCR", foreground="blue").pack(side=tk.LEFT)
        
        # Advanced settings
        advanced_frame = ttk.LabelFrame(self.frame, text="Advanced OCR Settings", padding=10)
        advanced_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # PSM
        psm_frame = ttk.Frame(advanced_frame)
        psm_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(psm_frame, text="PSM Mode:", width=15).pack(side=tk.LEFT)
        
        psm_combo = ttk.Combobox(
            psm_frame, textvariable=self.psm_var,
            values=[6, 7, 8, 11, 12, 13],
            width=10, state="readonly"
        )
        psm_combo.pack(side=tk.LEFT, padx=(5, 10))
        
        ttk.Label(psm_frame, text="Page Segmentation Mode (6=uniform block)", foreground="blue").pack(side=tk.LEFT)
        
        # OEM
        oem_frame = ttk.Frame(advanced_frame)
        oem_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(oem_frame, text="OEM Mode:", width=15).pack(side=tk.LEFT)
        
        oem_combo = ttk.Combobox(
            oem_frame, textvariable=self.oem_var,
            values=[0, 1, 2, 3],
            width=10, state="readonly"
        )
        oem_combo.pack(side=tk.LEFT, padx=(5, 10))
        
        ttk.Label(oem_frame, text="OCR Engine Mode (3=default LSTM)", foreground="blue").pack(side=tk.LEFT)
        
        # Features
        features_frame = ttk.LabelFrame(self.frame, text="OCR Features", padding=10)
        features_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(features_frame, text="• Automatic orientation detection (0°, 90°, 180°, 270°)", anchor=tk.W).pack(fill=tk.X, pady=2)
        ttk.Label(features_frame, text="• Confidence scoring for best orientation selection", anchor=tk.W).pack(fill=tk.X, pady=2)
        ttk.Label(features_frame, text="• Image resizing for optimal OCR performance", anchor=tk.W).pack(fill=tk.X, pady=2)
        ttk.Label(features_frame, text="• Support for multiple languages", anchor=tk.W).pack(fill=tk.X, pady=2)
        
        # Test section
        test_frame = ttk.LabelFrame(self.frame, text="Test OCR", padding=10)
        test_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(
            test_frame, text="Test Tesseract Installation",
            command=self.test_tesseract
        ).pack(pady=5)
        
        self.test_result_var = tk.StringVar()
        self.test_result_label = ttk.Label(
            test_frame, textvariable=self.test_result_var, 
            foreground="blue"
        )
        self.test_result_label.pack(pady=5)
    
    def test_tesseract(self):
        """Test Tesseract installation."""
        try:
            from ...core.ocr import check_tesseract_available
            
            is_available, message = check_tesseract_available()
            
            if is_available:
                self.test_result_var.set(f"✓ {message}")
                self.test_result_label.config(foreground="green")
            else:
                self.test_result_var.set(f"✗ {message}")
                self.test_result_label.config(foreground="red")
        
        except Exception as e:
            self.test_result_var.set(f"✗ Error: {e}")
            self.test_result_label.config(foreground="red")
    
    def update_from_config(self):
        """Update GUI from configuration."""
        config = self.app.config
        ocr = config.ocr
        
        self.language_var.set(ocr.language)
        self.max_edge_var.set(ocr.max_edge_px)
        self.psm_var.set(ocr.psm)
        self.oem_var.set(ocr.oem)
    
    def update_config(self):
        """Update configuration from GUI."""
        config = self.app.config
        ocr = config.ocr
        
        ocr.language = self.language_var.get()
        ocr.max_edge_px = self.max_edge_var.get()
        ocr.psm = self.psm_var.get()
        ocr.oem = self.oem_var.get()