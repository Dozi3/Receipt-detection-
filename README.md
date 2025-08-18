# Receipt Analyzer

A comprehensive receipt detection and processing application that:

- Splits PDFs into individual receipt images
- Detects multiple receipts per page using OpenCV
- Performs OCR and names each image: `Vendor_GBP-12-34_DD-MM-YYYY.(png|jpg)`
- Generates CSV reports for accounting software
- Features both GUI (default) and CLI interfaces
- Includes self-learning vendor mapping system

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
sudo apt-get install tesseract-ocr
```

### Install Receipt Analyzer

```bash
pip install -r requirements.txt
```

For full functionality including PDF rasterization and OpenCV detection:
```bash
pip install -r requirements.txt
pip install pdf2image opencv-python-headless
```

## Usage

### GUI (Default)
```bash
python -m receipt_analyzer
```

### CLI
```bash
python -m receipt_analyzer --cli --in /path/to/pdfs --out /path/to/output
```

### Build Executable
```bash
pyinstaller --onefile --noconsole --name ReceiptAnalyzer \
  --add-data "assets;assets" \
  --hidden-import tkinter \
  receipt_analyzer/main.py
```

## Features

- **PDF Processing**: Extract embedded images or rasterize pages
- **Receipt Detection**: Simple mode or advanced OpenCV contour detection
- **OCR**: Automatic orientation detection and text extraction
- **Smart Parsing**: Extract vendor, amount, and date information
- **Vendor Learning**: Self-learning vendor mapping with import/export
- **Multiple Output Formats**: PNG/JPEG with optional per-page ZIP files
- **CSV Reports**: Generate FreeAgent and index CSV files
- **Comprehensive Logging**: Track processing with detailed logs

## Architecture

- `receipt_analyzer/core/` - Core processing modules
- `receipt_analyzer/gui/` - Tkinter GUI interface
- `receipt_analyzer/cli.py` - Command-line interface
- `receipt_analyzer/tests/` - Unit and integration tests