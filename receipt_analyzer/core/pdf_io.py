"""PDF input/output operations with PyMuPDF and optional pdf2image fallback."""

import fitz  # PyMuPDF
from PIL import Image
from pathlib import Path
from typing import List, Tuple, Optional, Union
import io

from .logging_utils import get_logger, format_pdf_log


def check_dependencies() -> Tuple[bool, List[str]]:
    """Check if required and optional dependencies are available."""
    missing = []
    warnings = []
    
    # Check required dependencies
    try:
        import fitz
    except ImportError:
        missing.append("PyMuPDF (fitz) - required for PDF processing")
    
    try:
        from PIL import Image
    except ImportError:
        missing.append("Pillow - required for image processing")
    
    # Check optional dependencies
    try:
        import pdf2image
    except ImportError:
        warnings.append("pdf2image not available - PDF rasterization fallback unavailable")
    
    try:
        from pdf2image import convert_from_path
    except ImportError:
        warnings.append("Poppler not available - PDF rasterization fallback unavailable")
    
    return len(missing) == 0, missing + warnings


def extract_embedded_images(pdf_path: Path, page_num: int) -> List[Image.Image]:
    """Extract embedded images from a PDF page using PyMuPDF."""
    logger = get_logger()
    images = []
    
    try:
        doc = fitz.open(pdf_path)
        
        if page_num >= len(doc):
            logger.fail(format_pdf_log(str(pdf_path), page_num + 1, "page number out of range"))
            return []
        
        page = doc[page_num]
        image_list = page.get_images()
        
        if not image_list:
            logger.info(format_pdf_log(str(pdf_path), page_num + 1, "no embedded images found"))
            return []
        
        for img_index, img in enumerate(image_list):
            try:
                # Get image data
                xref = img[0]
                pix = fitz.Pixmap(doc, xref)
                
                # Convert to PIL Image
                if pix.n - pix.alpha < 4:  # GRAY or RGB
                    img_data = pix.tobytes("ppm")
                    pil_image = Image.open(io.BytesIO(img_data))
                else:  # CMYK
                    img_data = pix.tobytes("ppm")
                    pil_image = Image.open(io.BytesIO(img_data))
                
                images.append(pil_image)
                logger.info(format_pdf_log(str(pdf_path), page_num + 1, 
                                         f"extracted embedded image {img_index + 1} ({pil_image.size[0]}x{pil_image.size[1]})"))
                
                pix = None  # Free memory
                
            except Exception as e:
                logger.warn(format_pdf_log(str(pdf_path), page_num + 1, 
                                         f"failed to extract embedded image {img_index + 1}: {e}"))
        
        doc.close()
        
    except Exception as e:
        logger.fail(format_pdf_log(str(pdf_path), page_num + 1, f"failed to extract embedded images: {e}"))
    
    return images


def rasterize_page_pymupdf(pdf_path: Path, page_num: int, dpi: int = 200) -> Optional[Image.Image]:
    """Rasterize a PDF page using PyMuPDF."""
    logger = get_logger()
    
    try:
        doc = fitz.open(pdf_path)
        
        if page_num >= len(doc):
            logger.fail(format_pdf_log(str(pdf_path), page_num + 1, "page number out of range"))
            return None
        
        page = doc[page_num]
        
        # Calculate zoom factor for desired DPI
        mat = fitz.Matrix(dpi / 72.0, dpi / 72.0)
        pix = page.get_pixmap(matrix=mat)
        
        # Convert to PIL Image
        img_data = pix.tobytes("ppm")
        pil_image = Image.open(io.BytesIO(img_data))
        
        logger.info(format_pdf_log(str(pdf_path), page_num + 1, 
                                 f"rasterized page at {dpi} DPI ({pil_image.size[0]}x{pil_image.size[1]})"))
        
        pix = None  # Free memory
        doc.close()
        
        return pil_image
        
    except Exception as e:
        logger.fail(format_pdf_log(str(pdf_path), page_num + 1, f"PyMuPDF rasterization failed: {e}"))
        return None


def rasterize_page_pdf2image(pdf_path: Path, page_num: int, dpi: int = 200) -> Optional[Image.Image]:
    """Rasterize a PDF page using pdf2image (requires Poppler)."""
    logger = get_logger()
    
    try:
        from pdf2image import convert_from_path
        
        # Convert single page
        images = convert_from_path(
            pdf_path,
            dpi=dpi,
            first_page=page_num + 1,
            last_page=page_num + 1
        )
        
        if images:
            image = images[0]
            logger.info(format_pdf_log(str(pdf_path), page_num + 1, 
                                     f"rasterized page with pdf2image at {dpi} DPI ({image.size[0]}x{image.size[1]})"))
            return image
        else:
            logger.fail(format_pdf_log(str(pdf_path), page_num + 1, "pdf2image returned no images"))
            return None
            
    except ImportError:
        logger.warn(format_pdf_log(str(pdf_path), page_num + 1, "pdf2image not available"))
        return None
    except Exception as e:
        logger.fail(format_pdf_log(str(pdf_path), page_num + 1, f"pdf2image rasterization failed: {e}"))
        return None


def get_page_images(pdf_path: Path, page_num: int, dpi: int = 200) -> List[Image.Image]:
    """Get images from a PDF page, trying embedded images first, then rasterization."""
    logger = get_logger()
    
    # Try embedded images first
    images = extract_embedded_images(pdf_path, page_num)
    if images:
        return images
    
    # Fallback to rasterization
    logger.info(format_pdf_log(str(pdf_path), page_num + 1, "no embedded images, trying rasterization"))
    
    # Try PyMuPDF rasterization first
    raster_image = rasterize_page_pymupdf(pdf_path, page_num, dpi)
    if raster_image:
        return [raster_image]
    
    # Try pdf2image as fallback
    logger.info(format_pdf_log(str(pdf_path), page_num + 1, "PyMuPDF rasterization failed, trying pdf2image"))
    raster_image = rasterize_page_pdf2image(pdf_path, page_num, dpi)
    if raster_image:
        return [raster_image]
    
    # Complete failure
    logger.fail(format_pdf_log(str(pdf_path), page_num + 1, "no receipts detected"))
    return []


def get_pdf_page_count(pdf_path: Path) -> int:
    """Get the number of pages in a PDF."""
    try:
        doc = fitz.open(pdf_path)
        page_count = len(doc)
        doc.close()
        return page_count
    except Exception as e:
        logger = get_logger()
        logger.fail(f"Failed to get page count for {pdf_path}: {e}")
        return 0


def is_valid_pdf(pdf_path: Path) -> bool:
    """Check if a file is a valid PDF."""
    try:
        doc = fitz.open(pdf_path)
        doc.close()
        return True
    except Exception:
        return False


def find_pdf_files(input_dir: Path) -> List[Path]:
    """Find all PDF files in a directory."""
    pdf_files = []
    
    if not input_dir.exists() or not input_dir.is_dir():
        return pdf_files
    
    for file_path in input_dir.rglob("*.pdf"):
        if is_valid_pdf(file_path):
            pdf_files.append(file_path)
    
    # Also check for .PDF extension
    for file_path in input_dir.rglob("*.PDF"):
        if is_valid_pdf(file_path):
            pdf_files.append(file_path)
    
    return sorted(pdf_files)