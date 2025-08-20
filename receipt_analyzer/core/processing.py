"""Main processing pipeline that orchestrates all components."""

import zipfile
from pathlib import Path
from typing import List, Optional, Dict
from PIL import Image

from .config import Config
from .pdf_io import get_pdf_page_count, get_page_images
from .detection_simple import detect_receipts_simple
from .detection_opencv import detect_receipts_opencv
from .ocr import perform_ocr
from .parsing import parse_receipt_text
from .naming import build_receipt_filename, unique_path, build_page_zip_filename
from .vendors import VendorMap, load_vendor_map, save_vendor_map
from .csv_export import ReceiptRecord, export_all_csv_files
from .logging_utils import get_logger, log_info, log_success, log_warn, log_fail, log_debug, format_pdf_log, format_receipt_log


def resize_image_for_output(image: Image.Image, max_edge: int) -> Image.Image:
    """Resize image for final output if needed."""
    logger = get_logger()
    
    try:
        width, height = image.size
        logger.debug(f"resize_image_for_output: Input image: {width}x{height}, mode: {image.mode}")
        
        if max(width, height) <= max_edge:
            logger.debug(f"resize_image_for_output: No resize needed, max dimension {max(width, height)} <= {max_edge}")
            return image
        
        # Calculate new dimensions maintaining aspect ratio
        if width > height:
            new_width = max_edge
            new_height = int(height * max_edge / width)
            logger.debug(f"resize_image_for_output: Width-limited resize to {new_width}x{new_height}")
        else:
            new_height = max_edge
            new_width = int(width * max_edge / height)
            logger.debug(f"resize_image_for_output: Height-limited resize to {new_width}x{new_height}")
        
        # Ensure minimum dimensions
        new_width = max(new_width, 1)
        new_height = max(new_height, 1)
        
        # Perform the resize
        resized = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        logger.debug(f"resize_image_for_output: Resized image: {resized.size[0]}x{resized.size[1]}, mode: {resized.mode}")
        
        return resized
    except Exception as e:
        import traceback
        logger.warn(f"resize_image_for_output: Error resizing image: {e}")
        logger.debug(f"resize_image_for_output: Error details: {traceback.format_exc()}")
        # Return original image as fallback
        return image


def save_image(image: Image.Image, output_path: Path, config: Config) -> bool:
    """Save image in the specified format."""
    logger = get_logger()
    
    try:
        if image is None:
            logger.warn(f"Cannot save None image to {output_path}")
            return False
        # Check image dimensions
        width, height = image.size
        if width <= 0 or height <= 0:
            logger.warn(f"Cannot save zero-dimension image ({width}x{height}) to {output_path}")
            return False
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        # Resize if needed
        logger.debug(f"Original image: {width}x{height}, mode: {image.mode}")
        image = resize_image_for_output(image, config.output.max_edge)
        logger.debug(f"After resize: {image.size[0]}x{image.size[1]}")
        # Determine format from extension if possible
        ext = output_path.suffix.lower()
        fmt = None
        if ext in ('.jpg', '.jpeg'):
            fmt = 'JPEG'
        elif ext == '.png':
            fmt = 'PNG'
        elif ext == '.tif' or ext == '.tiff':
            fmt = 'TIFF'
        else:
            fmt = config.output.format.upper() if hasattr(config.output, 'format') else 'PNG'
        logger.debug(f"Selected output format: {fmt}")
        # Convert to appropriate mode
        if fmt == 'JPEG':
            if image.mode not in ('RGB', 'L'):
                logger.debug(f"Converting image from {image.mode} to RGB for JPEG format")
                image = image.convert('RGB')
        elif fmt == 'PNG':
            if image.mode not in ('RGB', 'RGBA', 'L'):
                logger.debug(f"Converting image from {image.mode} to RGBA for PNG format")
                image = image.convert('RGBA')
        # Save with appropriate options
        try:
            if fmt == 'JPEG':
                quality = getattr(config.output, 'jpeg_quality', 90)
                logger.debug(f"Saving as JPEG with quality {quality}")
                image.save(output_path, fmt, quality=quality, optimize=True)
            elif fmt == 'PNG':
                logger.debug("Saving as PNG with optimization")
                image.save(output_path, fmt, optimize=True)
            elif fmt == 'TIFF':
                logger.debug("Saving as TIFF")
                image.save(output_path, fmt)
            else:
                logger.debug(f"Saving with default settings, format: {fmt}")
                image.save(output_path)
        except Exception as save_error:
            import traceback
            logger.warn(f"Save operation failed: {save_error}")
            logger.debug(f"Save error details: {traceback.format_exc()}")
            raise
        
        logger.debug(f"Successfully saved image to {output_path} as {fmt}")
        return True
    except Exception as e:
        import traceback
        logger.warn(f"Failed to save image to {output_path}: {e}")
        logger.debug(f"Save error details: {traceback.format_exc()}")
        return False


def process_receipt(image: Image.Image, config: Config, vendor_map: Optional[VendorMap],
                   pdf_path: str, page_num: int, receipt_num: int) -> Optional[tuple]:
    """
    Process a single receipt image through OCR and parsing.
    
    Returns:
        Tuple of (parsed_receipt, ocr_metadata) or None if failed
    """
    logger = get_logger()
    
    # Validate image
    if image is None:
        logger.warn(format_receipt_log(pdf_path, page_num + 1, receipt_num + 1, "null image, skipping"))
        return None
        
    # Check image dimensions and validity
    try:
        width, height = image.size
        logger.debug(f"process_receipt: Receipt image size: {width}x{height}, mode: {image.mode}")
        
        if width < 50 or height < 50:
            logger.warn(format_receipt_log(pdf_path, page_num + 1, receipt_num + 1, 
                                         f"image too small ({width}x{height}), skipping"))
            return None
            
        # Basic validation to ensure image data is accessible
        try:
            # Try to access a pixel to ensure image data is valid
            image.getpixel((0, 0))
        except Exception as pixel_error:
            logger.warn(format_receipt_log(pdf_path, page_num + 1, receipt_num + 1, 
                                         f"corrupt image data: {pixel_error}, skipping"))
            return None
            
    except Exception as e:
        import traceback
        logger.warn(format_receipt_log(pdf_path, page_num + 1, receipt_num + 1, 
                                     f"invalid image: {e}, skipping"))
        logger.debug(f"Image validation error details: {traceback.format_exc()}")
        return None
    
    # Perform OCR
    try:
        logger.debug(f"process_receipt: Performing OCR on image {receipt_num+1} from page {page_num+1}")
        text, ocr_metadata = perform_ocr(
            image, config.ocr, pdf_path, page_num, receipt_num, auto_orient=True
        )
        
        if not text:
            logger.warn(format_receipt_log(pdf_path, page_num + 1, receipt_num + 1, 
                                         "no text extracted, skipping"))
            return None
            
        logger.debug(f"process_receipt: OCR successful, extracted {len(text)} characters")
            
    except Exception as ocr_error:
        import traceback
        logger.warn(format_receipt_log(pdf_path, page_num + 1, receipt_num + 1, 
                                     f"OCR failed: {ocr_error}, skipping"))
        logger.debug(f"OCR error details: {traceback.format_exc()}")
        return None
    
    # Parse receipt text
    try:
        logger.debug(f"process_receipt: Parsing receipt text")
        keyword_map = vendor_map.keywords if vendor_map else {}
        ignored_domains = list(vendor_map.ignored_domains) if vendor_map else None
        parsed_receipt = parse_receipt_text(
            text, keyword_map, ignored_domains, pdf_path, page_num, receipt_num
        )
        
        # Apply synonym resolution if vendor found
        if parsed_receipt.vendor and vendor_map:
            try:
                parsed_receipt.vendor = vendor_map.resolve_synonym(parsed_receipt.vendor)
            except Exception as synonym_error:
                logger.warn(format_receipt_log(pdf_path, page_num + 1, receipt_num + 1, 
                                             f"vendor synonym resolution failed: {synonym_error}"))
            
        # Validate parsed data and add placeholders for missing fields
        if not parsed_receipt.vendor:
            logger.warn(format_receipt_log(pdf_path, page_num + 1, receipt_num + 1, 
                                         "no vendor found, using placeholder"))
            parsed_receipt.vendor = "Unknown_Vendor"
            
        if not parsed_receipt.amount:
            logger.warn(format_receipt_log(pdf_path, page_num + 1, receipt_num + 1, 
                                         "no amount found, using placeholder"))
            parsed_receipt.amount = 0.0
            
        if not parsed_receipt.date:
            logger.warn(format_receipt_log(pdf_path, page_num + 1, receipt_num + 1, 
                                         "no date found, using current date"))
            from datetime import date
            parsed_receipt.date = date.today()
        
        logger.debug(f"process_receipt: Parsing completed successfully")
        return parsed_receipt, ocr_metadata
        
    except Exception as e:
        import traceback
        logger.warn(format_receipt_log(pdf_path, page_num + 1, receipt_num + 1, 
                                     f"parsing failed: {e}"))
        logger.debug(f"Parsing error details: {traceback.format_exc()}")
        return None


def process_pdf_page(pdf_path: Path, page_num: int, config: Config, 
                    vendor_map: Optional[VendorMap], output_dir: Path,
                    cancellation_token=None) -> List[ReceiptRecord]:
    """
    Process a single PDF page and return receipt records.
    
    Args:
        pdf_path: Path to PDF file
        page_num: Page number (0-based)
        config: Configuration object
        vendor_map: Vendor mapping object
        output_dir: Output directory
        cancellation_token: Optional cancellation token
    
    Returns:
        List of ReceiptRecord objects
    """
    logger = get_logger()
    records = []
    
    try:
        # Check for cancellation at start
        if cancellation_token and cancellation_token.is_cancelled():
            return records
        
        # Get images from PDF page
        logger.debug(f"process_pdf_page: Processing {pdf_path}, page {page_num+1}")
        images = get_page_images(pdf_path, page_num, cancellation_token=cancellation_token)
        if not images:
            logger.warn(format_pdf_log(str(pdf_path), page_num + 1, "no images extracted from page"))
            return records
        
        # Check for cancellation after image extraction
        if cancellation_token and cancellation_token.is_cancelled():
            return records
        
        logger.debug(f"process_pdf_page: Extracted {len(images)} image(s) from page {page_num+1}")
        
        # Detect receipts using configured method
        receipt_images = []
        try:
            if hasattr(config, 'detection_method') and config.detection_method == 'simple':
                logger.debug(f"process_pdf_page: Using simple detection method")
                receipt_images = detect_receipts_simple(images, str(pdf_path), page_num)
            else:  # opencv
                logger.debug(f"process_pdf_page: Using OpenCV detection method")
                receipt_images = detect_receipts_opencv(images, str(pdf_path), page_num, config.opencv)
            
            logger.debug(f"process_pdf_page: Detection found {len(receipt_images) if receipt_images else 0} receipt(s)")
        except Exception as e:
            import traceback
            logger.warn(f"process_pdf_page: Receipt detection failed: {e}")
            logger.debug(f"process_pdf_page: Detection error details: {traceback.format_exc()}")
            # If this is the first page and detection failed, it might be a summary page
            if page_num == 0:
                logger.info(f"process_pdf_page: First page detection failed, possibly a non-receipt summary page")
            return records
        
        if not receipt_images:
            logger.warn(format_pdf_log(str(pdf_path), page_num + 1, "no receipt images detected"))
            # If this is the first page, it might be a summary page
            if page_num == 0:
                logger.info(f"process_pdf_page: First page has no receipts, possibly a summary page")
            return records
        
        # Create page output directory
        page_dir = output_dir / f"page_{page_num + 1}"
        page_dir.mkdir(exist_ok=True)
        
        # Process each detected receipt
        page_receipts = []
        for receipt_num, receipt_image in enumerate(receipt_images):
            try:
                # Check for cancellation before each receipt
                if cancellation_token and cancellation_token.is_cancelled():
                    logger.debug("Processing cancelled during receipt processing")
                    break
                
                # Validate image before processing
                if receipt_image is None:
                    logger.warn(format_pdf_log(str(pdf_path), page_num + 1, 
                                             f"receipt {receipt_num + 1}: image is None, skipping"))
                    continue
                
                try:
                    # Basic image validation
                    width, height = receipt_image.size
                    if width <= 10 or height <= 10:
                        logger.warn(format_pdf_log(str(pdf_path), page_num + 1, 
                                                f"receipt {receipt_num + 1}: image too small ({width}x{height}), skipping"))
                        continue
                except Exception as img_error:
                    logger.warn(format_pdf_log(str(pdf_path), page_num + 1, 
                                             f"receipt {receipt_num + 1}: invalid image: {img_error}, skipping"))
                    continue
                
                logger.debug(f"process_pdf_page: Processing receipt {receipt_num+1}, size: {receipt_image.size}")
                
                # Process receipt (OCR + parsing)
                result = process_receipt(
                    receipt_image, config, vendor_map, str(pdf_path), page_num, receipt_num
                )
                
                if result is None:
                    log_warn(format_pdf_log(str(pdf_path), page_num + 1, 
                                          f"receipt {receipt_num + 1}: processing failed"))
                    continue
                
                parsed_receipt, ocr_metadata = result
                
                # Generate filename
                file_extension = config.output.format
                filename = build_receipt_filename(parsed_receipt, file_extension)
                
                # Ensure unique filename
                output_path = unique_path(page_dir / filename)
                final_filename = output_path.name
                
                # Save image
                save_success = False
                try:
                    save_success = save_image(receipt_image, output_path, config)
                except Exception as save_error:
                    logger.warn(format_pdf_log(str(pdf_path), page_num + 1, 
                                             f"receipt {receipt_num + 1}: error saving image: {save_error}"))
                
                if save_success:
                    log_success(format_pdf_log(str(pdf_path), page_num + 1, 
                                             f"receipt {receipt_num + 1} -> {page_dir.name}/{final_filename}"))
                    
                    # Create receipt record
                    record = ReceiptRecord(
                        pdf_name=pdf_path.name,
                        page_num=page_num,
                        receipt_num=receipt_num,
                        receipt=parsed_receipt,
                        filename=f"{page_dir.name}/{final_filename}"
                    )
                    
                    records.append(record)
                    page_receipts.append((final_filename, receipt_image))
                    
                    # Check for missing data and warn
                    missing = []
                    if not parsed_receipt.vendor:
                        missing.append("vendor")
                    if not parsed_receipt.amount:
                        missing.append("amount")
                    if not parsed_receipt.date:
                        missing.append("date")
                    
                    if missing:
                        preview = parsed_receipt.raw_text.replace('\n', ' ').strip()[:120]
                        log_warn(format_pdf_log(str(pdf_path), page_num + 1, 
                                              f"receipt {receipt_num + 1}: missing {', '.join(missing)} | {preview}"))
                
                else:
                    log_fail(format_pdf_log(str(pdf_path), page_num + 1, 
                                          f"receipt {receipt_num + 1}: failed to save image"))
            
            except Exception as e:
                import traceback
                log_fail(format_pdf_log(str(pdf_path), page_num + 1, 
                                      f"receipt {receipt_num + 1}: processing error: {e}"))
                logger.debug(f"Receipt processing error details: {traceback.format_exc()}")
        
        # Create per-page ZIP if requested and receipts were saved
        if config.output.per_page_zip and page_receipts:
            zip_filename = build_page_zip_filename(pdf_path.stem, page_num)
            zip_path = output_dir / zip_filename
            
            try:
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                    for filename, _ in page_receipts:
                        file_path = page_dir / filename
                        zf.write(file_path, filename)
                
                logger.info(format_pdf_log(str(pdf_path), page_num + 1, 
                                         f"created ZIP archive: {zip_filename}"))
            
            except Exception as e:
                log_warn(format_pdf_log(str(pdf_path), page_num + 1, 
                                      f"failed to create ZIP archive: {e}"))
    
    except Exception as e:
        import traceback
        log_fail(format_pdf_log(str(pdf_path), page_num + 1, f"page processing failed: {e}"))
        logger.debug(f"Page processing error details: {traceback.format_exc()}")
        
    return records


def process_pdf_files(pdf_files: List[Path], output_dir: Path, config: Config,
                     vendor_map: Optional[VendorMap] = None, 
                     cancellation_token=None, progress_callback=None) -> int:
    """
    Process a list of PDF files.
    
    Args:
        pdf_files: List of PDF file paths
        output_dir: Output directory
        config: Configuration object
        vendor_map: Optional vendor mapping object
        cancellation_token: Optional cancellation token for early termination
        progress_callback: Optional callback for progress updates
    
    Returns:
        Total number of receipts processed
    """
    logger = get_logger()
    
    # Check for cancellation at start
    if cancellation_token and cancellation_token.is_cancelled():
        return 0
    
    if vendor_map is None:
        vendor_map = load_vendor_map()
    
    all_records = []
    total_receipts = 0
    
    # Process each PDF file
    for pdf_index, pdf_path in enumerate(pdf_files):
        try:
            # Check for cancellation before each file
            if cancellation_token and cancellation_token.is_cancelled():
                logger.debug("Processing cancelled by user")
                break
            
            # Update progress
            if progress_callback:
                progress_callback.update(pdf_index, len(pdf_files), f"Processing {pdf_path.name}")
            
            log_info(f"Processing {pdf_path.name}")
            logger.debug(f"process_pdf_files: Starting processing of {pdf_path}")
            
            # Verify the file exists and is accessible
            if not pdf_path.exists():
                log_fail(f"{pdf_path.name}: file not found")
                continue
                
            try:
                page_count = get_pdf_page_count(pdf_path)
                logger.debug(f"process_pdf_files: {pdf_path.name} has {page_count} pages")
                
                if page_count == 0:
                    log_fail(f"{pdf_path.name}: no pages found")
                    continue
            except Exception as page_count_error:
                import traceback
                log_fail(f"{pdf_path.name}: error getting page count: {page_count_error}")
                logger.debug(f"Page count error details: {traceback.format_exc()}")
                continue
            
            pdf_receipts = 0
            
            # Process each page
            for page_num in range(page_count):
                # Check for cancellation before each page
                if cancellation_token and cancellation_token.is_cancelled():
                    logger.debug("Processing cancelled during page processing")
                    break
                    
                logger.debug(f"process_pdf_files: Processing page {page_num+1} of {page_count}")
                try:
                    page_records = process_pdf_page(
                        pdf_path, page_num, config, vendor_map, output_dir, cancellation_token
                    )
                    all_records.extend(page_records)
                    pdf_receipts += len(page_records)
                    
                    logger.debug(f"process_pdf_files: Page {page_num+1} yielded {len(page_records)} receipts")
                except Exception as page_error:
                    import traceback
                    log_fail(f"{pdf_path.name}, page {page_num+1}: processing failed: {page_error}")
                    logger.debug(f"Page processing error details: {traceback.format_exc()}")
                    # Continue with other pages
            
            if pdf_receipts > 0:
                log_success(f"Completed {pdf_path.name}: {pdf_receipts} receipts processed")
                total_receipts += pdf_receipts
            else:
                log_warn(f"No receipts extracted from {pdf_path.name}")
        
        except Exception as e:
            import traceback
            log_fail(f"Failed to process {pdf_path.name}: {e}")
            logger.debug(f"PDF processing error details: {traceback.format_exc()}")
    
    # Export CSV files
    if all_records:
        try:
            csv_results = export_all_csv_files(all_records, output_dir)
            
            for csv_type, success in csv_results.items():
                if success:
                    log_info(f"Generated {csv_type}.csv")
                else:
                    log_warn(f"Failed to generate {csv_type}.csv")
        except Exception as export_error:
            import traceback
            log_fail(f"Failed to export CSV files: {export_error}")
            logger.debug(f"CSV export error details: {traceback.format_exc()}")
    
    # Save updated vendor map (in case of auto-learning)
    if vendor_map:
        try:
            save_vendor_map(vendor_map)
        except Exception as vendor_error:
            logger.warn(f"Failed to save vendor map: {vendor_error}")
    
    return total_receipts


def check_processing_requirements(config: Config) -> tuple[bool, List[str]]:
    """
    Check if all requirements are met for processing.
    
    Returns:
        Tuple of (requirements_met, error_messages)
    """
    from .pdf_io import check_dependencies
    from .ocr import check_tesseract_available
    from .detection_opencv import check_opencv_available
    
    errors = []
    
    # Check PDF processing dependencies
    pdf_ok, pdf_messages = check_dependencies()
    if not pdf_ok:
        errors.extend([msg for msg in pdf_messages if "required" in msg.lower()])
    
    # Check Tesseract
    tesseract_ok, tesseract_msg = check_tesseract_available()
    if not tesseract_ok:
        errors.append(tesseract_msg)
    
    # Check OpenCV if needed
    if config.detection_method == 'opencv' and not check_opencv_available():
        errors.append("OpenCV not available but opencv detection method selected")
    
    return len(errors) == 0, errors