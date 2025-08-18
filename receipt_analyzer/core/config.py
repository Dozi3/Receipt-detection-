"""Configuration management with dataclasses and YAML support."""

import os
import yaml
from dataclasses import dataclass, asdict, fields
from pathlib import Path
from typing import Optional, Dict, Any, List


@dataclass
class OpenCVConfig:
    """OpenCV detection parameters."""
    min_area_ratio: float = 0.01
    max_area_ratio: float = 0.9
    min_aspect: float = 0.3
    max_aspect: float = 4.0
    quad_epsilon: float = 0.02
    canny1: int = 50
    canny2: int = 140
    morph_close: int = 9
    warp_long_edge_px: int = 1600
    pad_px: int = 6


@dataclass
class OCRConfig:
    """OCR processing parameters."""
    language: str = "eng"
    max_edge_px: int = 1000
    psm: int = 6
    oem: int = 3


@dataclass
class OutputConfig:
    """Output format configuration."""
    format: str = "png"  # "png" or "jpeg"
    jpeg_quality: int = 85
    per_page_zip: bool = False
    max_edge: int = 1000


@dataclass
class ParsingConfig:
    """Text parsing configuration."""
    date_formats: List[str] = None
    amount_patterns: List[str] = None
    
    def __post_init__(self):
        if self.date_formats is None:
            self.date_formats = [
                r"\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}",
                r"\d{1,2}\s+\w{3,9}\s+\d{2,4}",
            ]
        if self.amount_patterns is None:
            self.amount_patterns = [
                r"£\s*\d+\.?\d*",
                r"\d+\.\d{2}",
                r"\d{1,3}(?:,\d{3})*\.\d{2}",
            ]


@dataclass
class Config:
    """Main application configuration."""
    detection_method: str = "opencv"  # "simple" or "opencv"
    opencv: OpenCVConfig = None
    ocr: OCRConfig = None
    output: OutputConfig = None
    parsing: ParsingConfig = None
    vendor_map_path: Optional[str] = None
    
    def __post_init__(self):
        if self.opencv is None:
            self.opencv = OpenCVConfig()
        if self.ocr is None:
            self.ocr = OCRConfig()
        if self.output is None:
            self.output = OutputConfig()
        if self.parsing is None:
            self.parsing = ParsingConfig()


def get_config_dir() -> Path:
    """Get the user configuration directory."""
    if os.name == 'nt':  # Windows
        config_dir = Path(os.getenv('APPDATA', '')) / 'ReceiptAnalyzer'
    else:  # Unix-like
        config_dir = Path.home() / '.receipt_analyzer'
    
    config_dir.mkdir(exist_ok=True)
    return config_dir


def get_default_config_path() -> Path:
    """Get the default configuration file path."""
    return get_config_dir() / 'config.yaml'


def get_default_vendor_map_path() -> Path:
    """Get the default vendor mapping file path."""
    return get_config_dir() / 'vendors.json'


def load_config(config_path: Optional[Path] = None) -> Config:
    """Load configuration from YAML file."""
    if config_path is None:
        config_path = get_default_config_path()
    
    if not config_path.exists():
        return Config()
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        if not data:
            return Config()
        
        # Convert nested dictionaries to dataclasses
        config_data = {}
        for field in fields(Config):
            if field.name in data:
                if field.name == 'opencv' and isinstance(data[field.name], dict):
                    config_data[field.name] = OpenCVConfig(**data[field.name])
                elif field.name == 'ocr' and isinstance(data[field.name], dict):
                    config_data[field.name] = OCRConfig(**data[field.name])
                elif field.name == 'output' and isinstance(data[field.name], dict):
                    config_data[field.name] = OutputConfig(**data[field.name])
                elif field.name == 'parsing' and isinstance(data[field.name], dict):
                    config_data[field.name] = ParsingConfig(**data[field.name])
                else:
                    config_data[field.name] = data[field.name]
        
        return Config(**config_data)
    
    except (yaml.YAMLError, TypeError, ValueError) as e:
        print(f"Warning: Failed to load config from {config_path}: {e}")
        return Config()


def save_config(config: Config, config_path: Optional[Path] = None) -> bool:
    """Save configuration to YAML file."""
    if config_path is None:
        config_path = get_default_config_path()
    
    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to dictionary for YAML serialization
        data = asdict(config)
        
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, indent=2)
        
        return True
    
    except (yaml.YAMLError, OSError) as e:
        print(f"Error: Failed to save config to {config_path}: {e}")
        return False


def merge_cli_args(config: Config, args: Dict[str, Any]) -> Config:
    """Merge command-line arguments into configuration."""
    # Create a copy of the config
    import copy
    new_config = copy.deepcopy(config)
    
    # Map CLI arguments to config fields
    if 'method' in args and args['method']:
        new_config.detection_method = args['method']
    
    if 'lang' in args and args['lang']:
        new_config.ocr.language = args['lang']
    
    if 'max_edge' in args and args['max_edge']:
        new_config.ocr.max_edge_px = args['max_edge']
        new_config.output.max_edge = args['max_edge']
    
    if 'quality' in args and args['quality']:
        new_config.output.jpeg_quality = args['quality']
    
    if 'png' in args and args['png']:
        new_config.output.format = 'png'
    elif 'quality' in args:  # JPEG if quality specified without --png
        new_config.output.format = 'jpeg'
    
    if 'no_zip' in args and args['no_zip']:
        new_config.output.per_page_zip = False
    
    if 'vendor_map' in args and args['vendor_map']:
        new_config.vendor_map_path = args['vendor_map']
    
    return new_config