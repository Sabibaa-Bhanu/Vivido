"""
Download Manager Module for Vivido Image Processing

This module handles:
- Saving processed images with unique filenames
- Multiple download format options (PNG, JPG, PDF)
- Image quality settings (high quality / optimized)
- Watermark feature for free preview downloads
- Download metadata storage
- File cleanup functionality
"""

import os
import time
import datetime
import shutil
import logging
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
import base64

import numpy as np
from PIL import Image, ImageDraw, ImageFont
import streamlit as st

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "downloads")
TEMP_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "temp")
WATERMARK_TEXT = "Vivido Preview"
WATERMARK_FONT_SIZE = 24
WATERMARK_OPACITY = 0.3
FILE_CLEANUP_HOURS = 24

# Ensure directories exist
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)


def generate_unique_filename(user_id: int, original_filename: str, file_format: str) -> str:
    """
    Generate a unique filename for the processed image.
    
    Args:
        user_id: The user's ID
        original_filename: Original filename of the uploaded image
        file_format: The output format (png, jpg, pdf)
    
    Returns:
        Unique filename string
    """
    # Get current timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Sanitize original filename (remove extension and special characters)
    base_name = os.path.splitext(original_filename)[0]
    sanitized_name = "".join(c for c in base_name if c.isalnum() or c in (' ', '-', '_')).strip()
    sanitized_name = sanitized_name.replace(' ', '_')[:30]  # Limit length
    
    # Create unique filename: userid_timestamp_originalname.ext
    unique_filename = f"{user_id}_{timestamp}_{sanitized_name}.{file_format}"
    
    return unique_filename


def get_output_path(user_id: int, filename: str) -> str:
    """
    Get the full output path for a file.
    
    Args:
        user_id: The user's ID
        filename: The filename
    
    Returns:
        Full path to the output file
    """
    # Create user-specific subdirectory
    user_dir = os.path.join(OUTPUT_DIR, str(user_id))
    os.makedirs(user_dir, exist_ok=True)
    
    return os.path.join(user_dir, filename)


def add_watermark(image: Image.Image, watermark_text: str = WATERMARK_TEXT, 
                  position: str = "bottom-right", opacity: float = WATERMARK_OPACITY) -> Image.Image:
    """
    Add a watermark to the image.
    
    Args:
        image: PIL Image object
        watermark_text: Text to use as watermark
        position: Position of watermark (bottom-right, bottom-left, top-right, top-left, center)
        opacity: Opacity of watermark (0-1)
    
    Returns:
        Image with watermark applied
    """
    # Create a copy to avoid modifying original
    watermarked = image.copy()
    
    # Convert to RGBA if needed
    if watermarked.mode != 'RGBA':
        watermarked = watermarked.convert('RGBA')
    
    # Create overlay with transparency
    overlay = Image.new('RGBA', watermarked.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)
    
    # Get image dimensions
    width, height = watermarked.size
    
    # Calculate font size based on image size
    font_size = max(int(min(width, height) * 0.03), 12)
    
    try:
        # Try to use a default font
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        # Fallback to default font
        font = ImageFont.load_default()
    
    # Get text bounding box
    bbox = draw.textbbox((0, 0), watermark_text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # Calculate padding
    padding = int(min(width, height) * 0.02)
    
    # Determine position
    position_map = {
        "bottom-right": (width - text_width - padding, height - text_height - padding),
        "bottom-left": (padding, height - text_height - padding),
        "top-right": (width - text_width - padding, padding),
        "top-left": (padding, padding),
        "center": ((width - text_width) // 2, (height - text_height) // 2)
    }
    
    x, y = position_map.get(position, position_map["bottom-right"])
    
    # Draw watermark with transparency
    alpha = int(255 * opacity)
    draw.text((x, y), watermark_text, fill=(255, 255, 255, alpha), font=font)
    
    # Composite the overlay
    watermarked = Image.alpha_composite(watermarked, overlay)
    
    # Convert back to RGB
    watermarked = watermarked.convert('RGB')
    
    return watermarked


def save_image_for_download(image: Image.Image, user_id: int, original_filename: str,
                            file_format: str = "png", quality: str = "high",
                            add_watermark: bool = False) -> Tuple[bool, str, Optional[str]]:
    """
    Save the processed image for download.
    
    Args:
        image: PIL Image object
        user_id: The user's ID
        original_filename: Original filename of the uploaded image
        file_format: Output format (png, jpg, pdf)
        quality: Quality setting (high, optimized)
        add_watermark: Whether to add watermark
    
    Returns:
        Tuple of (success, file_path, error_message)
    """
    try:
        # Generate unique filename
        filename = generate_unique_filename(user_id, original_filename, file_format)
        output_path = get_output_path(user_id, filename)
        
        # Add watermark if requested
        if add_watermark:
            image = add_watermark(image)
        
        # Save with appropriate quality settings
        if file_format.lower() == "png":
            # PNG is lossless, quality doesn't apply in same way
            image.save(output_path, "PNG", optimize=(quality == "optimized"))
        
        elif file_format.lower() in ["jpg", "jpeg"]:
            # JPG quality: high = 95, optimized = 85
            jpeg_quality = 95 if quality == "high" else 85
            # Convert RGBA to RGB for JPG
            if image.mode in ('RGBA', 'LA'):
                # Create white background
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'RGBA':
                    background.paste(image, mask=image.split()[3])  # Use alpha as mask
                else:
                    background.paste(image, mask=image.split()[1])  # Use alpha as mask
                image = background
            image.save(output_path, "JPEG", quality=jpeg_quality, optimize=(quality == "optimized"))
        
        elif file_format.lower() == "pdf":
            # Save as PDF (single page)
            image.save(output_path, "PDF", resolution=100.0)
        
        else:
            return False, "", f"Unsupported format: {file_format}"
        
        logger.info(f"Image saved successfully: {output_path}")
        return True, output_path, None
    
    except Exception as e:
        logger.error(f"Error saving image: {str(e)}")
        return False, "", str(e)


def prepare_download(image: np.ndarray, user_id: int, original_filename: str,
                     style_name: str, file_format: str = "png", 
                     quality: str = "high", add_watermark: bool = False,
                     store_metadata: bool = True) -> Dict[str, Any]:
    """
    Prepare an image for download with all options.
    
    Args:
        image: numpy array (RGB) of the processed image
        user_id: The user's ID
        original_filename: Original filename of the uploaded image
        style_name: The applied style name
        file_format: Output format (png, jpg, pdf)
        quality: Quality setting (high, optimized)
        add_watermark: Whether to add watermark (for free previews)
        store_metadata: Whether to store metadata in database
    
    Returns:
        Dictionary with download information
    """
    # Convert numpy array to PIL Image
    if isinstance(image, np.ndarray):
        # Handle different array formats
        if image.dtype != np.uint8:
            image = (image * 255).astype(np.uint8)
        pil_image = Image.fromarray(image)
    else:
        pil_image = image
    
    # Save the image
    success, file_path, error = save_image_for_download(
        pil_image, user_id, original_filename, file_format, quality, add_watermark
    )
    
    if not success:
        return {
            "success": False,
            "error": error,
            "file_path": None,
            "download_filename": None
        }
    
    # Get filename from path
    download_filename = os.path.basename(file_path)
    
    # Store metadata in database if requested
    if store_metadata and success:
        try:
            from backend.database import get_connection
            conn = get_connection()
            cursor = conn.cursor()
            
            # Find the image record (most recent for this user with the style)
            cursor.execute("""
                SELECT image_id FROM image_history 
                WHERE user_id = ? AND style_applied = ?
                ORDER BY processing_date DESC LIMIT 1
            """, (user_id, style_name))
            
            result = cursor.fetchone()
            
            if result:
                image_id = result[0]
                download_timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # Update the record with download info
                cursor.execute("""
                    UPDATE image_history 
                    SET download_path = ?, download_format = ?, download_quality = ?,
                        has_watermark = ?, download_timestamp = ?
                    WHERE image_id = ?
                """, (file_path, file_format, quality, 1 if add_watermark else 0, 
                      download_timestamp, image_id))
                
                conn.commit()
            
            conn.close()
        
        except Exception as e:
            logger.warning(f"Failed to store download metadata: {str(e)}")
    
    # Store in session state
    if "download_info" not in st.session_state:
        st.session_state["download_info"] = {}
    
    st.session_state["download_info"][download_filename] = {
        "file_path": file_path,
        "format": file_format,
        "quality": quality,
        "has_watermark": add_watermark,
        "timestamp": datetime.datetime.now().isoformat()
    }
    
    return {
        "success": True,
        "error": None,
        "file_path": file_path,
        "download_filename": download_filename,
        "format": file_format,
        "quality": quality,
        "has_watermark": add_watermark
    }


def cleanup_old_files(directory: str, hours: int = FILE_CLEANUP_HOURS) -> int:
    """
    Clean up old files from a directory.
    
    Args:
        directory: Path to the directory to clean
        hours: Delete files older than this many hours
    
    Returns:
        Number of files deleted
    """
    if not os.path.exists(directory):
        return 0
    
    current_time = time.time()
    cutoff_time = current_time - (hours * 3600)
    deleted_count = 0
    
    try:
        for root, dirs, files in os.walk(directory):
            for filename in files:
                filepath = os.path.join(root, filename)
                try:
                    # Check file modification time
                    if os.path.getmtime(filepath) < cutoff_time:
                        os.remove(filepath)
                        deleted_count += 1
                        logger.info(f"Deleted old file: {filepath}")
                except Exception as e:
                    logger.warning(f"Failed to delete {filepath}: {str(e)}")
    
    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}")
    
    return deleted_count


def run_periodic_cleanup() -> None:
    """
    Run cleanup on temporary and output directories.
    Call this periodically (e.g., on app startup or via scheduler).
    """
    # Clean temp directory
    temp_deleted = cleanup_old_files(TEMP_DIR)
    logger.info(f"Cleaned {temp_deleted} files from temp directory")
    
    # Clean output directory (optional - might want to keep downloads longer)
    # output_deleted = cleanup_old_files(OUTPUT_DIR)
    # logger.info(f"Cleaned {output_deleted} files from output directory")


def get_file_size(file_path: str) -> str:
    """
    Get human-readable file size.
    
    Args:
        file_path: Path to the file
    
    Returns:
        Formatted file size string
    """
    if not os.path.exists(file_path):
        return "0 B"
    
    size = os.path.getsize(file_path)
    
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    
    return f"{size:.2f} TB"


def verify_file_exists(file_path: str) -> bool:
    """
    Verify that a file exists and is readable.
    
    Args:
        file_path: Path to the file
    
    Returns:
        True if file exists and is readable
    """
    return os.path.exists(file_path) and os.path.isfile(file_path) and os.access(file_path, os.R_OK)


def get_download_info(user_id: int) -> list:
    """
    Get download history for a user.
    
    Args:
        user_id: The user's ID
    
    Returns:
        List of download records
    """
    try:
        from backend.database import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT image_id, original_image_path, processed_image_path, style_applied,
                   processing_date, download_path, download_format, download_quality,
                   has_watermark, download_timestamp
            FROM image_history 
            WHERE user_id = ? AND download_path IS NOT NULL
            ORDER BY download_timestamp DESC
        """, (user_id,))
        
        results = cursor.fetchall()
        conn.close()
        
        return results
    
    except Exception as e:
        logger.error(f"Error getting download info: {str(e)}")
        return []


def delete_download_file(file_path: str) -> Tuple[bool, Optional[str]]:
    """
    Delete a download file.
    
    Args:
        file_path: Path to the file to delete
    
    Returns:
        Tuple of (success, error_message)
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Deleted file: {file_path}")
            return True, None
        return False, "File does not exist"
    except Exception as e:
        logger.error(f"Error deleting file: {str(e)}")
        return False, str(e)


# Initialize on import - run cleanup
try:
    run_periodic_cleanup()
except Exception as e:
    logger.warning(f"Initial cleanup failed: {str(e)}")
