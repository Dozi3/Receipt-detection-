"""Filename generation and safe filename utilities."""

import re
import os
from pathlib import Path
from typing import Optional
from datetime import date

from .parsing import ParsedReceipt, format_amount_for_filename, format_date_for_filename


# Reserved names on Windows
WINDOWS_RESERVED_NAMES = {
    'con', 'prn', 'aux', 'nul',
    'com1', 'com2', 'com3', 'com4', 'com5', 'com6', 'com7', 'com8', 'com9',
    'lpt1', 'lpt2', 'lpt3', 'lpt4', 'lpt5', 'lpt6', 'lpt7', 'lpt8', 'lpt9'
}

# Characters that are illegal in filenames (Windows + others)
ILLEGAL_CHARS = r'[<>:"/\\|?*\x00-\x1f]'

# Additional characters to replace for better compatibility
PROBLEMATIC_CHARS = r'[^\w\s\-_&.()\[\]]'


def safe_filename(text: str, max_length: int = 100) -> str:
    """
    Convert text to a safe filename.
    
    Args:
        text: Input text
        max_length: Maximum filename length
    
    Returns:
        Safe filename string
    """
    if not text:
        return "Unknown"
    
    # Replace illegal characters with underscores
    safe_text = re.sub(ILLEGAL_CHARS, '_', text)
    
    # Replace spaces with underscores
    safe_text = safe_text.replace(' ', '_')
    
    # Replace multiple underscores with single underscore
    safe_text = re.sub(r'_+', '_', safe_text)
    
    # Split into name and extension
    parts = safe_text.rsplit('.', 1) if '.' in safe_text else [safe_text, '']
    name, ext = (parts[0], '.' + parts[1]) if len(parts) > 1 and parts[1] else (safe_text, '')
    
    # Check for reserved names (Windows)
    name_lower = name.lower()
    if name_lower in WINDOWS_RESERVED_NAMES or name_lower.startswith(tuple(n + '.' for n in WINDOWS_RESERVED_NAMES)):
        name = f"{name}_file"
    
    # Trim to max length
    if len(name) > max_length:
        name = name[:max_length]
    
    # Remove trailing dots and spaces (Windows compatibility)
    name = name.rstrip('. ')
    
    # Ensure it's not empty after trimming
    if not name:
        name = "Unknown"
    
    # Recombine name and extension
    safe_text = name + ext if ext else name
    
    return safe_text


def build_receipt_filename(receipt: ParsedReceipt, file_extension: str = "png") -> str:
    """
    Build filename from parsed receipt data.
    
    Format: Vendor_GBP-12-34_DD-MM-YYYY.ext
    
    Args:
        receipt: ParsedReceipt object
        file_extension: File extension without dot
    
    Returns:
        Complete filename
    """
    # Get components
    vendor = receipt.vendor if receipt.vendor else "Unknown"
    amount_str = format_amount_for_filename(receipt.amount)
    date_str = format_date_for_filename(receipt.date)
    
    # Replace special characters in vendor name
    vendor = vendor.replace('&', 'and').replace('/', '-').replace('\\', '-')
    
    # Make vendor name safe for filename
    safe_vendor = safe_filename(vendor, max_length=50)
    
    # Build filename
    filename = f"{safe_vendor}_GBP-{amount_str}_{date_str}.{file_extension.lstrip('.')}"
    
    return filename


def unique_path(base_path: Path, max_attempts: int = 1000) -> Path:
    """
    Generate a unique file path by adding suffix if file exists.
    
    Args:
        base_path: Desired path
        max_attempts: Maximum number of attempts
    
    Returns:
        Unique path (may be same as input if it doesn't exist)
    """
    if not base_path.exists():
        return base_path
    
    stem = base_path.stem
    suffix = base_path.suffix
    parent = base_path.parent
    
    for i in range(2, max_attempts + 2):
        new_path = parent / f"{stem}_{i}{suffix}"
        if not new_path.exists():
            return new_path
    
    # Fallback with timestamp if all attempts failed
    from datetime import datetime
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    return parent / f"{stem}_{timestamp}{suffix}"


def build_page_zip_filename(pdf_name: str, page_num: int) -> str:
    """
    Build filename for per-page ZIP file.
    
    Args:
        pdf_name: Name of the PDF file (without extension)
        page_num: Page number (0-based)
    
    Returns:
        ZIP filename
    """
    safe_pdf_name = safe_filename(pdf_name, max_length=50)
    return f"{safe_pdf_name}_page_{page_num + 1}.zip"


def validate_filename(filename: str) -> tuple[bool, str]:
    """
    Validate if a filename is safe and legal.
    
    Args:
        filename: Filename to validate
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not filename:
        return False, "Filename is empty"
    
    # Check for illegal characters
    if re.search(ILLEGAL_CHARS, filename):
        return False, "Contains illegal characters"
    
    # Check length
    if len(filename) > 255:
        return False, "Filename too long"
    
    # Check for reserved names
    name_without_ext = Path(filename).stem.lower()
    if name_without_ext in WINDOWS_RESERVED_NAMES:
        return False, f"'{name_without_ext}' is a reserved name"
    
    # Check for trailing dots/spaces
    if filename.endswith(('.', ' ')):
        return False, "Filename ends with dot or space"
    
    return True, "OK"


def clean_vendor_name(vendor_name: str) -> str:
    """
    Clean vendor name for use in filename while preserving readability.
    
    Args:
        vendor_name: Raw vendor name
    
    Returns:
        Cleaned vendor name
    """
    if not vendor_name:
        return "Unknown"
    
    # Basic cleanup
    clean_name = vendor_name.strip()
    
    # Remove common suffixes
    suffixes_to_remove = [
        r'\s+ltd\.?$', r'\s+limited$', r'\s+inc\.?$', r'\s+corp\.?$',
        r'\s+co\.?$', r'\s+company$', r'\s+plc$', r'\s+llc$'
    ]
    
    for suffix in suffixes_to_remove:
        clean_name = re.sub(suffix, '', clean_name, flags=re.IGNORECASE)
    
    # Remove excessive whitespace
    clean_name = re.sub(r'\s+', ' ', clean_name).strip()
    
    # Title case for better readability
    clean_name = clean_name.title()
    
    return clean_name


def suggest_filename_improvements(receipt: ParsedReceipt) -> list[str]:
    """
    Suggest improvements to filename based on parsed data quality.
    
    Args:
        receipt: ParsedReceipt object
    
    Returns:
        List of improvement suggestions
    """
    suggestions = []
    
    if not receipt.vendor:
        suggestions.append("No vendor detected - filename will use 'Unknown'")
    elif receipt.confidence.get('vendor', 0) < 0.7:
        suggestions.append("Low confidence vendor detection - verify vendor name")
    
    if not receipt.amount:
        suggestions.append("No amount detected - filename will use '00-00'")
    elif receipt.confidence.get('amount', 0) < 0.7:
        suggestions.append("Low confidence amount detection - verify amount")
    
    if not receipt.date:
        suggestions.append("No date detected - filename will use current date")
    elif receipt.confidence.get('date', 0) < 0.7:
        suggestions.append("Low confidence date detection - verify date")
    
    return suggestions


def preview_filename(receipt: ParsedReceipt, file_extension: str = "png") -> dict:
    """
    Preview filename and provide metadata.
    
    Args:
        receipt: ParsedReceipt object
        file_extension: File extension without dot
    
    Returns:
        Dictionary with filename and metadata
    """
    filename = build_receipt_filename(receipt, file_extension)
    is_valid, validation_msg = validate_filename(filename)
    suggestions = suggest_filename_improvements(receipt)
    
    return {
        'filename': filename,
        'is_valid': is_valid,
        'validation_message': validation_msg,
        'suggestions': suggestions,
        'components': {
            'vendor': receipt.vendor or 'Unknown',
            'amount': format_amount_for_filename(receipt.amount),
            'date': format_date_for_filename(receipt.date),
            'extension': file_extension
        }
    }