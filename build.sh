#!/bin/bash

# Build script for Receipt Analyzer

echo "Building Receipt Analyzer executable..."

# Check if PyInstaller is installed
if ! command -v pyinstaller &> /dev/null; then
    echo "PyInstaller not found. Installing..."
    pip install pyinstaller
fi

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf build/
rm -rf dist/
rm -f ReceiptAnalyzer.exe

# Build with PyInstaller using spec file
echo "Building executable..."
pyinstaller ReceiptAnalyzer.spec

if [ $? -eq 0 ]; then
    echo ""
    echo "✓ Build completed successfully!"
    echo "Executable location: dist/ReceiptAnalyzer.exe"
    echo ""
    echo "Installation notes:"
    echo "1. Install Tesseract OCR from: https://github.com/UB-Mannheim/tesseract/wiki"
    echo "2. Default Tesseract path: C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
    echo "3. For PDF rasterization support, install Poppler for Windows"
    echo ""
else
    echo "✗ Build failed!"
    exit 1
fi