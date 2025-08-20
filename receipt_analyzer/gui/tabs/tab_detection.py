"""Detection settings tab."""

import tkinter as tk
from tkinter import ttk


class DetectionTab:
    """Detection settings tab."""
    
    def __init__(self, parent, app):
        self.parent = parent
        self.app = app
        
        # Create main frame
        self.frame = ttk.Frame(parent)
        
        # Variables
        self.method_var = tk.StringVar(value="opencv")
        
        # OpenCV parameters
        self.min_area_var = tk.DoubleVar(value=0.01)
        self.max_area_var = tk.DoubleVar(value=0.9)
        self.min_aspect_var = tk.DoubleVar(value=0.3)
        self.max_aspect_var = tk.DoubleVar(value=4.0)
        self.quad_epsilon_var = tk.DoubleVar(value=0.02)
        self.canny1_var = tk.IntVar(value=50)
        self.canny2_var = tk.IntVar(value=140)
        self.morph_close_var = tk.IntVar(value=9)
        self.warp_long_edge_var = tk.IntVar(value=1600)
        self.pad_px_var = tk.IntVar(value=6)
        
        # Setup GUI
        self.setup_gui()
    
    def setup_gui(self):
        """Setup the tab GUI."""
        # Title
        title_label = ttk.Label(self.frame, text="Detection Settings", font=("Arial", 14, "bold"))
        title_label.pack(pady=(10, 20))
        
        # Method selection
        method_frame = ttk.LabelFrame(self.frame, text="Detection Method", padding=10)
        method_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Radiobutton(
            method_frame, text="Simple (use images as-is)", 
            variable=self.method_var, value="simple"
        ).pack(anchor=tk.W, pady=2)
        
        ttk.Radiobutton(
            method_frame, text="OpenCV (contour detection + perspective correction)", 
            variable=self.method_var, value="opencv"
        ).pack(anchor=tk.W, pady=2)
        
        # OpenCV parameters
        opencv_frame = ttk.LabelFrame(self.frame, text="OpenCV Parameters", padding=10)
        opencv_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Create scrollable frame for parameters
        canvas = tk.Canvas(opencv_frame)
        scrollbar = ttk.Scrollbar(opencv_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Parameters
        params = [
            ("Min Area Ratio", self.min_area_var, "0.01", "Minimum receipt area as fraction of page"),
            ("Max Area Ratio", self.max_area_var, "0.9", "Maximum receipt area as fraction of page"),
            ("Min Aspect Ratio", self.min_aspect_var, "0.3", "Minimum width/height ratio"),
            ("Max Aspect Ratio", self.max_aspect_var, "4.0", "Maximum width/height ratio"),
            ("Quad Epsilon", self.quad_epsilon_var, "0.02", "Contour approximation epsilon"),
            ("Canny Lower", self.canny1_var, "50", "Canny edge detection lower threshold"),
            ("Canny Upper", self.canny2_var, "140", "Canny edge detection upper threshold"),
            ("Morph Close", self.morph_close_var, "9", "Morphological closing kernel size"),
            ("Warp Long Edge", self.warp_long_edge_var, "1600", "Maximum edge length for perspective warp"),
            ("Padding Pixels", self.pad_px_var, "6", "Padding around extracted receipts"),
        ]
        
        for i, (label, var, default, tooltip) in enumerate(params):
            param_frame = ttk.Frame(scrollable_frame)
            param_frame.pack(fill=tk.X, pady=2)
            
            ttk.Label(param_frame, text=f"{label}:", width=15).pack(side=tk.LEFT)
            
            entry = ttk.Entry(param_frame, textvariable=var, width=10)
            entry.pack(side=tk.LEFT, padx=(5, 10))
            
            ttk.Label(param_frame, text=f"({default})", foreground="gray").pack(side=tk.LEFT, padx=(0, 10))
            ttk.Label(param_frame, text=tooltip, foreground="blue").pack(side=tk.LEFT)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Reset button
        ttk.Button(
            opencv_frame, text="Reset to Defaults", 
            command=self.reset_defaults
        ).pack(pady=10)
    
    def reset_defaults(self):
        """Reset all parameters to defaults."""
        self.min_area_var.set(0.01)
        self.max_area_var.set(0.9)
        self.min_aspect_var.set(0.3)
        self.max_aspect_var.set(4.0)
        self.quad_epsilon_var.set(0.02)
        self.canny1_var.set(50)
        self.canny2_var.set(140)
        self.morph_close_var.set(9)
        self.warp_long_edge_var.set(1600)
        self.pad_px_var.set(6)
    
    def update_from_config(self):
        """Update GUI from configuration."""
        config = self.app.config
        self.method_var.set(config.detection_method)
        
        # OpenCV parameters
        opencv = config.opencv
        self.min_area_var.set(opencv.min_area_ratio)
        self.max_area_var.set(opencv.max_area_ratio)
        self.min_aspect_var.set(opencv.min_aspect)
        self.max_aspect_var.set(opencv.max_aspect)
        self.quad_epsilon_var.set(opencv.quad_epsilon)
        self.canny1_var.set(opencv.canny1)
        self.canny2_var.set(opencv.canny2)
        self.morph_close_var.set(opencv.morph_close)
        self.warp_long_edge_var.set(opencv.warp_long_edge_px)
        self.pad_px_var.set(opencv.pad_px)
    
    def update_config(self):
        """Update configuration from GUI."""
        config = self.app.config
        config.detection_method = self.method_var.get()
        
        # OpenCV parameters
        opencv = config.opencv
        opencv.min_area_ratio = self.min_area_var.get()
        opencv.max_area_ratio = self.max_area_var.get()
        opencv.min_aspect = self.min_aspect_var.get()
        opencv.max_aspect = self.max_aspect_var.get()
        opencv.quad_epsilon = self.quad_epsilon_var.get()
        opencv.canny1 = self.canny1_var.get()
        opencv.canny2 = self.canny2_var.get()
        opencv.morph_close = self.morph_close_var.get()
        opencv.warp_long_edge_px = self.warp_long_edge_var.get()
        opencv.pad_px = self.pad_px_var.get()