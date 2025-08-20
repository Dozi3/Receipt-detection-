# Receipt Analyzer

A comprehensive receipt detection and processing application that:

- Splits PDFs into individual receipt images
- Detects multiple receipts per page using OpenCV
- Performs OCR and names each image: `Vendor_GBP-12-34_DD-MM-YYYY.(png|jpg)`
- Generates CSV reports for accounting software
- Features both GUI (default) and CLI interfaces
- Includes self-learning vendor mapping system

## Features

✅ **PDF Processing**: Extract embedded images or rasterize pages  
✅ **Receipt Detection**: Simple mode or advanced OpenCV contour detection  
✅ **OCR**: Automatic orientation detection and text extraction  
✅ **Smart Parsing**: Extract vendor, amount, and date information  
✅ **Vendor Learning**: Self-learning vendor mapping with import/export  
✅ **Multiple Output Formats**: PNG/JPEG with optional per-page ZIP files  
✅ **CSV Reports**: Generate FreeAgent and index CSV files  
✅ **GUI Interface**: Complete Tkinter-based GUI with tabbed interface  
✅ **CLI Interface**: Full command-line support for automation  
✅ **Comprehensive Logging**: Track processing with detailed logs  
✅ **Windows Executable**: PyInstaller configuration for .exe build  

## Installation

### Prerequisites
- Python 3.8+
- Tesseract OCR (required for text recognition)

### Install Tesseract OCR

**Windows:**
Download and install from: https://github.com/UB-Mannheim/tesseract/wiki  
Default installation path: `C:\Program Files\Tesseract-OCR\tesseract.exe`

**macOS:**
```bash
brew install tesseract
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get install tesseract-ocr python3-tk
```

### Install Receipt Analyzer

```bash
git clone https://github.com/Dozi3/Receipt-detection-.git
cd Receipt-detection-
pip install -r requirements.txt
```

For full functionality including PDF rasterization and OpenCV detection:
```bash
pip install pdf2image opencv-python-headless
```

## Usage

### GUI (Default)
```bash
python -m receipt_analyzer
```

### CLI
```bash
# Basic usage
python -m receipt_analyzer --cli --in /path/to/pdfs --out /path/to/output

# With options
python -m receipt_analyzer --cli --in ./pdfs --out ./output --method opencv --png --vendor-map ./vendors.json

# Check dependencies
python -m receipt_analyzer --check-deps
```

### CLI Options
```
--in DIR              Input directory containing PDF files
--out DIR             Output directory for processed receipts
--method {simple|opencv}  Detection method (default: opencv)
--png                 Force PNG output format
--quality N           JPEG quality 1-100 (default: 85)
--max-edge N          Max image edge size (default: 1000)
--lang CODE           OCR language (default: eng)
--vendor-map PATH     Vendor mapping JSON file
--no-zip              Disable per-page ZIP files
--cli                 Force CLI mode
--gui                 Force GUI mode (default)
--check-deps          Check dependencies and exit
```

### Build Executable

**Windows:**
```cmd
build.bat
```

**Linux/macOS:**
```bash
chmod +x build.sh
./build.sh
```

## Architecture

### Core Modules (`receipt_analyzer/core/`)
- `config.py` - Configuration management with YAML support
- `pdf_io.py` - PDF processing with PyMuPDF and pdf2image fallback
- `detection_simple.py` - Simple "as-is" image processing
- `detection_opencv.py` - Advanced OpenCV contour detection
- `ocr.py` - Tesseract OCR with orientation detection
- `parsing.py` - Text parsing for vendor, amount, and date extraction
- `naming.py` - Safe filename generation
- `vendors.py` - Vendor mapping system with persistence
- `csv_export.py` - CSV report generation
- `logging_utils.py` - Comprehensive logging system
- `processing.py` - Main processing pipeline

### GUI Interface (`receipt_analyzer/gui/`)
- `app.py` - Main Tkinter application with tabbed interface
- `tabs/` - Individual tab implementations:
  - `tab_input_run.py` - Input selection and processing control
  - `tab_detection.py` - Detection method configuration
  - `tab_ocr.py` - OCR settings and testing
  - `tab_parsing_naming.py` - Parsing rules and filename format
  - `tab_vendors.py` - Vendor mapping management
  - `tab_outputs.py` - Output format and file management
  - `tab_logs.py` - Real-time log display and filtering

### Output Files
- **Receipt Images**: `Vendor_GBP-12-34_DD-MM-YYYY.(png|jpg)`
- **freeagent.csv**: For FreeAgent accounting software
- **receipts_index.csv**: Detailed processing index
- **processing_summary.csv**: Statistics and summary
- **processing.log**: Detailed processing log
- **page_N.zip**: Per-page archives (optional)

## Configuration

Configuration is stored in YAML format at:
- **Windows**: `%APPDATA%\ReceiptAnalyzer\config.yaml`
- **Linux/macOS**: `~/.receipt_analyzer/config.yaml`

Vendor mappings are stored at:
- **Windows**: `%APPDATA%\ReceiptAnalyzer\vendors.json`
- **Linux/macOS**: `~/.receipt_analyzer/vendors.json`

## Development

### Running Tests
```bash
python -c "
from receipt_analyzer.core.config import Config
from receipt_analyzer.core.naming import safe_filename
print('✓ Basic functionality test passed')
"
```

### Project Structure
```
receipt_analyzer/
├── core/              # Core processing modules
├── gui/               # GUI application
│   └── tabs/          # GUI tab implementations
├── tests/             # Test suite
├── main.py            # Main entry point
├── cli.py             # CLI interface
└── __main__.py        # Package execution entry point
```

## Dependencies

### Required
- `pymupdf` - PDF processing
- `pillow` - Image manipulation
- `pytesseract` - OCR interface
- `pyyaml` - Configuration files

### Optional
- `pdf2image` + Poppler - PDF rasterization fallback
- `opencv-python-headless` - Advanced receipt detection
- `pyperclip` - Clipboard support in GUI

### GUI (Linux only)
- `python3-tk` - Tkinter GUI framework

## License

This project is open source. See the repository for license details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## Support

For issues and feature requests, please use the GitHub issue tracker.