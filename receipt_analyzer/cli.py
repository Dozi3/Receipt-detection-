"""Command-line interface for receipt analyzer."""

import argparse
import sys
from pathlib import Path
from typing import Optional, List

from .core.config import Config, load_config, save_config, merge_cli_args
from .core.logging_utils import init_logger, get_logger, log_info, log_fail
from .core.pdf_io import check_dependencies, find_pdf_files
from .core.detection_opencv import check_opencv_available
from .core.ocr import check_tesseract_available
from .core.vendors import load_vendor_map


def check_all_dependencies() -> bool:
    """Check all dependencies and report issues."""
    logger = get_logger()
    all_ok = True
    
    # Check required dependencies
    pdf_ok, pdf_messages = check_dependencies()
    if not pdf_ok:
        for msg in pdf_messages:
            if "required" in msg.lower():
                log_fail(msg)
                all_ok = False
            else:
                logger.warn(msg)
    
    # Check Tesseract
    tesseract_ok, tesseract_msg = check_tesseract_available()
    if not tesseract_ok:
        log_fail(tesseract_msg)
        all_ok = False
    else:
        log_info(tesseract_msg)
    
    # Check OpenCV (only warn if missing)
    if not check_opencv_available():
        logger.warn("OpenCV not available - OpenCV detection method unavailable")
    
    return all_ok


def create_argument_parser() -> argparse.ArgumentParser:
    """Create the command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog='receipt-analyzer',
        description='Receipt detection and processing application',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  receipt-analyzer --in ./pdfs --out ./output
  receipt-analyzer --in ./pdfs --out ./output --method opencv --png
  receipt-analyzer --in ./pdfs --out ./output --vendor-map ./my_vendors.json
  receipt-analyzer --gui  # Force GUI mode (default anyway)
        """
    )
    
    # Input/Output
    parser.add_argument(
        '--in', '--input', dest='input_dir',
        type=Path, required=False,
        help='Input directory containing PDF files'
    )
    
    parser.add_argument(
        '--out', '--output', dest='output_dir',
        type=Path, required=False,
        help='Output directory for processed receipts'
    )
    
    # Processing options
    parser.add_argument(
        '--method', choices=['simple', 'opencv'],
        default='opencv',
        help='Detection method (default: opencv)'
    )
    
    # Output format
    parser.add_argument(
        '--png', action='store_true',
        help='Force PNG output format'
    )
    
    parser.add_argument(
        '--quality', type=int, default=85, metavar='N',
        help='JPEG quality (1-100, default: 85). Ignored if --png is used'
    )
    
    parser.add_argument(
        '--max-edge', type=int, default=1000, metavar='N',
        help='Maximum edge size in pixels for output images (default: 1000)'
    )
    
    # OCR options
    parser.add_argument(
        '--lang', default='eng',
        help='OCR language (default: eng)'
    )
    
    # Vendor mapping
    parser.add_argument(
        '--vendor-map', type=Path, metavar='PATH',
        help='Path to vendor mapping JSON file'
    )
    
    # ZIP option
    parser.add_argument(
        '--no-zip', action='store_true',
        help='Disable per-page ZIP files'
    )
    
    # Interface selection
    parser.add_argument(
        '--gui', action='store_true',
        help='Force GUI mode (default behavior)'
    )
    
    parser.add_argument(
        '--cli', action='store_true',
        help='Force CLI mode'
    )
    
    # Debugging
    parser.add_argument(
        '--check-deps', action='store_true',
        help='Check dependencies and exit'
    )
    
    parser.add_argument(
        '--config', type=Path, metavar='PATH',
        help='Path to configuration file'
    )
    
    parser.add_argument(
        '--verbose', '-v', action='store_true',
        help='Enable verbose output'
    )
    
    return parser


def validate_cli_args(args) -> Optional[str]:
    """Validate command-line arguments."""
    # If CLI mode is requested, input and output are required
    if args.cli:
        if not args.input_dir:
            return "CLI mode requires --in (input directory)"
        
        if not args.output_dir:
            return "CLI mode requires --out (output directory)"
        
        if not args.input_dir.exists():
            return f"Input directory does not exist: {args.input_dir}"
        
        if not args.input_dir.is_dir():
            return f"Input path is not a directory: {args.input_dir}"
    
    # Validate quality range
    if not 1 <= args.quality <= 100:
        return "Quality must be between 1 and 100"
    
    # Validate max edge
    if args.max_edge < 100:
        return "Max edge must be at least 100 pixels"
    
    # Validate vendor map file
    if args.vendor_map and not args.vendor_map.exists():
        return f"Vendor map file does not exist: {args.vendor_map}"
    
    # Validate config file
    if args.config and not args.config.exists():
        return f"Config file does not exist: {args.config}"
    
    return None


def run_cli_mode(args, config: Config) -> int:
    """Run the application in CLI mode."""
    from .core.processing import process_pdf_files
    
    logger = get_logger()
    
    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize logging with file output
    log_file = args.output_dir / "processing.log"
    init_logger(log_file)
    
    log_info(f"Receipt Analyzer CLI - Starting processing")
    log_info(f"Input directory: {args.input_dir}")
    log_info(f"Output directory: {args.output_dir}")
    log_info(f"Detection method: {config.detection_method}")
    log_info(f"Output format: {config.output.format}")
    
    # Check dependencies
    if not check_all_dependencies():
        log_fail("Missing required dependencies - cannot continue")
        return 1
    
    # Check OpenCV availability for opencv method
    if config.detection_method == 'opencv' and not check_opencv_available():
        log_fail("OpenCV detection method selected but OpenCV not available")
        return 1
    
    # Find PDF files
    pdf_files = find_pdf_files(args.input_dir)
    if not pdf_files:
        log_fail(f"No PDF files found in {args.input_dir}")
        return 1
    
    log_info(f"Found {len(pdf_files)} PDF files to process")
    
    # Load vendor map
    vendor_map = None
    if args.vendor_map:
        from .core.vendors import load_vendor_map
        vendor_map = load_vendor_map(args.vendor_map)
        log_info(f"Loaded vendor map with {len(vendor_map.keywords)} keywords")
    
    try:
        # Process all PDF files
        success_count = 0
        total_receipts = 0
        
        for pdf_path in pdf_files:
            try:
                receipt_count = process_pdf_files([pdf_path], args.output_dir, config, vendor_map)
                if receipt_count > 0:
                    success_count += 1
                    total_receipts += receipt_count
                    log_info(f"Successfully processed {pdf_path.name}: {receipt_count} receipts")
                else:
                    logger.warn(f"No receipts extracted from {pdf_path.name}")
            
            except Exception as e:
                logger.fail(f"Failed to process {pdf_path.name}: {e}")
        
        # Summary
        log_info(f"Processing complete: {success_count}/{len(pdf_files)} PDFs processed, {total_receipts} total receipts")
        
        if success_count > 0:
            log_info(f"Output files saved to: {args.output_dir}")
            log_info("Generated files:")
            log_info("  - processing.log (this log)")
            log_info("  - freeagent.csv (for accounting import)")
            log_info("  - receipts_index.csv (detailed index)")
            
            return 0
        else:
            log_fail("No PDF files were processed successfully")
            return 1
    
    except KeyboardInterrupt:
        log_info("Processing interrupted by user")
        return 130
    
    except Exception as e:
        log_fail(f"Unexpected error during processing: {e}")
        return 1


def run_gui_mode() -> int:
    """Run the application in GUI mode."""
    try:
        from .gui.app import ReceiptAnalyzerApp
        app = ReceiptAnalyzerApp()
        app.run()
        return 0
    
    except ImportError as e:
        print(f"GUI not available: {e}")
        print("Try installing tkinter: sudo apt-get install python3-tk")
        return 1
    
    except Exception as e:
        print(f"GUI failed to start: {e}")
        return 1


def main(argv: Optional[List[str]] = None) -> int:
    """Main entry point for the CLI."""
    parser = create_argument_parser()
    args = parser.parse_args(argv)
    
    # Handle dependency check
    if args.check_deps:
        init_logger()
        print("Checking dependencies...")
        if check_all_dependencies():
            print("All required dependencies are available.")
            return 0
        else:
            print("Some required dependencies are missing.")
            return 1
    
    # Load configuration
    config = load_config(args.config)
    
    # Merge CLI arguments into config
    config = merge_cli_args(config, vars(args))
    
    # Validate arguments
    validation_error = validate_cli_args(args)
    if validation_error:
        print(f"Error: {validation_error}", file=sys.stderr)
        parser.print_help()
        return 1
    
    # Determine which mode to use
    if args.cli:
        return run_cli_mode(args, config)
    else:
        # Default to GUI mode
        return run_gui_mode()


if __name__ == '__main__':
    sys.exit(main())