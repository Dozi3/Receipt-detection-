"""OpenCV-based receipt detection with contour analysis and perspective correction."""

from PIL import Image
import numpy as np
from typing import List, Tuple, Optional
from pathlib import Path

from .config import OpenCVConfig
from .logging_utils import get_logger, format_pdf_log


def check_opencv_available() -> bool:
    """Check if OpenCV is available."""
    try:
        import cv2
        return True
    except ImportError:
        return False


def pil_to_cv2(pil_image: Image.Image) -> np.ndarray:
    """Convert PIL Image to OpenCV format."""
    if pil_image.mode != 'RGB':
        pil_image = pil_image.convert('RGB')
    return np.array(pil_image)[:, :, ::-1]  # RGB to BGR


def cv2_to_pil(cv2_image: np.ndarray) -> Image.Image:
    """Convert OpenCV image to PIL format."""
    if len(cv2_image.shape) == 3:
        cv2_image = cv2_image[:, :, ::-1]  # BGR to RGB
    return Image.fromarray(cv2_image)


def preprocess_image(image: np.ndarray, config: OpenCVConfig) -> np.ndarray:
    """Preprocess image for contour detection."""
    import cv2
    
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Apply Gaussian blur
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # Apply Canny edge detection
    edges = cv2.Canny(blurred, config.canny1, config.canny2)
    
    # Apply morphological closing to fill gaps
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (config.morph_close, config.morph_close))
    closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
    
    return closed


def find_receipt_contours(processed_image: np.ndarray, original_shape: Tuple[int, int], 
                         config: OpenCVConfig) -> List[np.ndarray]:
    """Find rectangular contours that could be receipts."""
    import cv2
    from .logging_utils import get_logger, log_debug, format_pdf_log
    
    logger = get_logger()
    
    # Find contours
    contours, _ = cv2.findContours(processed_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    log_debug(f"Found {len(contours)} initial contours")
    
    receipt_contours = []
    image_area = original_shape[0] * original_shape[1]
    
    for i, contour in enumerate(contours):
        try:
            # Approximate contour to polygon
            epsilon = config.quad_epsilon * cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, epsilon, True)
            
            # Only consider quadrilaterals
            if len(approx) != 4:
                log_debug(f"Contour {i}: Skipping non-quadrilateral with {len(approx)} points")
                continue
            
            # Calculate area and aspect ratio
            area = cv2.contourArea(contour)
            area_ratio = area / image_area
            
            # Filter by area
            if area_ratio < config.min_area_ratio or area_ratio > config.max_area_ratio:
                log_debug(f"Contour {i}: Skipping quad with area ratio {area_ratio:.4f} outside range [{config.min_area_ratio}, {config.max_area_ratio}]")
                continue
            
            # Calculate bounding rectangle for aspect ratio
            x, y, w, h = cv2.boundingRect(contour)
            aspect_ratio = w / h if h > 0 else 0
            
            # Filter by aspect ratio
            if aspect_ratio < config.min_aspect or aspect_ratio > config.max_aspect:
                log_debug(f"Contour {i}: Skipping quad with aspect ratio {aspect_ratio:.2f} outside range [{config.min_aspect}, {config.max_aspect}]")
                continue
            
            log_debug(f"Contour {i}: Keeping quad with area ratio {area_ratio:.4f}, aspect ratio {aspect_ratio:.2f}")
            receipt_contours.append(approx.reshape(-1, 2))
        except Exception as e:
            log_debug(f"Error processing contour {i}: {e}")
    
    log_debug(f"Found {len(receipt_contours)} valid receipt contours")
    return receipt_contours


def order_quad_points(quad: np.ndarray) -> np.ndarray:
    """Order quad points as top-left, top-right, bottom-right, bottom-left."""
    # Sum and difference of coordinates to find corners
    sums = quad.sum(axis=1)
    diffs = np.diff(quad, axis=1)
    
    ordered = np.zeros((4, 2), dtype=np.float32)
    
    # Top-left has minimum sum, bottom-right has maximum sum
    ordered[0] = quad[np.argmin(sums)]  # top-left
    ordered[2] = quad[np.argmax(sums)]  # bottom-right
    
    # Top-right has minimum difference, bottom-left has maximum difference
    ordered[1] = quad[np.argmin(diffs)]  # top-right
    ordered[3] = quad[np.argmax(diffs)]  # bottom-left
    
    return ordered


def apply_perspective_transform(image: np.ndarray, quad: np.ndarray, 
                               config: OpenCVConfig) -> Optional[np.ndarray]:
    """Apply perspective transformation to extract receipt."""
    import cv2
    from .logging_utils import log_debug
    
    try:
        # Check if quad has exactly 4 points
        if quad.shape[0] != 4:
            log_debug(f"Invalid quad shape: {quad.shape}, expected (4, 2)")
            return None
        
        # Order the quad points
        ordered_quad = order_quad_points(quad.astype(np.float32))
        
        # Calculate output dimensions
        width_top = np.sqrt(((ordered_quad[1][0] - ordered_quad[0][0]) ** 2) + 
                           ((ordered_quad[1][1] - ordered_quad[0][1]) ** 2))
        width_bottom = np.sqrt(((ordered_quad[2][0] - ordered_quad[3][0]) ** 2) + 
                              ((ordered_quad[2][1] - ordered_quad[3][1]) ** 2))
        width = max(int(width_top), int(width_bottom))
        
        height_left = np.sqrt(((ordered_quad[3][0] - ordered_quad[0][0]) ** 2) + 
                             ((ordered_quad[3][1] - ordered_quad[0][1]) ** 2))
        height_right = np.sqrt(((ordered_quad[2][0] - ordered_quad[1][0]) ** 2) + 
                              ((ordered_quad[2][1] - ordered_quad[1][1]) ** 2))
        height = max(int(height_left), int(height_right))
        
        # Validate width and height
        if width <= 0 or height <= 0:
            log_debug(f"Invalid dimensions for warping: {width}x{height}")
            return None
        
        # Limit the size to warp_long_edge_px
        if width > height:
            if width > config.warp_long_edge_px:
                height = int(height * config.warp_long_edge_px / width)
                width = config.warp_long_edge_px
        else:
            if height > config.warp_long_edge_px:
                width = int(width * config.warp_long_edge_px / height)
                height = config.warp_long_edge_px
        
        # Double-check dimensions
        if width <= 0 or height <= 0:
            log_debug(f"Invalid dimensions after scaling: {width}x{height}")
            return None
        
        # Define destination points
        dst_points = np.array([
            [0, 0],
            [width - 1, 0],
            [width - 1, height - 1],
            [0, height - 1]
        ], dtype=np.float32)
        
        # Calculate perspective transform matrix
        matrix = cv2.getPerspectiveTransform(ordered_quad, dst_points)
        
        # Apply transformation
        warped = cv2.warpPerspective(image, matrix, (width, height))
        
        # Validate output
        if warped is None or warped.size == 0 or warped.shape[0] == 0 or warped.shape[1] == 0:
            log_debug("Warping produced invalid image")
            return None
        
        log_debug(f"Warped dimensions: {warped.shape[1]}x{warped.shape[0]}")
        
        # Add padding
        if config.pad_px > 0:
            warped = cv2.copyMakeBorder(
                warped, config.pad_px, config.pad_px, config.pad_px, config.pad_px,
                cv2.BORDER_CONSTANT, value=[255, 255, 255]
            )
        
        return warped
        
    except Exception as e:
        log_debug(f"Error in perspective transform: {e}")
        return None


def remove_overlapping_quads(quads: List[np.ndarray], overlap_threshold: float = 0.5) -> List[np.ndarray]:
    """Remove overlapping quadrilaterals using intersection over union."""
    import cv2
    from .logging_utils import log_debug
    
    if len(quads) <= 1:
        return quads
    
    # Calculate areas and sort by area (largest first)
    quad_areas = []
    for i, quad in enumerate(quads):
        try:
            area = cv2.contourArea(quad)
            quad_areas.append((i, area))
        except Exception as e:
            log_debug(f"Error calculating area for quad {i}: {e}")
            continue
    
    quad_areas.sort(key=lambda x: x[1], reverse=True)
    
    keep = []
    for i, area in quad_areas:
        if area <= 0:
            log_debug(f"Skipping quad {i} with non-positive area: {area}")
            continue
            
        quad_i = quads[i]
        
        # Check overlap with already kept quads
        overlaps = False
        for j in keep:
            try:
                quad_j = quads[j]
                
                # Simple bounding box overlap check
                x1_i, y1_i = quad_i.min(axis=0)
                x2_i, y2_i = quad_i.max(axis=0)
                x1_j, y1_j = quad_j.min(axis=0)
                x2_j, y2_j = quad_j.max(axis=0)
                
                # Calculate intersection
                x1 = max(x1_i, x1_j)
                y1 = max(y1_i, y1_j)
                x2 = min(x2_i, x2_j)
                y2 = min(y2_i, y2_j)
                
                if x1 < x2 and y1 < y2:
                    intersection = (x2 - x1) * (y2 - y1)
                    area_i = (x2_i - x1_i) * (y2_i - y1_i)
                    area_j = (x2_j - x1_j) * (y2_j - y1_j)
                    
                    if area_i <= 0 or area_j <= 0:
                        continue
                        
                    union = area_i + area_j - intersection
                    
                    if union > 0 and intersection / union > overlap_threshold:
                        log_debug(f"Quad {i} overlaps with quad {j} (IoU: {intersection/union:.3f})")
                        overlaps = True
                        break
            except Exception as e:
                log_debug(f"Error checking overlap between quads {i} and {j}: {e}")
                continue
        
        if not overlaps:
            keep.append(i)
    
    result = [quads[i] for i in sorted(keep)]
    log_debug(f"Kept {len(result)} quads after overlap removal")
    
    return result


def sort_quads_reading_order(quads: List[np.ndarray]) -> List[np.ndarray]:
    """Sort quadrilaterals in reading order (top to bottom, left to right)."""
    if not quads:
        return quads
    
    # Calculate center points
    centers = []
    for quad in quads:
        center = quad.mean(axis=0)
        centers.append(center)
    
    # Sort by Y coordinate first (top to bottom), then X coordinate (left to right)
    sorted_indices = sorted(range(len(centers)), key=lambda i: (centers[i][1], centers[i][0]))
    
    return [quads[i] for i in sorted_indices]


def detect_receipts_opencv(images: List[Image.Image], pdf_path: str, page_num: int, 
                          config: OpenCVConfig) -> List[Image.Image]:
    """
    OpenCV-based receipt detection with contour analysis.
    
    Args:
        images: List of PIL Images from PDF page
        pdf_path: Path to PDF file (for logging)
        page_num: Page number (0-based, for logging)
        config: OpenCV configuration parameters
    
    Returns:
        List of detected receipt images
    """
    logger = get_logger()
    
    if not check_opencv_available():
        logger.fail(format_pdf_log(pdf_path, page_num + 1, "OpenCV not available, cannot use opencv detection method"))
        return []
    
    if not images:
        logger.fail(format_pdf_log(pdf_path, page_num + 1, "no images to process"))
        return []
    
    # Use the largest image as the main canvas
    main_image = max(images, key=lambda img: img.size[0] * img.size[1])
    
    try:
        cv_image = pil_to_cv2(main_image)
    except Exception as e:
        logger.warn(format_pdf_log(pdf_path, page_num + 1, f"failed to convert image to OpenCV format: {e}"))
        logger.info(format_pdf_log(pdf_path, page_num + 1, "1 receipts detected (method=opencv-fallback)"))
        return [main_image]  # Return original image as fallback
    
    logger.info(format_pdf_log(pdf_path, page_num + 1, 
                             f"processing image ({main_image.size[0]}x{main_image.size[1]}) for receipt detection"))
    
    try:
        # Preprocess image
        processed = preprocess_image(cv_image, config)
        
        # Find receipt contours
        quads = find_receipt_contours(processed, cv_image.shape[:2], config)
        
        logger.debug(format_pdf_log(pdf_path, page_num + 1, f"found {len(quads)} potential receipt contours"))
        
        if not quads:
            logger.info(format_pdf_log(pdf_path, page_num + 1, "no receipt contours found, using whole page"))
            logger.info(format_pdf_log(pdf_path, page_num + 1, "1 receipts detected (method=opencv-whole-page)"))
            return [main_image]
        
        # Remove overlapping quads
        quads = remove_overlapping_quads(quads)
        logger.debug(format_pdf_log(pdf_path, page_num + 1, f"after removing overlaps: {len(quads)} contours"))
        
        # Sort in reading order
        quads = sort_quads_reading_order(quads)
        
        # Extract receipts using perspective transformation
        receipts = []
        for i, quad in enumerate(quads):
            try:
                warped = apply_perspective_transform(cv_image, quad, config)
                if warped is not None and warped.shape[0] > 0 and warped.shape[1] > 0:
                    receipt_image = cv2_to_pil(warped)
                    receipts.append(receipt_image)
                    logger.info(format_pdf_log(pdf_path, page_num + 1, 
                                             f"extracted receipt {i+1} ({receipt_image.size[0]}x{receipt_image.size[1]})"))
                else:
                    logger.warn(format_pdf_log(pdf_path, page_num + 1, 
                                             f"skipping receipt {i+1}: invalid warped image"))
            except Exception as e:
                logger.warn(format_pdf_log(pdf_path, page_num + 1, f"failed to extract receipt {i+1}: {e}"))
        
        if not receipts:
            logger.info(format_pdf_log(pdf_path, page_num + 1, "no receipts extracted, using whole page"))
            receipts = [main_image]
        
        logger.info(format_pdf_log(pdf_path, page_num + 1, 
                                 f"{len(receipts)} receipts detected (method=opencv)"))
        
        return receipts
        
    except Exception as e:
        logger.warn(format_pdf_log(pdf_path, page_num + 1, f"opencv detection failed: {e}, using whole page"))
        logger.info(format_pdf_log(pdf_path, page_num + 1, "1 receipts detected (method=opencv-error-fallback)"))
        return [main_image]  # Return original image as fallback