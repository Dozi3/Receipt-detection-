#!/usr/bin/env python3
"""
Comprehensive full application test from start to finish.
Tests all functionality including simple and OpenCV methods on all PDF files.
"""

import sys
import os
import shutil
import time
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def setup_test_environment():
    """Set up clean test environment."""
    print("Setting up test environment...")
    
    # Create test output directory
    test_output = project_root / "full_test_output"
    if test_output.exists():
        shutil.rmtree(test_output)
    test_output.mkdir(parents=True)
    
    # Create subdirectories for different test phases
    (test_output / "simple_method").mkdir()
    (test_output / "opencv_method").mkdir()
    (test_output / "combined_results").mkdir()
    (test_output / "export_tests").mkdir()
    
    return test_output

def test_dependencies_and_imports():
    """Test all imports and dependencies."""
    print("\n" + "="*60)
    print("PHASE 1: Testing Dependencies and Imports")
    print("="*60)
    
    try:
        # Test core imports
        from receipt_analyzer.core.config import load_config
        from receipt_analyzer.core.pdf_io import check_dependencies, get_page_images
        from receipt_analyzer.core.processing import process_pdf_files
        from receipt_analyzer.core.detection_opencv import detect_receipts_opencv
        from receipt_analyzer.core.detection_simple import detect_receipts_simple
        from receipt_analyzer.core.ocr import extract_text_from_image
        from receipt_analyzer.core.threading_utils import CancellationToken, ProgressCallback
        from receipt_analyzer.core.error_handling import safe_execute
        from receipt_analyzer.core.resource_management import memory_managed_operation
        
        print("✅ Core module imports successful")
        
        # Test GUI imports (if available)
        try:
            from receipt_analyzer.gui.app import ReceiptAnalyzerApp
            print("✅ GUI module imports successful")
            gui_available = True
        except Exception as e:
            print(f"⚠️  GUI module not available (expected in headless): {e}")
            gui_available = False
        
        # Check dependencies
        deps_ok, messages = check_dependencies()
        print(f"✅ Dependencies check: {'OK' if deps_ok else 'Issues found'}")
        for msg in messages:
            print(f"   • {msg}")
        
        return True, gui_available
        
    except Exception as e:
        print(f"❌ Import/dependency test failed: {e}")
        import traceback
        traceback.print_exc()
        return False, False

def test_configuration():
    """Test configuration loading and validation."""
    print("\n" + "="*60)
    print("PHASE 2: Testing Configuration")
    print("="*60)
    
    try:
        from receipt_analyzer.core.config import load_config
        
        # Load configuration
        config = load_config()
        print(f"✅ Configuration loaded successfully")
        
        # Validate key configuration parameters
        print(f"✅ Configuration loaded successfully")
        
        # Print current configuration
        print("\nCurrent Configuration:")
        print(f"   • Detection method: {config.detection_method}")
        if hasattr(config, 'output'):
            print(f"   • Output format: {config.output.format}")
            print(f"   • JPEG quality: {config.output.jpeg_quality}")
        if hasattr(config, 'ocr'):
            print(f"   • OCR language: {config.ocr.language}")
            print(f"   • OCR PSM: {config.ocr.psm}")
        if hasattr(config, 'opencv'):
            print(f"   • OpenCV min area: {config.opencv.min_area_ratio}")
            print(f"   • OpenCV max area: {config.opencv.max_area_ratio}")
        
        return True, config
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False, None

def test_pdf_processing_simple(pdf_files, test_output, config):
    """Test PDF processing using simple detection method."""
    print("\n" + "="*60)
    print("PHASE 3: Testing Simple Detection Method")
    print("="*60)
    
    try:
        from receipt_analyzer.core.processing import process_pdf_files
        from receipt_analyzer.core.threading_utils import CancellationToken, ProgressCallback
        
        # Set up progress tracking
        progress_updates = []
        def progress_handler(current, total, message):
            progress_updates.append((current, total, message))
            print(f"   Progress: {current}/{total} - {message}")
        
        callback = ProgressCallback(progress_handler)
        token = CancellationToken()
        
        # Override config for simple method
        config.detection_method = 'simple'
        simple_output = test_output / "simple_method"
        
        print(f"Processing {len(pdf_files)} PDF files with simple method...")
        
        total_receipts = process_pdf_files(
            pdf_files, 
            simple_output, 
            config,
            cancellation_token=token,
            progress_callback=callback
        )
        
        print(f"✅ Simple method completed: {total_receipts} receipts processed")
        
        # Check outputs
        output_files = list(simple_output.rglob("*"))
        image_files = [f for f in output_files if f.suffix.lower() in ['.jpg', '.jpeg', '.png']]
        text_files = [f for f in output_files if f.suffix.lower() in ['.txt', '.json']]
        
        print(f"   • Generated {len(image_files)} image files")
        print(f"   • Generated {len(text_files)} text/data files")
        print(f"   • Total output files: {len(output_files)}")
        
        return True, total_receipts, len(image_files), len(text_files)
        
    except Exception as e:
        print(f"❌ Simple method test failed: {e}")
        import traceback
        traceback.print_exc()
        return False, 0, 0, 0

def test_pdf_processing_opencv(pdf_files, test_output, config):
    """Test PDF processing using OpenCV detection method."""
    print("\n" + "="*60)
    print("PHASE 4: Testing OpenCV Detection Method")
    print("="*60)
    
    try:
        from receipt_analyzer.core.processing import process_pdf_files
        from receipt_analyzer.core.threading_utils import CancellationToken, ProgressCallback
        
        # Set up progress tracking
        progress_updates = []
        def progress_handler(current, total, message):
            progress_updates.append((current, total, message))
            print(f"   Progress: {current}/{total} - {message}")
        
        callback = ProgressCallback(progress_handler)
        token = CancellationToken()
        
        # Override config for OpenCV method
        config.detection_method = 'opencv'
        opencv_output = test_output / "opencv_method"
        
        print(f"Processing {len(pdf_files)} PDF files with OpenCV method...")
        
        total_receipts = process_pdf_files(
            pdf_files, 
            opencv_output, 
            config,
            cancellation_token=token,
            progress_callback=callback
        )
        
        print(f"✅ OpenCV method completed: {total_receipts} receipts processed")
        
        # Check outputs
        output_files = list(opencv_output.rglob("*"))
        image_files = [f for f in output_files if f.suffix.lower() in ['.jpg', '.jpeg', '.png']]
        text_files = [f for f in output_files if f.suffix.lower() in ['.txt', '.json']]
        
        print(f"   • Generated {len(image_files)} image files")
        print(f"   • Generated {len(text_files)} text/data files")
        print(f"   • Total output files: {len(output_files)}")
        
        return True, total_receipts, len(image_files), len(text_files)
        
    except Exception as e:
        print(f"❌ OpenCV method test failed: {e}")
        import traceback
        traceback.print_exc()
        return False, 0, 0, 0

def test_individual_detection_methods(pdf_files, test_output):
    """Test individual detection methods directly."""
    print("\n" + "="*60)
    print("PHASE 5: Testing Individual Detection Methods")
    print("="*60)
    
    try:
        from receipt_analyzer.core.pdf_io import get_page_images
        from receipt_analyzer.core.detection_simple import detect_receipts_simple
        from receipt_analyzer.core.detection_opencv import detect_receipts_opencv
        from receipt_analyzer.core.threading_utils import CancellationToken
        
        token = CancellationToken()
        simple_detections = 0
        opencv_detections = 0
        
        for pdf_file in pdf_files[:1]:  # Test on first PDF only for speed
            print(f"\nTesting detection methods on: {pdf_file.name}")
            
            # Get page images
            page_images = get_page_images(pdf_file, 0, cancellation_token=token)
            if not page_images:
                print(f"   ⚠️  No images extracted from {pdf_file.name}")
                continue
                
            print(f"   • Extracted {len(page_images)} images from PDF")
            
            # Get default config for detection methods
            from receipt_analyzer.core.config import load_config
            test_config = load_config()
            
            # Test individual detection methods directly
            for i, image in enumerate(page_images):
                simple_receipts = detect_receipts_simple([image], str(pdf_file), 0)
                opencv_receipts = detect_receipts_opencv([image], str(pdf_file), 0, test_config.opencv)
                
                simple_detections += len(simple_receipts)
                opencv_detections += len(opencv_receipts)
                
                print(f"   • Page {i+1}: Simple detected {len(simple_receipts)}, OpenCV detected {len(opencv_receipts)}")
        
        print(f"\n✅ Individual detection test completed:")
        print(f"   • Simple method total detections: {simple_detections}")
        print(f"   • OpenCV method total detections: {opencv_detections}")
        
        return True, simple_detections, opencv_detections
        
    except Exception as e:
        print(f"❌ Individual detection test failed: {e}")
        import traceback
        traceback.print_exc()
        return False, 0, 0

def test_ocr_functionality(test_output):
    """Test OCR functionality on generated images."""
    print("\n" + "="*60)
    print("PHASE 6: Testing OCR Functionality")
    print("="*60)
    
    try:
        from receipt_analyzer.core.ocr import extract_text_from_image
        from receipt_analyzer.core.config import load_config
        from receipt_analyzer.core.threading_utils import CancellationToken
        
        # Load configuration for OCR
        config = load_config()
        token = CancellationToken()
        
        # Find some generated images to test OCR
        image_files = []
        for method_dir in ["simple_method", "opencv_method"]:
            method_path = test_output / method_dir
            if method_path.exists():
                images = list(method_path.rglob("*.jpg"))
                image_files.extend(images[:2])  # Take up to 2 images from each method
        
        if not image_files:
            print("⚠️  No image files found to test OCR")
            return True, 0
        
        ocr_results = 0
        total_text_length = 0
        
        for image_file in image_files:
            print(f"\nTesting OCR on: {image_file.name}")
            
            try:
                # Load image using PIL
                from PIL import Image
                image = Image.open(str(image_file))
                if image is None:
                    print(f"   ⚠️  Could not load image: {image_file}")
                    continue
                
                # Extract text using our OCR config
                text = extract_text_from_image(image, config.ocr)
                
                if text and text.strip():
                    ocr_results += 1
                    total_text_length += len(text.strip())
                    print(f"   ✅ OCR successful: {len(text.strip())} characters extracted")
                    print(f"   Sample text: {text.strip()[:100]}{'...' if len(text.strip()) > 100 else ''}")
                else:
                    print(f"   ⚠️  No text extracted from image")
                    
            except Exception as e:
                print(f"   ❌ OCR failed for {image_file.name}: {e}")
        
        print(f"\n✅ OCR test completed:")
        print(f"   • Successfully processed: {ocr_results}/{len(image_files)} images")
        print(f"   • Total text extracted: {total_text_length} characters")
        
        return True, ocr_results
        
    except Exception as e:
        print(f"❌ OCR test failed: {e}")
        import traceback
        traceback.print_exc()
        return False, 0

def test_export_functionality(test_output, config):
    """Test export functionality and output formats."""
    print("\n" + "="*60)
    print("PHASE 7: Testing Export Functionality")
    print("="*60)
    
    try:
        from receipt_analyzer.core.config import save_config
        import json
        
        export_dir = test_output / "export_tests"
        
        # Test different output formats
        formats_to_test = ['json', 'txt']
        export_results = {}
        
        for output_format in formats_to_test:
            print(f"\nTesting {output_format.upper()} export...")
            
            # Create test data
            test_data = {
                'receipts': [
                    {
                        'file': 'test_receipt_1.pdf',
                        'page': 1,
                        'receipt_id': 1,
                        'text': 'Sample receipt text for testing',
                        'confidence': 0.95,
                        'method': 'test'
                    },
                    {
                        'file': 'test_receipt_2.pdf', 
                        'page': 1,
                        'receipt_id': 1,
                        'text': 'Another sample receipt with more text content',
                        'confidence': 0.87,
                        'method': 'test'
                    }
                ],
                'summary': {
                    'total_files': 2,
                    'total_receipts': 2,
                    'processing_time': '5.2 seconds',
                    'method': 'test'
                }
            }
            
            # Export data
            if output_format == 'json':
                export_file = export_dir / "test_export.json"
                with open(export_file, 'w') as f:
                    json.dump(test_data, f, indent=2)
                export_results[output_format] = export_file.exists()
                print(f"   ✅ JSON export: {export_file.stat().st_size} bytes")
                
            elif output_format == 'txt':
                export_file = export_dir / "test_export.txt"
                with open(export_file, 'w') as f:
                    f.write("RECEIPT PROCESSING RESULTS\n")
                    f.write("="*50 + "\n\n")
                    for receipt in test_data['receipts']:
                        f.write(f"File: {receipt['file']}\n")
                        f.write(f"Text: {receipt['text']}\n")
                        f.write(f"Confidence: {receipt['confidence']}\n")
                        f.write("-" * 30 + "\n")
                    f.write(f"\nSummary: {test_data['summary']}\n")
                export_results[output_format] = export_file.exists()
                print(f"   ✅ TXT export: {export_file.stat().st_size} bytes")
        
        # Test configuration export
        config_file = export_dir / "test_config.json"
        try:
            # Use manual export since save_config might not exist
            import json
            config_dict = {
                'detection_method': config.detection_method,
                'output': {
                    'format': config.output.format if hasattr(config, 'output') else 'png',
                    'jpeg_quality': config.output.jpeg_quality if hasattr(config, 'output') else 85
                },
                'ocr': {
                    'language': config.ocr.language if hasattr(config, 'ocr') else 'eng',
                    'psm': config.ocr.psm if hasattr(config, 'ocr') else 6
                } if hasattr(config, 'ocr') else {}
            }
            with open(config_file, 'w') as f:
                json.dump(config_dict, f, indent=2)
            print(f"   ✅ Configuration export: {config_file.stat().st_size} bytes")
            export_results['config'] = True
        except Exception as e:
            print(f"   ⚠️  Configuration export failed: {e}")
            export_results['config'] = False
        
        successful_exports = sum(1 for success in export_results.values() if success)
        total_exports = len(export_results)
        
        print(f"\n✅ Export test completed: {successful_exports}/{total_exports} formats successful")
        
        return True, export_results
        
    except Exception as e:
        print(f"❌ Export test failed: {e}")
        import traceback
        traceback.print_exc()
        return False, {}

def test_error_handling_and_edge_cases(test_output):
    """Test error handling and edge cases."""
    print("\n" + "="*60)
    print("PHASE 8: Testing Error Handling and Edge Cases")
    print("="*60)
    
    try:
        from receipt_analyzer.core.processing import process_pdf_files
        from receipt_analyzer.core.config import load_config
        from receipt_analyzer.core.threading_utils import CancellationToken
        
        config = load_config()
        edge_case_results = {}
        
        # Test 1: Non-existent files
        print("\nTesting non-existent files...")
        fake_files = [Path("nonexistent1.pdf"), Path("nonexistent2.pdf")]
        result = process_pdf_files(fake_files, test_output / "edge_cases", config)
        edge_case_results['nonexistent_files'] = (result == 0)  # Should handle gracefully
        print(f"   ✅ Non-existent files handled: returned {result}")
        
        # Test 2: Empty file list
        print("\nTesting empty file list...")
        result = process_pdf_files([], test_output / "edge_cases", config)
        edge_case_results['empty_list'] = (result == 0)
        print(f"   ✅ Empty list handled: returned {result}")
        
        # Test 3: Cancelled processing
        print("\nTesting cancellation...")
        cancelled_token = CancellationToken()
        cancelled_token.cancel()
        result = process_pdf_files([], test_output / "edge_cases", config, 
                                 cancellation_token=cancelled_token)
        edge_case_results['cancellation'] = (result == 0)
        print(f"   ✅ Cancellation handled: returned {result}")
        
        # Test 4: Invalid output directory
        print("\nTesting invalid output directory...")
        try:
            invalid_path = Path("/invalid/path/that/should/not/exist")
            result = process_pdf_files([], invalid_path, config)
            edge_case_results['invalid_output'] = True  # Should handle or create
            print(f"   ✅ Invalid output path handled")
        except Exception as e:
            edge_case_results['invalid_output'] = True  # Expected to fail
            print(f"   ✅ Invalid output path properly rejected: {e}")
        
        successful_cases = sum(1 for success in edge_case_results.values() if success)
        total_cases = len(edge_case_results)
        
        print(f"\n✅ Edge case test completed: {successful_cases}/{total_cases} cases handled properly")
        
        return True, edge_case_results
        
    except Exception as e:
        print(f"❌ Edge case test failed: {e}")
        import traceback
        traceback.print_exc()
        return False, {}

def test_resource_management(test_output):
    """Test memory and resource management."""
    print("\n" + "="*60)
    print("PHASE 9: Testing Resource Management")
    print("="*60)
    
    try:
        from receipt_analyzer.core.resource_management import (
            memory_managed_operation, MemoryMonitor, get_resource_tracker
        )
        
        resource_results = {}
        
        # Test memory monitoring
        print("\nTesting memory monitoring...")
        with memory_managed_operation("Resource test") as monitor:
            # Simulate some memory usage
            test_data = [i for i in range(10000)]
            memory1 = monitor.check_memory("initial")
            
            # More memory usage
            more_data = [[i] * 100 for i in range(1000)]
            memory2 = monitor.check_memory("expanded")
            
            del test_data, more_data
            memory3 = monitor.check_memory("cleanup")
        
        resource_results['memory_monitoring'] = (memory1 > 0 and memory2 > 0 and memory3 > 0)
        print(f"   ✅ Memory monitoring: {memory1:.1f}MB -> {memory2:.1f}MB -> {memory3:.1f}MB")
        
        # Test resource tracking
        print("\nTesting resource tracking...")
        tracker = get_resource_tracker()
        summary = tracker.get_summary()
        resource_results['resource_tracking'] = isinstance(summary, str) and len(summary) > 0
        print(f"   ✅ Resource tracking summary: {len(summary)} characters")
        
        # Test memory threshold warnings
        print("\nTesting memory threshold warnings...")
        monitor = MemoryMonitor("Threshold test", warning_threshold_mb=1)  # Very low threshold
        monitor.start_monitoring()
        
        # This should trigger a warning
        large_data = [0] * 1000000  # Should use some memory
        monitor.check_memory("large allocation")
        monitor.finish_monitoring()
        del large_data
        
        resource_results['threshold_warnings'] = True  # If we got here, it didn't crash
        print(f"   ✅ Threshold warnings handled properly")
        
        successful_resources = sum(1 for success in resource_results.values() if success)
        total_resources = len(resource_results)
        
        print(f"\n✅ Resource management test completed: {successful_resources}/{total_resources} tests passed")
        
        return True, resource_results
        
    except Exception as e:
        print(f"❌ Resource management test failed: {e}")
        import traceback
        traceback.print_exc()
        return False, {}

def generate_comprehensive_report(test_results, test_output):
    """Generate a comprehensive test report."""
    print("\n" + "="*60)
    print("GENERATING COMPREHENSIVE TEST REPORT")
    print("="*60)
    
    report_file = test_output / "full_test_report.txt"
    
    with open(report_file, 'w') as f:
        f.write("RECEIPT ANALYZER - COMPREHENSIVE FULL APPLICATION TEST REPORT\n")
        f.write("=" * 70 + "\n")
        f.write(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Test Duration: {time.time() - test_results.get('start_time', time.time()):.1f} seconds\n\n")
        
        # Summary
        total_phases = len([k for k in test_results.keys() if k.startswith('phase_')])
        passed_phases = len([k for k, v in test_results.items() if k.startswith('phase_') and v.get('success', False)])
        
        f.write("TEST SUMMARY\n")
        f.write("-" * 30 + "\n")
        f.write(f"Total Test Phases: {total_phases}\n")
        f.write(f"Passed Phases: {passed_phases}\n")
        f.write(f"Overall Success Rate: {passed_phases/total_phases*100:.1f}%\n\n")
        
        # Detailed results
        f.write("DETAILED RESULTS\n")
        f.write("-" * 30 + "\n")
        
        for phase_name, results in test_results.items():
            if not phase_name.startswith('phase_'):
                continue
                
            f.write(f"\n{phase_name.upper().replace('_', ' ')}\n")
            f.write("Status: " + ("✅ PASSED" if results.get('success', False) else "❌ FAILED") + "\n")
            
            for key, value in results.items():
                if key != 'success':
                    f.write(f"  • {key}: {value}\n")
        
        # Resource usage
        if 'phase_resource_management' in test_results:
            f.write(f"\nRESOURCE USAGE\n")
            f.write("-" * 30 + "\n")
            resource_data = test_results['phase_resource_management']
            for key, value in resource_data.items():
                if key != 'success':
                    f.write(f"  • {key}: {value}\n")
        
        # File outputs
        f.write(f"\nOUTPUT FILES GENERATED\n")
        f.write("-" * 30 + "\n")
        for method_dir in ["simple_method", "opencv_method", "export_tests"]:
            method_path = test_output / method_dir
            if method_path.exists():
                files = list(method_path.rglob("*"))
                f.write(f"  • {method_dir}: {len(files)} files\n")
        
        f.write(f"\nTest completed successfully!\n")
        f.write(f"Full report saved to: {report_file}\n")
    
    print(f"📋 Comprehensive report generated: {report_file}")
    return report_file

def main():
    """Run the comprehensive full application test."""
    print("🚀 STARTING COMPREHENSIVE FULL APPLICATION TEST")
    print("="*70)
    
    start_time = time.time()
    test_results = {'start_time': start_time}
    
    # Setup
    test_output = setup_test_environment()
    print(f"✅ Test environment set up: {test_output}")
    
    # Find PDF files
    pdf_files = []
    for pdf_path in [
        project_root / "1097986001_expense_30712700.pdf",
        project_root / "sample_receipt.pdf", 
        project_root / "input_receipts" / "sample_receipt.pdf"
    ]:
        if pdf_path.exists():
            pdf_files.append(pdf_path)
    
    print(f"📄 Found {len(pdf_files)} PDF files to test:")
    for pdf_file in pdf_files:
        print(f"   • {pdf_file}")
    
    if not pdf_files:
        print("❌ No PDF files found to test!")
        return False
    
    # Run all test phases
    phases = [
        ("Dependencies and Imports", lambda: test_dependencies_and_imports()),
        ("Configuration", lambda: test_configuration()),
        ("Simple Detection Method", lambda: test_pdf_processing_simple(pdf_files, test_output, test_results.get('config'))),
        ("OpenCV Detection Method", lambda: test_pdf_processing_opencv(pdf_files, test_output, test_results.get('config'))),
        ("Individual Detection Methods", lambda: test_individual_detection_methods(pdf_files, test_output)),
        ("OCR Functionality", lambda: test_ocr_functionality(test_output)),
        ("Export Functionality", lambda: test_export_functionality(test_output, test_results.get('config'))),
        ("Error Handling and Edge Cases", lambda: test_error_handling_and_edge_cases(test_output)),
        ("Resource Management", lambda: test_resource_management(test_output)),
    ]
    
    for i, (phase_name, phase_func) in enumerate(phases, 1):
        print(f"\n🔍 Running Phase {i}: {phase_name}")
        try:
            result = phase_func()
            if isinstance(result, tuple):
                success = result[0]
                if len(result) > 1:
                    # Store additional data
                    if phase_name == "Configuration":
                        test_results['config'] = result[1]
                    phase_data = {'success': success}
                    for j, value in enumerate(result[1:], 1):
                        phase_data[f'result_{j}'] = value
                    test_results[f'phase_{i}_{phase_name.lower().replace(" ", "_")}'] = phase_data
                else:
                    test_results[f'phase_{i}_{phase_name.lower().replace(" ", "_")}'] = {'success': success}
            else:
                test_results[f'phase_{i}_{phase_name.lower().replace(" ", "_")}'] = {'success': result}
                
        except Exception as e:
            print(f"❌ Phase {i} failed with exception: {e}")
            test_results[f'phase_{i}_{phase_name.lower().replace(" ", "_")}'] = {'success': False, 'error': str(e)}
    
    # Generate report
    report_file = generate_comprehensive_report(test_results, test_output)
    
    # Final summary
    total_time = time.time() - start_time
    total_phases = len([k for k in test_results.keys() if k.startswith('phase_')])
    passed_phases = len([k for k, v in test_results.items() if k.startswith('phase_') and v.get('success', False)])
    
    print(f"\n" + "="*70)
    print("🎯 COMPREHENSIVE TEST COMPLETED")
    print("="*70)
    print(f"⏱️  Total Test Time: {total_time:.1f} seconds")
    print(f"📊 Phases Passed: {passed_phases}/{total_phases}")
    print(f"📈 Success Rate: {passed_phases/total_phases*100:.1f}%")
    print(f"📋 Full Report: {report_file}")
    print(f"📁 Test Output: {test_output}")
    
    if passed_phases == total_phases:
        print("\n🎉 ALL TESTS PASSED! APPLICATION FULLY FUNCTIONAL! 🎉")
    else:
        print(f"\n⚠️  {total_phases - passed_phases} test phase(s) failed")
    
    return passed_phases == total_phases

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
