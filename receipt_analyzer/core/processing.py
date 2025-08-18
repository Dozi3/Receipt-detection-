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
from .logging_utils import get_logger, log_info, log_success, log_warn, log_fail, format_pdf_log


def resize_image_for_output(image: Image.Image, max_edge: int) -> Image.Image:
    """Resize image for final output if needed."""
    width, height = image.size
    
    if max(width, height) <= max_edge:
        return image
    
    # Calculate new dimensions maintaining aspect ratio
    if width > height:
        new_width = max_edge
        new_height = int(height * max_edge / width)
    else:
        new_height = max_edge
        new_width = int(width * max_edge / height)
    
    return image.resize((new_width, new_height), Image.Resampling.LANCZOS)


def save_image(image: Image.Image, output_path: Path, config: Config) -> bool:
    """Save image in the specified format."""
    try:
        # Resize if needed
        image = resize_image_for_output(image, config.output.max_edge)
        
        # Save in specified format
        if config.output.format.lower() == 'jpeg':
            # Convert to RGB if needed (JPEG doesn't support RGBA)
            if image.mode in ('RGBA', 'LA', 'P'):
                rgb_image = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image = image.convert('RGBA')
                rgb_image.paste(image, mask=image.split()[-1] if 'A' in image.mode else None)
                image = rgb_image
            
            image.save(output_path, 'JPEG', quality=config.output.jpeg_quality, optimize=True)
        else:
            # Default to PNG
            image.save(output_path, 'PNG', optimize=True)
        
        return True
    
    except Exception as e:
        get_logger().fail(f"Failed to save image to {output_path}: {e}")
        return False


def process_receipt(image: Image.Image, config: Config, vendor_map: Optional[VendorMap],
                   pdf_path: str, page_num: int, receipt_num: int) -> Optional[tuple]:
    """
    Process a single receipt image through OCR and parsing.
    
    Returns:
        Tuple of (parsed_receipt, ocr_metadata) or None if failed
    """
    logger = get_logger()
    
    # Perform OCR
    text, ocr_metadata = perform_ocr(
        image, config.ocr, pdf_path, page_num, receipt_num, auto_orient=True
    )
    
    if not text:
        return None
    
    # Parse receipt text
    keyword_map = vendor_map.keywords if vendor_map else {}
    ignored_domains = list(vendor_map.ignored_domains) if vendor_map else None
    
    parsed_receipt = parse_receipt_text(
        text, keyword_map, ignored_domains, pdf_path, page_num, receipt_num
    )
    
    # Apply synonym resolution if vendor found
    if parsed_receipt.vendor and vendor_map:
        parsed_receipt.vendor = vendor_map.resolve_synonym(parsed_receipt.vendor)
    
    return parsed_receipt, ocr_metadata


def process_pdf_page(pdf_path: Path, page_num: int, config: Config, 
                    vendor_map: Optional[VendorMap], output_dir: Path) -> List[ReceiptRecord]:
    """
    Process a single PDF page and return receipt records.
    
    Args:
        pdf_path: Path to PDF file
        page_num: Page number (0-based)
        config: Configuration object
        vendor_map: Vendor mapping object
        output_dir: Output directory
    
    Returns:
        List of ReceiptRecord objects
    """
    logger = get_logger()
    records = []
    
    # Get images from PDF page
    images = get_page_images(pdf_path, page_num)
    if not images:
        return records
    
    # Detect receipts using configured method
    if config.detection_method == 'simple':
        receipt_images = detect_receipts_simple(images, str(pdf_path), page_num)
    else:  # opencv
        receipt_images = detect_receipts_opencv(images, str(pdf_path), page_num, config.opencv)
    
    if not receipt_images:
        return records
    
    # Create page output directory
    page_dir = output_dir / f"page_{page_num + 1}"
    page_dir.mkdir(exist_ok=True)
    
    # Process each detected receipt
    page_receipts = []
    for receipt_num, receipt_image in enumerate(receipt_images):
        try:
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
            if save_image(receipt_image, output_path, config):
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
            log_fail(format_pdf_log(str(pdf_path), page_num + 1, 
                                  f"receipt {receipt_num + 1}: processing error: {e}"))
    
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
    
    return records


def process_pdf_files(pdf_files: List[Path], output_dir: Path, config: Config,
                     vendor_map: Optional[VendorMap] = None) -> int:
    """
    Process a list of PDF files.
    
    Args:
        pdf_files: List of PDF file paths
        output_dir: Output directory
        config: Configuration object
        vendor_map: Optional vendor mapping object
    
    Returns:
        Total number of receipts processed
    """
    logger = get_logger()
    
    if vendor_map is None:
        vendor_map = load_vendor_map()
    
    all_records = []
    total_receipts = 0
    
    # Process each PDF file
    for pdf_path in pdf_files:
        try:
            log_info(f"Processing {pdf_path.name}")
            
            page_count = get_pdf_page_count(pdf_path)
            if page_count == 0:
                log_fail(f"{pdf_path.name}: no pages found")
                continue
            
            pdf_receipts = 0
            
            # Process each page
            for page_num in range(page_count):
                page_records = process_pdf_page(
                    pdf_path, page_num, config, vendor_map, output_dir
                )
                all_records.extend(page_records)
                pdf_receipts += len(page_records)
            
            if pdf_receipts > 0:
                log_info(f"Completed {pdf_path.name}: {pdf_receipts} receipts processed")
                total_receipts += pdf_receipts
            else:
                log_warn(f"No receipts extracted from {pdf_path.name}")
        
        except Exception as e:
            log_fail(f"Failed to process {pdf_path.name}: {e}")
    
    # Export CSV files
    if all_records:
        csv_results = export_all_csv_files(all_records, output_dir)
        
        for csv_type, success in csv_results.items():
            if success:
                log_info(f"Generated {csv_type}.csv")
            else:
                log_warn(f"Failed to generate {csv_type}.csv")
    
    # Save updated vendor map (in case of auto-learning)
    if vendor_map:
        save_vendor_map(vendor_map)
    
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