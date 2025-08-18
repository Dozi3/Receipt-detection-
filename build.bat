@echo off
REM Build script for Receipt Analyzer on Windows

echo Building Receipt Analyzer executable...

REM Check if PyInstaller is installed
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo PyInstaller not found. Installing...
    pip install pyinstaller
)

REM Clean previous builds
echo Cleaning previous builds...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist ReceiptAnalyzer.exe del ReceiptAnalyzer.exe

REM Build with PyInstaller using spec file
echo Building executable...
pyinstaller ReceiptAnalyzer.spec

if %errorlevel% == 0 (
    echo.
    echo ✓ Build completed successfully!
    echo Executable location: dist\ReceiptAnalyzer.exe
    echo.
    echo Installation notes:
    echo 1. Install Tesseract OCR from: https://github.com/UB-Mannheim/tesseract/wiki
    echo 2. Default Tesseract path: C:\Program Files\Tesseract-OCR\tesseract.exe
    echo 3. For PDF rasterization support, install Poppler for Windows
    echo.
) else (
    echo ✗ Build failed!
    exit /b 1
)

pause