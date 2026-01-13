"""
Image Processing Utilities for OMR.

Provides functions for preprocessing sheet music images
to improve OMR accuracy.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Union, Tuple
import logging

logger = logging.getLogger(__name__)


def preprocess_for_omr(
    input_path: Union[str, Path],
    output_path: Union[str, Path],
    deskew: bool = True,
    enhance: bool = True,
    target_dpi: int = 300,
) -> Path:
    """
    Preprocess an image for optimal OMR results.
    
    Args:
        input_path: Path to input image
        output_path: Path for output image
        deskew: Whether to apply deskewing
        enhance: Whether to enhance contrast
        target_dpi: Target DPI for output
        
    Returns:
        Path to preprocessed image
    """
    input_path = Path(input_path)
    output_path = Path(output_path)
    
    try:
        import cv2
        import numpy as np
        from PIL import Image
    except ImportError:
        logger.warning("OpenCV or Pillow not available, copying image as-is")
        import shutil
        shutil.copy(input_path, output_path)
        return output_path
    
    # Load image
    img = cv2.imread(str(input_path))
    
    if img is None:
        raise ValueError(f"Could not load image: {input_path}")
    
    # Convert to grayscale
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img
    
    # Deskew if requested
    if deskew:
        gray = deskew_image(gray)
    
    # Enhance contrast if requested
    if enhance:
        gray = enhance_contrast(gray)
    
    # Apply light denoising
    gray = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
    
    # Binarize with adaptive threshold for clean lines
    # binary = cv2.adaptiveThreshold(
    #     gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    # )
    
    # Save output
    cv2.imwrite(str(output_path), gray)
    
    logger.info(f"Preprocessed image saved to: {output_path}")
    return output_path


def deskew_image(image) -> "np.ndarray":
    """
    Deskew a grayscale image.
    
    Uses Hough transform to detect dominant angle and rotate.
    
    Args:
        image: Grayscale numpy array
        
    Returns:
        Deskewed image
    """
    import cv2
    import numpy as np
    
    # Detect edges
    edges = cv2.Canny(image, 50, 150, apertureSize=3)
    
    # Detect lines using Hough transform
    lines = cv2.HoughLines(edges, 1, np.pi / 180, 200)
    
    if lines is None:
        return image
    
    # Calculate angles
    angles = []
    for line in lines:
        rho, theta = line[0]
        # Convert to degrees and adjust
        angle = np.degrees(theta) - 90
        # Focus on small angles (likely staff lines)
        if -10 < angle < 10:
            angles.append(angle)
    
    if not angles:
        return image
    
    # Use median angle
    median_angle = np.median(angles)
    
    if abs(median_angle) < 0.1:
        return image
    
    # Rotate image
    height, width = image.shape[:2]
    center = (width // 2, height // 2)
    
    rotation_matrix = cv2.getRotationMatrix2D(center, median_angle, 1.0)
    
    # Calculate new image size
    cos = np.abs(rotation_matrix[0, 0])
    sin = np.abs(rotation_matrix[0, 1])
    new_width = int((height * sin) + (width * cos))
    new_height = int((height * cos) + (width * sin))
    
    # Adjust rotation matrix
    rotation_matrix[0, 2] += (new_width / 2) - center[0]
    rotation_matrix[1, 2] += (new_height / 2) - center[1]
    
    rotated = cv2.warpAffine(
        image,
        rotation_matrix,
        (new_width, new_height),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=255
    )
    
    logger.info(f"Deskewed image by {median_angle:.2f} degrees")
    return rotated


def enhance_contrast(image) -> "np.ndarray":
    """
    Enhance contrast of a grayscale image.
    
    Uses CLAHE (Contrast Limited Adaptive Histogram Equalization).
    
    Args:
        image: Grayscale numpy array
        
    Returns:
        Contrast-enhanced image
    """
    import cv2
    
    # Apply CLAHE
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(image)
    
    return enhanced


def extract_pdf_pages(
    pdf_path: Union[str, Path],
    output_dir: Union[str, Path],
    pages: Optional[List[int]] = None,
    dpi: int = 300,
) -> List[Path]:
    """
    Extract pages from a PDF as images.
    
    Args:
        pdf_path: Path to PDF file
        output_dir: Directory for output images
        pages: List of page numbers to extract (0-indexed).
               If None, extracts all pages.
        dpi: Resolution for output images
        
    Returns:
        List of paths to extracted images
    """
    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    extracted = []
    
    try:
        import fitz  # PyMuPDF
        
        doc = fitz.open(str(pdf_path))
        
        page_indices = pages if pages else range(len(doc))
        
        for i, page_num in enumerate(page_indices):
            if page_num >= len(doc):
                continue
            
            page = doc[page_num]
            
            # Calculate zoom factor for desired DPI
            zoom = dpi / 72  # PDF default is 72 DPI
            matrix = fitz.Matrix(zoom, zoom)
            
            # Render page to image
            pix = page.get_pixmap(matrix=matrix)
            
            # Save image
            output_path = output_dir / f"page_{page_num + 1:04d}.png"
            pix.save(str(output_path))
            
            extracted.append(output_path)
            logger.info(f"Extracted page {page_num + 1}")
        
        doc.close()
        
    except ImportError:
        logger.warning("PyMuPDF not installed, trying pdf2image")
        
        try:
            from pdf2image import convert_from_path
            
            images = convert_from_path(str(pdf_path), dpi=dpi)
            
            for i, image in enumerate(images):
                if pages and i not in pages:
                    continue
                
                output_path = output_dir / f"page_{i + 1:04d}.png"
                image.save(str(output_path), "PNG")
                extracted.append(output_path)
                logger.info(f"Extracted page {i + 1}")
                
        except ImportError:
            raise RuntimeError(
                "PDF extraction requires PyMuPDF or pdf2image. "
                "Install with: pip install PyMuPDF"
            )
    
    return extracted


def create_placeholder_musicxml(output_path: Union[str, Path]) -> None:
    """
    Create a simple placeholder MusicXML file for testing.
    
    Args:
        output_path: Path for output file
    """
    output_path = Path(output_path)
    
    musicxml = '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 4.0 Partwise//EN" "http://www.musicxml.org/dtds/partwise.dtd">
<score-partwise version="4.0">
  <work>
    <work-title>Placeholder Score</work-title>
  </work>
  <identification>
    <creator type="composer">Sheet Music Scanner</creator>
  </identification>
  <part-list>
    <score-part id="P1">
      <part-name>Piano</part-name>
    </score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>1</divisions>
        <key>
          <fifths>0</fifths>
        </key>
        <time>
          <beats>4</beats>
          <beat-type>4</beat-type>
        </time>
        <clef>
          <sign>G</sign>
          <line>2</line>
        </clef>
      </attributes>
      <note>
        <pitch>
          <step>C</step>
          <octave>4</octave>
        </pitch>
        <duration>1</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch>
          <step>D</step>
          <octave>4</octave>
        </pitch>
        <duration>1</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch>
          <step>E</step>
          <octave>4</octave>
        </pitch>
        <duration>1</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch>
          <step>F</step>
          <octave>4</octave>
        </pitch>
        <duration>1</duration>
        <type>quarter</type>
      </note>
    </measure>
    <measure number="2">
      <note>
        <pitch>
          <step>G</step>
          <octave>4</octave>
        </pitch>
        <duration>1</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch>
          <step>A</step>
          <octave>4</octave>
        </pitch>
        <duration>1</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch>
          <step>B</step>
          <octave>4</octave>
        </pitch>
        <duration>1</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch>
          <step>C</step>
          <octave>5</octave>
        </pitch>
        <duration>1</duration>
        <type>quarter</type>
      </note>
    </measure>
  </part>
</score-partwise>
'''
    
    output_path.write_text(musicxml)
    logger.info(f"Created placeholder MusicXML: {output_path}")


def get_image_info(image_path: Union[str, Path]) -> dict:
    """
    Get information about an image file.
    
    Args:
        image_path: Path to image
        
    Returns:
        Dictionary with image info (width, height, format, etc.)
    """
    image_path = Path(image_path)
    
    try:
        from PIL import Image
        
        with Image.open(image_path) as img:
            return {
                "path": str(image_path),
                "width": img.width,
                "height": img.height,
                "format": img.format,
                "mode": img.mode,
                "dpi": img.info.get("dpi", (72, 72)),
            }
    except ImportError:
        import cv2
        
        img = cv2.imread(str(image_path))
        if img is not None:
            height, width = img.shape[:2]
            return {
                "path": str(image_path),
                "width": width,
                "height": height,
                "format": image_path.suffix.upper(),
                "mode": "BGR" if len(img.shape) == 3 else "GRAY",
            }
    
    return {"path": str(image_path), "error": "Could not read image"}
