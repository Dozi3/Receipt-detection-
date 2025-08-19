#!/usr/bin/env python3
"""
Script to check for import issues without requiring a display
"""

import sys
import importlib
import traceback
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

def test_import(module_name):
    """Test importing a module and report any issues"""
    print(f"Testing import of {module_name}...")
    try:
        module = importlib.import_module(module_name)
        print(f"✅ Successfully imported {module_name}")
        return True
    except Exception as e:
        print(f"❌ Failed to import {module_name}: {e}")
        print("Traceback:")
        traceback.print_exc()
        return False

# Test all the relevant modules
modules_to_test = [
    # Core modules
    "receipt_analyzer.core.config",
    "receipt_analyzer.core.logging_utils",
    "receipt_analyzer.core.detection_simple",
    "receipt_analyzer.core.detection_opencv",
    "receipt_analyzer.core.ocr",
    "receipt_analyzer.core.parsing",
    "receipt_analyzer.core.naming",
    "receipt_analyzer.core.vendors",
    "receipt_analyzer.core.csv_export",
    "receipt_analyzer.core.pdf_io",
    "receipt_analyzer.core.processing",
    
    # GUI modules
    "receipt_analyzer.gui.utils",
    "receipt_analyzer.gui.dialogs",
    "receipt_analyzer.gui.tabs.tab_input_run",
    "receipt_analyzer.gui.tabs.tab_detection",
    "receipt_analyzer.gui.tabs.tab_ocr",
    "receipt_analyzer.gui.tabs.tab_parsing_naming",
    "receipt_analyzer.gui.tabs.tab_vendors",
    "receipt_analyzer.gui.tabs.tab_outputs",
    "receipt_analyzer.gui.tabs.tab_logs",
    "receipt_analyzer.gui.app",
    
    # Main module
    "receipt_analyzer.main",
]

def main():
    """Run the import tests"""
    print("Starting import tests...\n")
    
    failed = []
    for module in modules_to_test:
        if not test_import(module):
            failed.append(module)
        print("")
    
    if failed:
        print(f"\n❌ {len(failed)} modules failed to import:")
        for module in failed:
            print(f"  - {module}")
        return 1
    else:
        print("\n✅ All modules imported successfully!")
        return 0

if __name__ == "__main__":
    sys.exit(main())
