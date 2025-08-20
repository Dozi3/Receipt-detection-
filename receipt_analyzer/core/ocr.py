"""OCR processing with Tesseract and automatic orientation detection."""

import pytesseract
from PIL import Image
import numpy as np
from typing import Dict, Tuple, Optional, List
from pathlib import Path

from .config import OCRConfig
from .logging_utils import get_logger, format_receipt_log


def check_tesseract_available() -> Tuple[bool, str]:
    """Check if Tesseract OCR is available and get version info."""
    try:
        version = pytesseract.get_tesseract_version()
        return True, f"Tesseract {version}"
    except Exception as e:
        return False, f"Tesseract not available: {e}"


def resize_image_for_ocr(image: Image.Image, max_edge: int) -> Image.Image:
    """Resize image if it's too large for optimal OCR performance."""
    width, height = image.size
    
    if max(width, height) <= max_edge:
        return image
    
    # Calculate new dimensions
    if width > height:
        new_width = max_edge
        new_height = int(height * max_edge / width)
    else:
        new_height = max_edge
        new_width = int(width * max_edge / height)
    
    return image.resize((new_width, new_height), Image.Resampling.LANCZOS)


def rotate_image(image: Image.Image, angle: int) -> Image.Image:
    """Rotate image by specified angle (0, 90, 180, 270 degrees)."""
    if angle == 0:
        return image
    elif angle == 90:
        return image.transpose(Image.Transpose.ROTATE_90)
    elif angle == 180:
        return image.transpose(Image.Transpose.ROTATE_180)
    elif angle == 270:
        return image.transpose(Image.Transpose.ROTATE_270)
    else:
        raise ValueError(f"Invalid rotation angle: {angle}. Must be 0, 90, 180, or 270.")


def get_text_confidence_scores(image: Image.Image, config: OCRConfig) -> Dict[str, float]:
    """Get confidence scores for text at different orientations."""
    from .logging_utils import log_debug
    
    confidences = {}
    
    # Skip orientation detection for very small images
    width, height = image.size
    if width < 100 or height < 100:
        log_debug(f"Image too small for orientation detection ({width}x{height}), using 0°")
        confidences["0°"] = 0
        confidences["90°"] = 0
        confidences["180°"] = 0
        confidences["270°"] = 0
        return confidences
    
    # Test each orientation
    for angle in [0, 90, 180, 270]:
        try:
            # Rotate image
            rotated = rotate_image(image, angle)
            
            # Perform OCR with detailed data
            custom_config = f'--psm {config.psm} --oem {config.oem} -l {config.language}'
            data = pytesseract.image_to_data(rotated, config=custom_config, output_type=pytesseract.Output.DICT)
            
            # Calculate mean confidence for text with confidence > 0
            conf_scores = [int(conf) for conf in data['conf'] if int(conf) > 0]
            if conf_scores:
                mean_confidence = sum(conf_scores) / len(conf_scores)
                log_debug(f"Angle {angle}°: {len(conf_scores)} words, avg confidence {mean_confidence:.1f}")
            else:
                mean_confidence = 0
                log_debug(f"Angle {angle}°: no words detected")
            
            confidences[f"{angle}°"] = mean_confidence
            
        except Exception as e:
            log_debug(f"Error checking angle {angle}°: {e}")
            confidences[f"{angle}°"] = 0
    
    return confidences


def find_best_orientation(image: Image.Image, config: OCRConfig) -> Tuple[int, Dict[str, float]]:
    """Find the best orientation for OCR by testing all rotations."""
    confidences = get_text_confidence_scores(image, config)
    
    # Find angle with highest confidence
    best_angle = 0
    best_confidence = 0
    
    for angle_str, confidence in confidences.items():
        angle = int(angle_str.replace('°', ''))
        if confidence > best_confidence:
            best_confidence = confidence
            best_angle = angle
    
    return best_angle, confidences


def extract_text_with_orientation(image: Image.Image, config: OCRConfig) -> Tuple[str, int, Dict[str, float]]:
    """
    Extract text from image with automatic orientation detection.
    
    Args:
        image: PIL Image to process
        config: OCR configuration
    
    Returns:
        Tuple of (extracted_text, best_angle, confidence_scores)
    """
    # Resize image if needed
    image = resize_image_for_ocr(image, config.max_edge)
    
    # Find best orientation
    best_angle, confidences = find_best_orientation(image, config)
    
    # Extract text using best orientation
    best_image = rotate_image(image, best_angle)
    custom_config = f'--psm {config.psm} --oem {config.oem} -l {config.language}'
    text = pytesseract.image_to_string(best_image, config=custom_config)
    
    return text.strip(), best_angle, confidences


def extract_text_simple(image: Image.Image, config: OCRConfig) -> str:
    """
    Simple text extraction without orientation detection.
    
    Args:
        image: PIL Image to process
        config: OCR configuration
    
    Returns:
        Extracted text
    """
    # Resize image if needed
    image = resize_image_for_ocr(image, config.max_edge)
    
    # Extract text
    custom_config = f'--psm {config.psm} --oem {config.oem} -l {config.language}'
    text = pytesseract.image_to_string(image, config=custom_config)
    
    return text.strip()


def get_word_boxes(image: Image.Image, config: OCRConfig) -> List[Dict]:
    """
    Get bounding boxes and confidence scores for individual words.
    
    Args:
        image: PIL Image to process
        config: OCR configuration
    
    Returns:
        List of dictionaries containing word information
    """
    # Resize image if needed
    image = resize_image_for_ocr(image, config.max_edge)
    
    # Get detailed OCR data
    custom_config = f'--psm {config.psm} --oem {config.oem} -l {config.language}'
    data = pytesseract.image_to_data(image, config=custom_config, output_type=pytesseract.Output.DICT)
    
    words = []
    for i in range(len(data['text'])):
        text = data['text'][i].strip()
        if text:  # Only include non-empty text
            word_info = {
                'text': text,
                'confidence': int(data['conf'][i]),
                'left': int(data['left'][i]),
                'top': int(data['top'][i]),
                'width': int(data['width'][i]),
                'height': int(data['height'][i]),
                'level': int(data['level'][i])
            }
            words.append(word_info)
    
    return words


def perform_ocr(image: Image.Image, config: OCRConfig, pdf_path: str, page_num: int, 
                receipt_num: int, auto_orient: bool = True) -> Tuple[str, Dict]:
    """
    Perform OCR on a receipt image with optional orientation detection.
    
    Args:
        image: PIL Image of the receipt
        config: OCR configuration
        pdf_path: Path to PDF file (for logging)
        page_num: Page number (0-based, for logging)
        receipt_num: Receipt number (0-based, for logging)
        auto_orient: Whether to perform automatic orientation detection
    
    Returns:
        Tuple of (extracted_text, metadata_dict)
    """
    logger = get_logger()
    
    # Check if image is valid
    if image is None:
        logger.warn(format_receipt_log(pdf_path, page_num + 1, receipt_num + 1, 
                                     "OCR skipped: null image"))
        return "", {}
        
    # Check image dimensions
    width, height = image.size
    if width < 20 or height < 20:
        logger.warn(format_receipt_log(pdf_path, page_num + 1, receipt_num + 1, 
                                     f"OCR skipped: image too small ({width}x{height})"))
        return "", {}
    
    # Check Tesseract availability with timeout
    tesseract_available, tesseract_msg = check_tesseract_available()
    if not tesseract_available:
        logger.fail(format_receipt_log(pdf_path, page_num + 1, receipt_num + 1, 
                                     f"Tesseract not available: {tesseract_msg}"))
        return "", {}
    
    try:
        metadata = {
            'original_size': image.size,
            'auto_orient': auto_orient
        }
        
        if auto_orient:
            try:
                text, best_angle, confidences = extract_text_with_orientation(image, config)
                metadata.update({
                    'best_angle': best_angle,
                    'confidence_scores': confidences,
                    'best_confidence': confidences.get(f"{best_angle}°", 0)
                })
                
                logger.info(format_receipt_log(pdf_path, page_num + 1, receipt_num + 1,
                                            f"OCR completed (angle: {best_angle}°, confidence: {metadata['best_confidence']:.1f})"))
            except Exception as e:
                logger.warn(format_receipt_log(pdf_path, page_num + 1, receipt_num + 1,
                                            f"Orientation detection failed: {e}, falling back to default orientation"))
                # Fallback to simple OCR
                text = extract_text_simple(image, config)
                metadata.update({
                    'best_angle': 0,
                    'confidence_scores': {'0°': 0},
                    'best_confidence': 0
                })
        else:
            text = extract_text_simple(image, config)
            metadata.update({
                'best_angle': 0,
                'confidence_scores': {'0°': 0},
                'best_confidence': 0
            })
            
            logger.info(format_receipt_log(pdf_path, page_num + 1, receipt_num + 1, "OCR completed (no orientation detection)"))
        
        # Log text preview
        text_preview = text.replace('\n', ' ').strip()[:120]
        if len(text) > 120:
            text_preview += "..."
        
        if text_preview:
            logger.info(format_receipt_log(pdf_path, page_num + 1, receipt_num + 1, 
                                         f"extracted text preview: {text_preview}"))
        else:
            logger.warn(format_receipt_log(pdf_path, page_num + 1, receipt_num + 1, "no text extracted"))
        
        return text, metadata
    
    except Exception as e:
        logger.fail(format_receipt_log(pdf_path, page_num + 1, receipt_num + 1, f"OCR failed: {e}"))
        return "", {}


def extract_text_from_image(image: Image.Image, config: OCRConfig = None) -> str:
    """
    Simple wrapper function for text extraction from image.
    
    Args:
        image: PIL Image to process
        config: OCR configuration (optional, uses default if None)
    
    Returns:
        Extracted text string
    """
    if config is None:
        # Create default config if none provided
        config = OCRConfig()
    
    try:
        text, _ = extract_text_with_orientation(image, config)
        return text
    except Exception:
        # Fallback to simple extraction if orientation detection fails
        return extract_text_simple(image, config)


def validate_ocr_quality(text: str, min_words: int = 3, min_chars: int = 10) -> Tuple[bool, str]:
    """
    Validate OCR quality based on extracted text.
    
    Args:
        text: Extracted text
        min_words: Minimum number of words expected
        min_chars: Minimum number of characters expected
    
    Returns:
        Tuple of (is_valid, reason)
    """
    if not text or not text.strip():
        return False, "No text extracted"
    
    words = text.split()
    if len(words) < min_words:
        return False, f"Too few words ({len(words)} < {min_words})"
    
    if len(text.strip()) < min_chars:
        return False, f"Too few characters ({len(text.strip())} < {min_chars})"
    
    # Check for reasonable character distribution
    alpha_chars = sum(1 for c in text if c.isalpha())
    if alpha_chars < len(text.strip()) * 0.3:  # At least 30% alphabetic characters
        return False, "Too few alphabetic characters"
    
    return True, "OK"