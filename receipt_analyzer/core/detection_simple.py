"""Simple receipt detection - uses images as-is without advanced processing."""

from PIL import Image
from typing import List
from pathlib import Path

from .logging_utils import get_logger, format_pdf_log


def detect_receipts_simple(images: List[Image.Image], pdf_path: str, page_num: int) -> List[Image.Image]:
    """
    Simple detection method - returns input images as-is.
    
    This method assumes each input image is already a receipt or contains
    a single receipt that doesn't need further processing.
    
    Args:
        images: List of PIL Images from PDF page
        pdf_path: Path to PDF file (for logging)
        page_num: Page number (0-based, for logging)
    
    Returns:
        List of receipt images (same as input)
    """
    logger = get_logger()
    
    if not images:
        logger.fail(format_pdf_log(pdf_path, page_num + 1, "no images to process"))
        return []
    
    # In simple mode, we just return the input images as receipt crops
    receipts = []
    for i, image in enumerate(images):
        # Validate the image
        if image.size[0] < 50 or image.size[1] < 50:
            logger.warn(format_pdf_log(pdf_path, page_num + 1, 
                                     f"image {i+1} too small ({image.size[0]}x{image.size[1]}), skipping"))
            continue
        
        receipts.append(image)
        logger.info(format_pdf_log(pdf_path, page_num + 1, 
                                 f"accepted image {i+1} as receipt ({image.size[0]}x{image.size[1]})"))
    
    logger.info(format_pdf_log(pdf_path, page_num + 1, 
                             f"{len(receipts)} receipts detected (method=simple)"))
    
    return receipts


def validate_simple_receipt(image: Image.Image, min_width: int = 50, min_height: int = 50) -> bool:
    """
    Validate that an image is suitable as a receipt.
    
    Args:
        image: PIL Image to validate
        min_width: Minimum width in pixels
        min_height: Minimum height in pixels
    
    Returns:
        True if image passes validation
    """
    if image.size[0] < min_width or image.size[1] < min_height:
        return False
    
    # Could add more validation here:
    # - Check for reasonable aspect ratio
    # - Check for sufficient contrast
    # - Check for text content
    
    return True