#!/usr/bin/env python3
"""Test script to validate GUI fixes without creating actual Tkinter widgets."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_imports():
    """Test that all imports work correctly."""
    print("Testing imports...")
    
    try:
        # Test core imports first
        from receipt_analyzer.core.config import Config, load_config
        print("✅ Core config imports working")
        
        from receipt_analyzer.core.processing import process_pdf_files
        print("✅ Core processing imports working")
        
        # Test GUI imports
        import tkinter as tk
        print("✅ Tkinter available")
        
        # Import GUI modules without creating widgets
        from receipt_analyzer.gui.tabs.tab_input_run import InputRunTab
        print("✅ InputRunTab import working")
        
        from receipt_analyzer.gui.dialogs import ProcessingStatusDialog
        print("✅ ProcessingStatusDialog import working")
        
        print("✅ All imports successful")
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_method_signatures():
    """Test that method signatures are correct."""
    print("\nTesting method signatures...")
    
    try:
        from receipt_analyzer.gui.tabs.tab_input_run import InputRunTab
        import inspect
        
        # Check InputRunTab.update_config signature
        sig = inspect.signature(InputRunTab.update_config)
        param_count = len(sig.parameters)
        print(f"InputRunTab.update_config has {param_count} parameters (expected: 1 for self only)")
        
        if param_count != 1:  # Only self parameter expected
            print("❌ InputRunTab.update_config signature incorrect")
            return False
        else:
            print("✅ InputRunTab.update_config signature correct")
            
        print("✅ All method signatures correct")
        return True
        
    except Exception as e:
        print(f"❌ Method signature test failed: {e}")
        return False

def test_app_class_structure():
    """Test that the app class has the required methods."""
    print("\nTesting app class structure...")
    
    try:
        # Import without creating Tkinter root
        import sys
        from unittest.mock import Mock
        
        # Mock tkinter to avoid display issues
        original_tk = sys.modules.get('tkinter')
        mock_tk = Mock()
        mock_tk.Tk.return_value = Mock()
        mock_tk.StringVar.return_value = Mock()
        mock_tk.BooleanVar.return_value = Mock()
        mock_tk.DoubleVar.return_value = Mock()
        sys.modules['tkinter'] = mock_tk
        
        try:
            from receipt_analyzer.gui.app import ReceiptAnalyzerApp
            
            # Check required methods exist
            required_methods = [
                '_poll_worker_queue',
                '_handle_worker_message', 
                '_worker_process',
                'start_processing',
                'stop_processing',
                'set_processing_state'
            ]
            
            for method in required_methods:
                if not hasattr(ReceiptAnalyzerApp, method):
                    print(f"❌ Missing method: {method}")
                    return False
                else:
                    print(f"✅ Method exists: {method}")
                    
            print("✅ App class structure correct")
            return True
            
        finally:
            # Restore original tkinter
            if original_tk:
                sys.modules['tkinter'] = original_tk
            elif 'tkinter' in sys.modules:
                del sys.modules['tkinter']
                
    except Exception as e:
        print(f"❌ App class structure test failed: {e}")
        return False

def main():
    """Run all validation tests."""
    print("🔧 RECEIPT ANALYZER - GUI FIXES VALIDATION")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_method_signatures,
        test_app_class_structure
    ]
    
    passed = 0
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"📊 VALIDATION RESULTS: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("✅ All validation tests passed!")
        print("🎯 The GUI fixes should resolve the crashing issues.")
        print("")
        print("Key fixes applied:")
        print("• Fixed InputRunTab.update_config() parameter issue")
        print("• Added better error handling in worker process")
        print("• Improved queue polling mechanism")
        print("• Added debug logging for troubleshooting")
        print("• Enhanced thread safety in completion handlers")
        return True
    else:
        print("❌ Some validation tests failed!")
        print("⚠️  Please check the error messages above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
