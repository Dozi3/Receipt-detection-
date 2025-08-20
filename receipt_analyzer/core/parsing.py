"""Text parsing for extracting amount, date, and vendor information from OCR text."""

import re
from typing import Optional, Tuple, List, Dict
from datetime import datetime, date
from pathlib import Path

from .config import ParsingConfig
from .logging_utils import get_logger, format_receipt_log


class ParsedReceipt:
    """Container for parsed receipt information."""
    
    def __init__(self):
        self.vendor: Optional[str] = None
        self.amount: Optional[float] = None
        self.date: Optional[date] = None
        self.raw_text: str = ""
        self.extraction_method: Dict[str, str] = {}
        self.confidence: Dict[str, float] = {}


def extract_amounts(text: str) -> List[Tuple[float, str]]:
    """
    Extract monetary amounts from text.
    
    Returns:
        List of tuples (amount, matched_text)
    """
    amounts = []
    
    # Pattern for GBP amounts with £ symbol
    gbp_pattern = r'£\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?|\d+\.\d{2})'
    for match in re.finditer(gbp_pattern, text, re.IGNORECASE):
        try:
            amount_str = match.group(1).replace(',', '')
            amount = float(amount_str)
            amounts.append((amount, match.group(0)))
        except ValueError:
            continue
    
    # Pattern for decimal amounts (e.g., 12.34, 1,234.56)
    decimal_pattern = r'\b(\d{1,3}(?:,\d{3})*\.\d{2})\b'
    for match in re.finditer(decimal_pattern, text):
        try:
            amount_str = match.group(1).replace(',', '')
            amount = float(amount_str)
            # Only include if it looks like a price (reasonable range)
            if 0.01 <= amount <= 10000.00:
                amounts.append((amount, match.group(0)))
        except ValueError:
            continue
    
    # Pattern for whole numbers that might be amounts
    whole_pattern = r'\b(\d{1,4})\s*(?:GBP|£|pounds?)\b'
    for match in re.finditer(whole_pattern, text, re.IGNORECASE):
        try:
            amount = float(match.group(1))
            if 1 <= amount <= 1000:  # Reasonable range for whole number amounts
                amounts.append((amount, match.group(0)))
        except ValueError:
            continue
    
    return amounts


def find_largest_amount(text: str) -> Optional[Tuple[float, str]]:
    """Find the largest plausible amount in the text."""
    amounts = extract_amounts(text)
    
    if not amounts:
        return None
    
    # Return the largest amount
    return max(amounts, key=lambda x: x[0])


def extract_dates(text: str) -> List[Tuple[date, str]]:
    """
    Extract dates from text in various formats.
    
    Returns:
        List of tuples (date_object, matched_text)
    """
    dates = []
    
    # DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY patterns
    date_patterns = [
        r'\b(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{4})\b',
        r'\b(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{2})\b',  # Short year
    ]
    
    for pattern in date_patterns:
        for match in re.finditer(pattern, text):
            try:
                day, month, year = match.groups()
                day, month = int(day), int(month)
                year = int(year)
                
                # Handle short year (assume 20xx)
                if year < 100:
                    if year < 50:
                        year += 2000
                    else:
                        year += 1900
                
                # Validate ranges
                if 1 <= day <= 31 and 1 <= month <= 12 and 1900 <= year <= 2100:
                    try:
                        date_obj = date(year, month, day)
                        dates.append((date_obj, match.group(0)))
                    except ValueError:
                        # Invalid date (e.g., Feb 30)
                        continue
            except ValueError:
                continue
    
    # DD Mon YYYY, DD Month YYYY patterns
    month_names = {
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
        'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
        'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6,
        'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12
    }
    
    month_pattern = r'\b(\d{1,2})\s+([a-z]+)\s+(\d{4})\b'
    for match in re.finditer(month_pattern, text, re.IGNORECASE):
        try:
            day_str, month_str, year_str = match.groups()
            day = int(day_str)
            year = int(year_str)
            month_name = month_str.lower()
            
            if month_name in month_names:
                month = month_names[month_name]
                if 1 <= day <= 31 and 1900 <= year <= 2100:
                    try:
                        date_obj = date(year, month, day)
                        dates.append((date_obj, match.group(0)))
                    except ValueError:
                        continue
        except ValueError:
            continue
    
    return dates


def find_most_recent_date(text: str) -> Optional[Tuple[date, str]]:
    """Find the most recent date in the text."""
    dates = extract_dates(text)
    
    if not dates:
        return None
    
    # Return the most recent date
    return max(dates, key=lambda x: x[0])


def extract_vendor_from_email(text: str, ignored_domains: List[str] = None) -> Optional[str]:
    """Extract vendor name from email addresses."""
    if ignored_domains is None:
        ignored_domains = ['gmail.com', 'outlook.com', 'hotmail.com', 'yahoo.com', 'icloud.com', 'proton.me']
    
    # Look for email patterns
    email_pattern = r'\b[a-zA-Z0-9._%+-]+@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b'
    
    for match in re.finditer(email_pattern, text, re.IGNORECASE):
        domain = match.group(1).lower()
        
        # Skip generic email providers
        if domain in [d.lower() for d in ignored_domains]:
            continue
        
        # Extract company name from domain
        # Remove common prefixes and get the main part
        domain_parts = domain.split('.')
        if len(domain_parts) >= 2:
            company_name = domain_parts[-2]  # Second-to-last part (before TLD)
            
            # Clean up the company name
            company_name = company_name.replace('-', ' ').replace('_', ' ')
            company_name = ' '.join(word.capitalize() for word in company_name.split())
            
            return company_name
    
    return None


def extract_vendor_from_keywords(text: str, keyword_map: Dict[str, str]) -> Optional[str]:
    """Extract vendor name using keyword mapping."""
    if not keyword_map:
        return None
    
    text_lower = text.lower()
    
    # Sort keywords by length (longest first) for better matching
    sorted_keywords = sorted(keyword_map.keys(), key=len, reverse=True)
    
    for keyword in sorted_keywords:
        if keyword.lower() in text_lower:
            return keyword_map[keyword]
    
    return None


def extract_vendor_from_first_line(text: str) -> Optional[str]:
    """Extract vendor name from the first clean line of text."""
    lines = text.strip().split('\n')
    
    blacklist_patterns = [
        r'^\d+$',  # Pure numbers
        r'^\d+[/\-\.]\d+[/\-\.]\d+$',  # Dates
        r'^£?\d+\.?\d*$',  # Amounts
        r'^receipt$',  # Generic words
        r'^invoice$',
        r'^bill$',
        r'^payment$',
        r'^total$',
        r'^tax$',
        r'^vat$',
        r'^\d+:\d+$',  # Times
        r'^[a-z]{1,3}\s+\d+$',  # Short codes with numbers
    ]
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Skip if matches blacklist patterns
        skip = False
        for pattern in blacklist_patterns:
            if re.match(pattern, line, re.IGNORECASE):
                skip = True
                break
        
        if skip:
            continue
        
        # Clean the line
        clean_line = re.sub(r'[^\w\s&\-]', '', line)
        clean_line = ' '.join(clean_line.split())
        
        if len(clean_line) >= 3:  # Minimum reasonable length
            return clean_line.title()
    
    return None


def parse_receipt_text(text: str, keyword_map: Dict[str, str] = None, 
                      ignored_domains: List[str] = None, pdf_path: str = "", 
                      page_num: int = 0, receipt_num: int = 0) -> ParsedReceipt:
    """
    Parse receipt text to extract vendor, amount, and date.
    
    Args:
        text: OCR-extracted text
        keyword_map: Dictionary mapping keywords to vendor names
        ignored_domains: List of email domains to ignore for vendor extraction
        pdf_path: Path to PDF file (for logging)
        page_num: Page number (0-based, for logging)
        receipt_num: Receipt number (0-based, for logging)
    
    Returns:
        ParsedReceipt object with extracted information
    """
    logger = get_logger()
    receipt = ParsedReceipt()
    receipt.raw_text = text
    
    if keyword_map is None:
        keyword_map = {}
    
    # Extract amount
    amount_result = find_largest_amount(text)
    if amount_result:
        receipt.amount = amount_result[0]
        receipt.extraction_method['amount'] = f"largest amount: {amount_result[1]}"
        receipt.confidence['amount'] = 0.8  # High confidence for amount extraction
        logger.info(format_receipt_log(pdf_path, page_num + 1, receipt_num + 1,
                                     f"extracted amount: £{receipt.amount:.2f}"))
    else:
        logger.warn(format_receipt_log(pdf_path, page_num + 1, receipt_num + 1, "no amount found"))
    
    # Extract date
    date_result = find_most_recent_date(text)
    if date_result:
        receipt.date = date_result[0]
        receipt.extraction_method['date'] = f"most recent date: {date_result[1]}"
        receipt.confidence['date'] = 0.8  # High confidence for date extraction
        logger.info(format_receipt_log(pdf_path, page_num + 1, receipt_num + 1,
                                     f"extracted date: {receipt.date.strftime('%d-%m-%Y')}"))
    else:
        logger.warn(format_receipt_log(pdf_path, page_num + 1, receipt_num + 1, "no date found"))
    
    # Extract vendor (try multiple methods in priority order)
    
    # 1. Try email domain extraction
    vendor_email = extract_vendor_from_email(text, ignored_domains)
    if vendor_email:
        receipt.vendor = vendor_email
        receipt.extraction_method['vendor'] = "email domain"
        receipt.confidence['vendor'] = 0.9
        logger.info(format_receipt_log(pdf_path, page_num + 1, receipt_num + 1,
                                     f"extracted vendor from email: {receipt.vendor}"))
        return receipt
    
    # 2. Try keyword mapping
    vendor_keyword = extract_vendor_from_keywords(text, keyword_map)
    if vendor_keyword:
        receipt.vendor = vendor_keyword
        receipt.extraction_method['vendor'] = "keyword mapping"
        receipt.confidence['vendor'] = 0.8
        logger.info(format_receipt_log(pdf_path, page_num + 1, receipt_num + 1,
                                     f"extracted vendor from keywords: {receipt.vendor}"))
        return receipt
    
    # 3. Try first clean line
    vendor_line = extract_vendor_from_first_line(text)
    if vendor_line:
        receipt.vendor = vendor_line
        receipt.extraction_method['vendor'] = "first clean line"
        receipt.confidence['vendor'] = 0.6
        logger.info(format_receipt_log(pdf_path, page_num + 1, receipt_num + 1,
                                     f"extracted vendor from first line: {receipt.vendor}"))
        return receipt
    
    logger.warn(format_receipt_log(pdf_path, page_num + 1, receipt_num + 1, "no vendor found"))
    
    return receipt


def format_amount_for_filename(amount: Optional[float]) -> str:
    """Format amount for use in filename (12.34 -> 12-34)."""
    if amount is None:
        return "00-00"
    
    # Format to 2 decimal places and replace dot with dash
    return f"{amount:.2f}".replace('.', '-')


def format_date_for_filename(date_obj: Optional[date]) -> str:
    """Format date for use in filename (DD-MM-YYYY)."""
    if date_obj is None:
        return datetime.now().strftime('%d-%m-%Y')
    
    return date_obj.strftime('%d-%m-%Y')