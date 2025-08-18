"""Main entry point for Receipt Analyzer - launches GUI by default, CLI if flags given."""

import sys
import os
from pathlib import Path
from typing import List, Optional


def setup_path():
    """Add the application directory to Python path if needed."""
    app_dir = Path(__file__).parent
    if str(app_dir) not in sys.path:
        sys.path.insert(0, str(app_dir))


def is_gui_available() -> bool:
    """Check if GUI components are available."""
    try:
        import tkinter
        return True
    except ImportError:
        return False


def should_use_gui(argv: List[str]) -> bool:
    """Determine if GUI should be used based on command line arguments."""
    # If no arguments, use GUI
    if not argv:
        return True
    
    # Check for explicit CLI/GUI flags
    if '--cli' in argv:
        return False
    
    if '--gui' in argv:
        return True
    
    # Check for other CLI-specific arguments
    cli_args = ['--in', '--input', '--out', '--output', '--check-deps']
    for arg in cli_args:
        if arg in argv:
            return False
    
    # Default to GUI if available
    return is_gui_available()


def run_gui() -> int:
    """Run the GUI application."""
    try:
        from .gui.app import ReceiptAnalyzerApp
        
        app = ReceiptAnalyzerApp()
        app.run()
        return 0
    
    except ImportError as e:
        print("Error: GUI components not available")
        print(f"Details: {e}")
        print()
        print("On Linux, try installing tkinter:")
        print("  sudo apt-get install python3-tk")
        print()
        print("Alternatively, use CLI mode:")
        print("  python -m receipt_analyzer --cli --help")
        return 1
    
    except Exception as e:
        print(f"Error: Failed to start GUI: {e}")
        return 1


def run_cli(argv: List[str]) -> int:
    """Run the CLI application."""
    try:
        from .cli import main
        return main(argv)
    
    except ImportError as e:
        print(f"Error: CLI components not available: {e}")
        return 1
    
    except Exception as e:
        print(f"Error: CLI failed: {e}")
        return 1


def print_welcome():
    """Print welcome message."""
    print("Receipt Analyzer v1.0.0")
    print("A comprehensive receipt detection and processing application")
    print()


def print_usage():
    """Print basic usage information."""
    print("Usage:")
    print("  receipt-analyzer                    # Start GUI (default)")
    print("  receipt-analyzer --gui              # Force GUI mode")
    print("  receipt-analyzer --cli --help       # Show CLI help")
    print("  receipt-analyzer --check-deps       # Check dependencies")
    print()
    print("For full CLI usage:")
    print("  receipt-analyzer --cli --help")


def main(argv: Optional[List[str]] = None) -> int:
    """
    Main entry point for Receipt Analyzer.
    
    Launches GUI by default, CLI if command-line flags are provided.
    """
    if argv is None:
        argv = sys.argv[1:]
    
    setup_path()
    
    # Handle help request
    if '--help' in argv or '-h' in argv:
        if '--cli' in argv:
            return run_cli(argv)
        else:
            print_welcome()
            print_usage()
            return 0
    
    # Handle version request
    if '--version' in argv:
        print("Receipt Analyzer v1.0.0")
        return 0
    
    # Determine interface to use
    use_gui = should_use_gui(argv)
    
    if use_gui:
        if not is_gui_available():
            print("GUI not available, falling back to CLI mode")
            print()
            return run_cli(argv)
        else:
            return run_gui()
    else:
        return run_cli(argv)


if __name__ == '__main__':
    sys.exit(main())