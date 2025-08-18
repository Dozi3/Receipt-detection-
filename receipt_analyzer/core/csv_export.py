"""CSV export functionality for FreeAgent and receipts index files."""

import csv
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import date

from .parsing import ParsedReceipt
from .logging_utils import get_logger


def sanitize_csv_value(value: str) -> str:
    """
    Sanitize CSV values to prevent formula injection.
    
    Prefixes values starting with =, +, -, or @ with a single quote.
    """
    if not value:
        return value
    
    value_str = str(value).strip()
    
    # Check if value starts with potentially dangerous characters
    if value_str.startswith(('=', '+', '-', '@')):
        return f"'{value_str}"
    
    return value_str


def format_amount_for_csv(amount: Optional[float]) -> str:
    """Format amount for CSV export."""
    if amount is None:
        return "0.00"
    return f"{amount:.2f}"


def format_date_for_csv(date_obj: Optional[date]) -> str:
    """Format date for CSV export (DD/MM/YYYY format for UK accounting)."""
    if date_obj is None:
        return ""
    return date_obj.strftime("%d/%m/%Y")


class ReceiptRecord:
    """Data class for receipt records."""
    
    def __init__(self, pdf_name: str, page_num: int, receipt_num: int, 
                 receipt: ParsedReceipt, filename: str):
        self.pdf_name = pdf_name
        self.page_num = page_num  # 0-based
        self.receipt_num = receipt_num  # 0-based
        self.receipt = receipt
        self.filename = filename
        self.success = bool(receipt.vendor and receipt.amount and receipt.date)


def generate_freeagent_csv(records: List[ReceiptRecord], output_path: Path) -> bool:
    """
    Generate FreeAgent-compatible CSV file.
    
    Format: Date, Description, Amount, Receipt File
    """
    logger = get_logger()
    
    try:
        with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            
            # Header row
            writer.writerow(['Date', 'Description', 'Amount', 'Receipt File'])
            
            # Data rows
            for record in records:
                if not record.success:
                    continue  # Skip incomplete records
                
                receipt = record.receipt
                
                # Date in DD/MM/YYYY format
                date_str = format_date_for_csv(receipt.date)
                
                # Description (vendor name)
                description = sanitize_csv_value(receipt.vendor or "Unknown Vendor")
                
                # Amount (positive value for expenses)
                amount_str = format_amount_for_csv(receipt.amount)
                
                # Receipt file (just filename, not full path)
                receipt_file = sanitize_csv_value(record.filename)
                
                writer.writerow([date_str, description, amount_str, receipt_file])
        
        logger.info(f"Generated FreeAgent CSV with {len([r for r in records if r.success])} records at {output_path}")
        return True
    
    except OSError as e:
        logger.fail(f"Failed to generate FreeAgent CSV at {output_path}: {e}")
        return False


def generate_receipts_index_csv(records: List[ReceiptRecord], output_path: Path) -> bool:
    """
    Generate receipts index CSV file.
    
    Format: Receipt File, Vendor, Amount, Date, PDF Source, Page, Status
    """
    logger = get_logger()
    
    try:
        with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            
            # Header row
            writer.writerow([
                'Receipt File', 'Vendor', 'Amount', 'Date', 
                'PDF Source', 'Page', 'Status', 'Notes'
            ])
            
            # Data rows
            for record in records:
                receipt = record.receipt
                
                # Receipt file
                receipt_file = sanitize_csv_value(record.filename)
                
                # Vendor
                vendor = sanitize_csv_value(receipt.vendor or "Unknown")
                
                # Amount
                amount_str = format_amount_for_csv(receipt.amount)
                
                # Date
                date_str = format_date_for_csv(receipt.date)
                
                # PDF source
                pdf_source = sanitize_csv_value(record.pdf_name)
                
                # Page number (1-based for display)
                page_display = str(record.page_num + 1)
                
                # Status
                if record.success:
                    status = "Complete"
                    notes = ""
                else:
                    status = "Incomplete"
                    missing = []
                    if not receipt.vendor:
                        missing.append("vendor")
                    if not receipt.amount:
                        missing.append("amount")
                    if not receipt.date:
                        missing.append("date")
                    notes = f"Missing: {', '.join(missing)}"
                
                notes = sanitize_csv_value(notes)
                
                writer.writerow([
                    receipt_file, vendor, amount_str, date_str,
                    pdf_source, page_display, status, notes
                ])
        
        logger.info(f"Generated receipts index CSV with {len(records)} records at {output_path}")
        return True
    
    except OSError as e:
        logger.fail(f"Failed to generate receipts index CSV at {output_path}: {e}")
        return False


def generate_processing_summary_csv(records: List[ReceiptRecord], output_path: Path) -> bool:
    """
    Generate processing summary CSV with detailed statistics.
    """
    logger = get_logger()
    
    try:
        # Calculate statistics
        total_records = len(records)
        successful_records = len([r for r in records if r.success])
        total_amount = sum(r.receipt.amount for r in records if r.receipt.amount)
        
        # Count by extraction method
        extraction_methods = {}
        for record in records:
            for field, method in record.receipt.extraction_method.items():
                key = f"{field}_{method}"
                extraction_methods[key] = extraction_methods.get(key, 0) + 1
        
        # Count by PDF
        pdf_stats = {}
        for record in records:
            pdf_name = record.pdf_name
            if pdf_name not in pdf_stats:
                pdf_stats[pdf_name] = {'total': 0, 'successful': 0, 'amount': 0.0}
            
            pdf_stats[pdf_name]['total'] += 1
            if record.success:
                pdf_stats[pdf_name]['successful'] += 1
            if record.receipt.amount:
                pdf_stats[pdf_name]['amount'] += record.receipt.amount
        
        with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            
            # Summary section
            writer.writerow(['Processing Summary'])
            writer.writerow(['Total Records', total_records])
            writer.writerow(['Successful Records', successful_records])
            writer.writerow(['Success Rate', f"{(successful_records/total_records*100):.1f}%" if total_records > 0 else "0%"])
            writer.writerow(['Total Amount', f"£{total_amount:.2f}"])
            writer.writerow([])
            
            # Extraction methods
            writer.writerow(['Extraction Methods'])
            writer.writerow(['Method', 'Count'])
            for method, count in sorted(extraction_methods.items()):
                writer.writerow([method, count])
            writer.writerow([])
            
            # PDF statistics
            writer.writerow(['PDF Statistics'])
            writer.writerow(['PDF File', 'Total Receipts', 'Successful', 'Success Rate', 'Total Amount'])
            for pdf_name, stats in sorted(pdf_stats.items()):
                success_rate = f"{(stats['successful']/stats['total']*100):.1f}%" if stats['total'] > 0 else "0%"
                writer.writerow([
                    pdf_name,
                    stats['total'],
                    stats['successful'],
                    success_rate,
                    f"£{stats['amount']:.2f}"
                ])
        
        logger.info(f"Generated processing summary CSV at {output_path}")
        return True
    
    except OSError as e:
        logger.fail(f"Failed to generate processing summary CSV at {output_path}: {e}")
        return False


def validate_csv_output(csv_path: Path, expected_encoding: str = 'utf-8-sig') -> tuple[bool, str]:
    """
    Validate that a CSV file was written correctly.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        if not csv_path.exists():
            return False, "File does not exist"
        
        if csv_path.stat().st_size == 0:
            return False, "File is empty"
        
        # Try to read the file
        with open(csv_path, 'r', encoding=expected_encoding) as f:
            reader = csv.reader(f)
            rows = list(reader)
        
        if len(rows) < 2:  # At least header + one row
            return False, "File has no data rows"
        
        return True, "OK"
    
    except Exception as e:
        return False, f"Validation failed: {e}"


def export_all_csv_files(records: List[ReceiptRecord], output_dir: Path) -> Dict[str, bool]:
    """
    Export all CSV files to the output directory.
    
    Returns:
        Dictionary with success status for each file type
    """
    results = {}
    
    # FreeAgent CSV
    freeagent_path = output_dir / "freeagent.csv"
    results['freeagent'] = generate_freeagent_csv(records, freeagent_path)
    
    # Receipts index CSV  
    index_path = output_dir / "receipts_index.csv"
    results['receipts_index'] = generate_receipts_index_csv(records, index_path)
    
    # Processing summary CSV
    summary_path = output_dir / "processing_summary.csv"
    results['processing_summary'] = generate_processing_summary_csv(records, summary_path)
    
    return results


def get_csv_file_paths(output_dir: Path) -> Dict[str, Path]:
    """Get the expected paths for all CSV files."""
    return {
        'freeagent': output_dir / "freeagent.csv",
        'receipts_index': output_dir / "receipts_index.csv",
        'processing_summary': output_dir / "processing_summary.csv"
    }