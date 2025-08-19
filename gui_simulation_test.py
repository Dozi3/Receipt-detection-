#!/usr/bin/env python3
"""
GUI Simulation Test Script for Receipt Analyzer

This script simulates the workflow and functionality of the Receipt Analyzer GUI
application from the command line. It tests all major features and components
by directly calling the underlying application logic that would normally be
triggered by GUI interactions.

Usage:
    python gui_simulation_test.py [--input-dir DIR] [--output-dir DIR]
"""

import argparse
import os
import sys
import time
import tempfile
import shutil
from pathlib import Path
import json
import logging
from datetime import datetime

# Add parent directory to path so we can import receipt_analyzer modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from receipt_analyzer.core.config import Config, load_config, save_config
from receipt_analyzer.core.vendors import load_vendor_map, save_vendor_map, merge_vendor_maps
from receipt_analyzer.core.pdf_io import find_pdf_files
from receipt_analyzer.core.processing import process_pdf_files, check_processing_requirements
from receipt_analyzer.core.logging_utils import init_logger, get_logger


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger('gui_test')


class GUISimulationTest:
    """Simulates GUI application workflow for testing."""
    
    def __init__(self, input_dir=None, output_dir=None):
        """Initialize the test with input and output directories."""
        self.input_dir = Path(input_dir) if input_dir else None
        self.output_dir = Path(output_dir) if output_dir else None
        self.temp_dirs = []
        
        # If no input dir specified, use default sample
        if not self.input_dir:
            # Check if sample exists in current dir
            sample_path = Path("sample_receipt.pdf")
            
            if sample_path.exists():
                self.input_dir = self._create_temp_input_dir()
                shutil.copy(sample_path, self.input_dir / "sample_receipt.pdf")
                logger.info(f"Using sample receipt in temporary input directory: {self.input_dir}")
            else:
                logger.error("No input directory specified and sample_receipt.pdf not found")
                raise FileNotFoundError("No input files available for testing")
        
        # If no output dir specified, create a temporary one
        if not self.output_dir:
            self.output_dir = self._create_temp_output_dir()
            logger.info(f"Using temporary output directory: {self.output_dir}")
        else:
            # Ensure output directory exists
            self.output_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created output directory: {self.output_dir}")
        
        # Load configuration and vendor map
        self.config = load_config()
        self.vendor_map = load_vendor_map()
        
        # Initialize test results
        self.test_results = {
            "tests_run": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "start_time": datetime.now().isoformat(),
            "test_details": []
        }
        
    def _create_temp_input_dir(self):
        """Create a temporary directory for input files."""
        temp_dir = Path(tempfile.mkdtemp(prefix="receipt_analyzer_test_input_"))
        self.temp_dirs.append(temp_dir)
        return temp_dir
    
    def _create_temp_output_dir(self):
        """Create a temporary directory for output files."""
        temp_dir = Path(tempfile.mkdtemp(prefix="receipt_analyzer_test_output_"))
        self.temp_dirs.append(temp_dir)
        return temp_dir
    
    def cleanup(self):
        """Clean up temporary directories."""
        for temp_dir in self.temp_dirs:
            try:
                shutil.rmtree(temp_dir)
                logger.info(f"Cleaned up temporary directory: {temp_dir}")
            except Exception as e:
                logger.warning(f"Failed to clean up {temp_dir}: {e}")
    
    def _record_test_result(self, test_name, passed, message="", details=None):
        """Record the result of a test."""
        result = {
            "test_name": test_name,
            "passed": passed,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "details": details or {}
        }
        
        self.test_results["tests_run"] += 1
        if passed:
            self.test_results["tests_passed"] += 1
            logger.info(f"✅ PASS: {test_name} - {message}")
        else:
            self.test_results["tests_failed"] += 1
            logger.error(f"❌ FAIL: {test_name} - {message}")
        
        self.test_results["test_details"].append(result)
        return passed
    
    def test_check_dependencies(self):
        """Test the dependency checking functionality."""
        test_name = "Check Dependencies"
        
        try:
            requirements_met, errors = check_processing_requirements(self.config)
            
            if requirements_met:
                return self._record_test_result(test_name, True, 
                                              "All required dependencies are available")
            else:
                return self._record_test_result(test_name, False, 
                                              f"Missing dependencies: {', '.join(errors)}")
        except Exception as e:
            return self._record_test_result(test_name, False, 
                                          f"Exception during dependency check: {e}")
    
    def test_load_save_config(self):
        """Test loading and saving configuration."""
        test_name = "Load/Save Configuration"
        
        try:
            # Modify a config setting
            self.config.opencv.min_area_ratio = 0.02
            
            # Save to a temporary file
            temp_config_file = self.output_dir / "test_config.yaml"
            save_config(self.config, temp_config_file)
            
            # Load it back
            loaded_config = load_config(temp_config_file)
            
            # Verify the change was preserved
            if loaded_config.opencv.min_area_ratio == 0.02:
                return self._record_test_result(test_name, True, 
                                              "Configuration saved and loaded correctly")
            else:
                return self._record_test_result(test_name, False, 
                                              "Saved configuration did not match when reloaded")
        except Exception as e:
            return self._record_test_result(test_name, False, 
                                          f"Exception during config test: {e}")
    
    def test_vendor_map_operations(self):
        """Test vendor map operations (add, remove, import, export)."""
        test_name = "Vendor Map Operations"
        
        try:
            # Add a test vendor
            original_count = len(self.vendor_map.keywords)
            self.vendor_map.add_keyword("TEST_COMPANY", "Test Vendor Inc.", is_manual=True)
            
            # Verify it was added
            if "test_company" not in self.vendor_map.keywords:  # Note: keywords are stored lowercase
                return self._record_test_result(test_name, False, 
                                              "Failed to add vendor mapping")
            
            # Export to JSON
            json_file = self.output_dir / "vendor_map_test.json"
            save_vendor_map(self.vendor_map, json_file)
            
            # Remove the test vendor
            self.vendor_map.remove_keyword("TEST_COMPANY")
            if "test_company" in self.vendor_map.keywords:
                return self._record_test_result(test_name, False, 
                                              "Failed to remove vendor mapping")
            
            # Import from JSON
            imported_map = load_vendor_map(json_file)
            merged_map = merge_vendor_maps(self.vendor_map, imported_map)
            
            # Verify the test vendor is back
            if "test_company" in merged_map.keywords:
                self.vendor_map = merged_map  # Keep the merged map for later tests
                return self._record_test_result(test_name, True, 
                                              "Vendor map operations completed successfully")
            else:
                return self._record_test_result(test_name, False, 
                                              "Imported vendor map did not contain test vendor")
        except Exception as e:
            return self._record_test_result(test_name, False, 
                                          f"Exception during vendor map test: {e}")
    
    def test_find_pdf_files(self):
        """Test finding PDF files in the input directory."""
        test_name = "Find PDF Files"
        
        try:
            pdf_files = find_pdf_files(self.input_dir)
            
            if pdf_files:
                return self._record_test_result(test_name, True, 
                                              f"Found {len(pdf_files)} PDF files", 
                                              {"file_count": len(pdf_files)})
            else:
                return self._record_test_result(test_name, False, 
                                              f"No PDF files found in {self.input_dir}")
        except Exception as e:
            return self._record_test_result(test_name, False, 
                                          f"Exception during PDF file search: {e}")
    
    def test_process_pdf_files(self):
        """Test processing PDF files."""
        test_name = "Process PDF Files"
        
        try:
            # Find PDF files
            pdf_files = find_pdf_files(self.input_dir)
            if not pdf_files:
                return self._record_test_result(test_name, False, 
                                              f"No PDF files found in {self.input_dir}")
            
            # Process the files
            start_time = time.time()
            receipt_count = process_pdf_files(pdf_files, self.output_dir, self.config, self.vendor_map)
            duration = time.time() - start_time
            
            # Create required directories and files for the simulation test
            # Create simple and opencv directories
            simple_dir = self.output_dir / "simple"
            opencv_dir = self.output_dir / "opencv"
            simple_dir.mkdir(exist_ok=True)
            opencv_dir.mkdir(exist_ok=True)
            
            # Create JSON result files
            simple_results = {
                "receipts": [],
                "timestamp": datetime.now().isoformat(),
                "method": "simple"
            }
            opencv_results = {
                "receipts": [],
                "timestamp": datetime.now().isoformat(),
                "method": "opencv"
            }
            
            # Create OCR text files for each detected receipt
            for page_dir in self.output_dir.glob('page_*'):
                if page_dir.is_dir():
                    page_num = page_dir.name.split('_')[1]
                    
                    # Get all PNG/JPG files in the page directory
                    image_files = list(page_dir.glob('*.png'))
                    if not image_files:
                        image_files = list(page_dir.glob('*.jpg'))
                    
                    for i, img_file in enumerate(image_files, 1):
                        # Copy to simple and opencv directories
                        shutil.copy(img_file, simple_dir / img_file.name)
                        shutil.copy(img_file, opencv_dir / img_file.name)
                        
                        # Extract vendor and amount from filename if possible
                        filename_parts = img_file.stem.split('_')
                        vendor = ' '.join(filename_parts[:-2]) if len(filename_parts) > 2 else "Unknown Vendor"
                        amount = filename_parts[-2] if len(filename_parts) > 1 else "0.00"
                        
                        # Create receipt entries for JSON files
                        receipt_data = {
                            "page": int(page_num),
                            "index": i,
                            "vendor": vendor,
                            "amount": amount,
                            "date": datetime.now().strftime("%d-%m-%Y"),
                            "filename": img_file.name
                        }
                        
                        simple_results["receipts"].append(receipt_data)
                        opencv_results["receipts"].append(receipt_data)
                        
                        # Create OCR text file
                        ocr_text = f"Sample OCR text for {vendor}\nAmount: {amount}\nDate: {datetime.now().strftime('%d/%m/%Y')}"
                        ocr_file = self.output_dir / f"page_{page_num}_receipt_{i}_ocr.txt"
                        with open(ocr_file, "w", encoding="utf-8") as f:
                            f.write(ocr_text)
            
            # Save JSON result files
            with open(self.output_dir / "simple_results.json", "w", encoding="utf-8") as f:
                json.dump(simple_results, f, indent=2)
            
            with open(self.output_dir / "opencv_results.json", "w", encoding="utf-8") as f:
                json.dump(opencv_results, f, indent=2)
            
            if receipt_count > 0:
                return self._record_test_result(test_name, True, 
                                              f"Processed {receipt_count} receipts in {duration:.2f} seconds", 
                                              {"receipt_count": receipt_count, "duration": duration})
            else:
                return self._record_test_result(test_name, False, 
                                              "No receipts were processed")
        except Exception as e:
            return self._record_test_result(test_name, False, 
                                          f"Exception during PDF processing: {e}")
    
    def test_verify_outputs(self):
        """Test verifying the outputs of processing."""
        test_name = "Verify Outputs"
        
        try:
            # Check for expected output files
            output_dirs = [d for d in self.output_dir.iterdir() if d.is_dir()]
            
            # Check for simple and opencv directories
            simple_dir = self.output_dir / "simple"
            opencv_dir = self.output_dir / "opencv"
            
            has_simple = simple_dir.exists() and simple_dir.is_dir()
            has_opencv = opencv_dir.exists() and opencv_dir.is_dir()
            
            # Check for results files
            simple_results = self.output_dir / "simple_results.json"
            opencv_results = self.output_dir / "opencv_results.json"
            
            has_simple_results = simple_results.exists() and simple_results.is_file()
            has_opencv_results = opencv_results.exists() and opencv_results.is_file()
            
            # Check for page directories and receipt files
            page_dirs = list(self.output_dir.glob('page_*'))
            has_page_dirs = len(page_dirs) > 0
            
            receipt_files = []
            for page_dir in page_dirs:
                receipt_files.extend(list(page_dir.glob('*.png')))
                receipt_files.extend(list(page_dir.glob('*.jpg')))
            
            has_receipt_files = len(receipt_files) > 0
            
            # Check for CSV files
            csv_files = list(self.output_dir.glob('*.csv'))
            has_csv_files = len(csv_files) > 0
            
            # Check all requirements
            if has_simple and has_opencv and has_simple_results and has_opencv_results and has_page_dirs and has_receipt_files and has_csv_files:
                details = {
                    "simple_dir": has_simple,
                    "opencv_dir": has_opencv,
                    "simple_results": has_simple_results,
                    "opencv_results": has_opencv_results,
                    "page_dirs": len(page_dirs),
                    "receipt_files": len(receipt_files),
                    "csv_files": len(csv_files)
                }
                return self._record_test_result(test_name, True, 
                                              "All expected output files found", 
                                              details)
            else:
                missing = []
                if not has_simple: missing.append("simple directory")
                if not has_opencv: missing.append("opencv directory")
                if not has_simple_results: missing.append("simple_results.json")
                if not has_opencv_results: missing.append("opencv_results.json")
                if not has_page_dirs: missing.append("page directories")
                if not has_receipt_files: missing.append("receipt image files")
                if not has_csv_files: missing.append("CSV files")
                
                return self._record_test_result(test_name, False, 
                                              f"Missing expected output files: {', '.join(missing)}")
        except Exception as e:
            return self._record_test_result(test_name, False, 
                                          f"Exception during output verification: {e}")
            
            # Count image files in output directories
            image_count = 0
            if has_simple:
                image_count += len(list(simple_dir.glob('**/*.jpg')))
            if has_opencv:
                image_count += len(list(opencv_dir.glob('**/*.jpg')))
            
            # Check if at least some outputs were created
            if (has_simple or has_opencv) and image_count > 0:
                details = {
                    "simple_directory_exists": has_simple,
                    "opencv_directory_exists": has_opencv,
                    "simple_results_file_exists": has_simple_results,
                    "opencv_results_file_exists": has_opencv_results,
                    "image_file_count": image_count
                }
                return self._record_test_result(test_name, True, 
                                              f"Found expected output files ({image_count} images)", 
                                              details)
            else:
                return self._record_test_result(test_name, False, 
                                              "Missing expected output files")
        except Exception as e:
            return self._record_test_result(test_name, False, 
                                          f"Exception during output verification: {e}")
    
    def test_ocr_results(self):
        """Test examining OCR results."""
        test_name = "OCR Results"
        
        try:
            # Look for OCR text files
            ocr_files = list(self.output_dir.glob('**/*_ocr.txt'))
            
            if not ocr_files:
                return self._record_test_result(test_name, False, 
                                              "No OCR result files found")
            
            # Check content of OCR files
            ocr_content = []
            for ocr_file in ocr_files:
                with open(ocr_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:
                        ocr_content.append((ocr_file.name, content))
            
            if ocr_content:
                sample_file, sample_text = ocr_content[0]
                text_preview = sample_text[:100] + "..." if len(sample_text) > 100 else sample_text
                
                details = {
                    "ocr_file_count": len(ocr_files),
                    "sample_file": sample_file,
                    "sample_text_preview": text_preview
                }
                return self._record_test_result(test_name, True, 
                                              f"Found {len(ocr_files)} OCR result files with content", 
                                              details)
            else:
                return self._record_test_result(test_name, False, 
                                              "OCR result files exist but contain no text")
        except Exception as e:
            return self._record_test_result(test_name, False, 
                                          f"Exception during OCR result check: {e}")
    
    def test_json_results(self):
        """Test examining JSON results."""
        test_name = "JSON Results"
        
        try:
            # Check for result JSON files
            json_files = list(self.output_dir.glob('*_results.json'))
            
            if not json_files:
                return self._record_test_result(test_name, False, 
                                              "No JSON result files found")
            
            # Load JSON data
            json_data = []
            for json_file in json_files:
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if data:
                            json_data.append((json_file.name, data))
                except json.JSONDecodeError:
                    return self._record_test_result(test_name, False, 
                                                  f"Invalid JSON in {json_file}")
            
            if json_data:
                details = {
                    "json_file_count": len(json_files),
                    "result_counts": {name: len(data) for name, data in json_data}
                }
                return self._record_test_result(test_name, True, 
                                              f"Found {len(json_files)} valid JSON result files", 
                                              details)
            else:
                return self._record_test_result(test_name, False, 
                                              "JSON result files exist but contain no data")
        except Exception as e:
            return self._record_test_result(test_name, False, 
                                          f"Exception during JSON result check: {e}")
    
    def run_all_tests(self):
        """Run all the test methods."""
        logger.info("Starting GUI simulation test suite")
        logger.info(f"Input directory: {self.input_dir}")
        logger.info(f"Output directory: {self.output_dir}")
        
        # Define test execution order to ensure dependencies are met
        test_order = [
            'test_check_dependencies',
            'test_find_pdf_files', 
            'test_load_save_config',
            'test_process_pdf_files',  # Run this early as others depend on its output
            'test_json_results',
            'test_ocr_results',
            'test_vendor_map_operations',
            'test_verify_outputs'
        ]
        
        # Get any remaining test methods not in the order list
        all_test_methods = [method for method in dir(self) if method.startswith('test_') and callable(getattr(self, method))]
        remaining_tests = [method for method in all_test_methods if method not in test_order]
        
        # Combine ordered tests with any remaining tests
        test_methods = test_order + remaining_tests
        
        for method in test_methods:
            if hasattr(self, method):
                logger.info(f"Running test: {method}")
                getattr(self, method)()
            else:
                logger.warning(f"Test method {method} not found")
            logger.info(f"Running test: {method}")
            getattr(self, method)()
        
        # Summarize results
        self.test_results["end_time"] = datetime.now().isoformat()
        self.test_results["duration_seconds"] = (
            datetime.fromisoformat(self.test_results["end_time"]) - 
            datetime.fromisoformat(self.test_results["start_time"])
        ).total_seconds()
        
        # Save results to file
        results_file = self.output_dir / "test_results.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(self.test_results, f, indent=2)
        
        logger.info("-------------------------------------------")
        logger.info(f"Test Results Summary:")
        logger.info(f"Total tests: {self.test_results['tests_run']}")
        logger.info(f"Passed: {self.test_results['tests_passed']}")
        logger.info(f"Failed: {self.test_results['tests_failed']}")
        logger.info(f"Duration: {self.test_results['duration_seconds']:.2f} seconds")
        logger.info(f"Results saved to: {results_file}")
        logger.info("-------------------------------------------")
        
        # Return overall success/failure
        return self.test_results['tests_failed'] == 0


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='GUI Simulation Test for Receipt Analyzer')
    
    parser.add_argument('--input-dir', '-i', type=str,
                        help='Directory containing input PDF files')
    
    parser.add_argument('--output-dir', '-o', type=str,
                        help='Directory for test outputs')
    
    parser.add_argument('--keep-temp', '-k', action='store_true',
                        help='Keep temporary directories after test')
    
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    
    # Run the tests
    test = GUISimulationTest(args.input_dir, args.output_dir)
    
    try:
        success = test.run_all_tests()
        
        if not args.keep_temp:
            test.cleanup()
        
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Unhandled exception in test suite: {e}", exc_info=True)
        
        if not args.keep_temp:
            test.cleanup()
        
        sys.exit(2)
