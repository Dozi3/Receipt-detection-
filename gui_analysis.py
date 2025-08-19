#!/usr/bin/env python3
"""
Script to analyze the GUI code for potential crash points without requiring a display
"""

import sys
import ast
import traceback
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

def analyze_gui_code():
    """Analyze GUI code for potential crash points"""
    issues = []
    
    # Read the main app.py file
    app_path = Path(__file__).parent / "receipt_analyzer" / "gui" / "app.py"
    with open(app_path, 'r') as f:
        app_content = f.read()
    
    # Analyze common crash patterns
    
    # 1. Check for exception handling in processing
    if "_process_files" in app_content:
        lines = app_content.split('\n')
        in_process_files = False
        has_exception_handling = False
        
        for line in lines:
            if "def _process_files" in line:
                in_process_files = True
            elif in_process_files and line.strip().startswith("def "):
                break
            elif in_process_files and "except Exception" in line:
                has_exception_handling = True
        
        if in_process_files and has_exception_handling:
            print("✅ _process_files has exception handling")
        else:
            issues.append("❌ _process_files may lack proper exception handling")
    
    # 2. Check for proper threading cleanup
    if "processing_thread" in app_content:
        if ".join(" in app_content:
            print("✅ Thread joining found")
        else:
            issues.append("❌ No thread joining found - may cause cleanup issues")
    
    # 3. Check for GUI updates from background thread
    if "self.root.after" in app_content:
        print("✅ GUI updates use proper thread-safe method")
    else:
        issues.append("❌ Direct GUI updates from background thread may cause crashes")
    
    # 4. Check for proper cancellation handling
    if "cancel_processing" in app_content:
        print("✅ Cancellation mechanism exists")
    else:
        issues.append("❌ No cancellation mechanism found")
    
    # 5. Check for proper error display
    if "messagebox.showerror" in app_content:
        print("✅ Error message boxes implemented")
    else:
        issues.append("❌ No error message boxes found")
    
    return issues

def analyze_tab_input_run():
    """Analyze the input run tab for issues"""
    issues = []
    
    tab_path = Path(__file__).parent / "receipt_analyzer" / "gui" / "tabs" / "tab_input_run.py"
    with open(tab_path, 'r') as f:
        tab_content = f.read()
    
    # Check for proper validation
    if "validate_directories" in tab_content:
        print("✅ Directory validation exists")
    else:
        issues.append("❌ No directory validation found")
    
    # Check for proper error handling in start_processing
    if "start_processing" in tab_content and "messagebox.showerror" in tab_content:
        print("✅ Error handling in start_processing")
    else:
        issues.append("❌ start_processing may lack error handling")
    
    return issues

def analyze_imports():
    """Check for import-related issues"""
    issues = []
    
    # Test importing all GUI modules
    modules_to_test = [
        "receipt_analyzer.gui.app",
        "receipt_analyzer.gui.tabs.tab_input_run",
        "receipt_analyzer.gui.utils",
    ]
    
    for module in modules_to_test:
        try:
            __import__(module)
            print(f"✅ {module} imports successfully")
        except Exception as e:
            issues.append(f"❌ {module} import failed: {e}")
    
    return issues

def main():
    """Run the GUI code analysis"""
    print("Analyzing GUI code for potential crash points...\n")
    
    all_issues = []
    
    print("=== App.py Analysis ===")
    all_issues.extend(analyze_gui_code())
    
    print("\n=== Tab Input Run Analysis ===")
    all_issues.extend(analyze_tab_input_run())
    
    print("\n=== Import Analysis ===")
    all_issues.extend(analyze_imports())
    
    if all_issues:
        print(f"\n❌ Found {len(all_issues)} potential issues:")
        for issue in all_issues:
            print(f"  {issue}")
        
        print("\nRecommendations:")
        print("1. Ensure all background operations have proper exception handling")
        print("2. Use self.root.after() for all GUI updates from background threads")
        print("3. Implement proper thread cleanup with .join()")
        print("4. Add comprehensive error message boxes for user feedback")
        print("5. Validate all user inputs before processing")
        
        return 1
    else:
        print("\n✅ No obvious issues found in static analysis")
        return 0

if __name__ == "__main__":
    sys.exit(main())
