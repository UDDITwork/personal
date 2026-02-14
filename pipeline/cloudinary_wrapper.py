"""
Cloudinary Wrapper for Extraction Pipeline
Downloads files from Cloudinary for processing, uploads results back to Cloudinary
DOES NOT MODIFY extraction logic - just handles file I/O
"""
import tempfile
import requests
from pathlib import Path
from loguru import logger
from typing import Dict, Any
import shutil


async def download_from_cloudinary_to_temp(cloudinary_url: str, filename: str) -> Path:
    """
    Download file from Cloudinary to temporary location for processing

    Args:
        cloudinary_url: Cloudinary URL
        filename: Original filename (with extension)

    Returns:
        Path to temporary file
    """
    try:
        logger.info(f"📥 Downloading from Cloudinary: {cloudinary_url}")

        # Download file
        response = requests.get(cloudinary_url, timeout=60)
        response.raise_for_status()

        # Create temporary file with correct extension
        suffix = Path(filename).suffix
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        temp_path = Path(temp_file.name)

        # Write content
        temp_file.write(response.content)
        temp_file.close()

        logger.success(f"✅ Downloaded to temp: {temp_path} ({len(response.content) / 1024:.2f} KB)")

        return temp_path

    except Exception as e:
        logger.error(f"❌ Download from Cloudinary failed: {e}")
        raise


async def upload_extracted_images_to_cloudinary(
    images_list: list,
    user_id: str,
    session_id: str
) -> list:
    """
    Upload extracted images from local paths to Cloudinary, update paths in-place

    Args:
        images_list: List of ExtractedImage objects with local image_path
        user_id: User ID
        session_id: Session ID

    Returns:
        Updated images_list with Cloudinary URLs instead of local paths
    """
    try:
        from services.cloudinary_service import upload_image_from_path

        logger.info(f"📤 Uploading {len(images_list)} extracted images to Cloudinary")

        for img in images_list:
            if hasattr(img, 'image_path') and img.image_path:
                local_path = Path(img.image_path)

                if local_path.exists():
                    # Upload to Cloudinary
                    cloudinary_url = await upload_image_from_path(
                        local_path,
                        user_id,
                        session_id,
                        img.image_id if hasattr(img, 'image_id') else local_path.stem
                    )

                    # Update image path to Cloudinary URL
                    img.image_path = cloudinary_url
                    logger.debug(f"  ✅ {img.image_id}: {cloudinary_url}")

        logger.success(f"✅ All {len(images_list)} images uploaded to Cloudinary")

        return images_list

    except Exception as e:
        logger.error(f"❌ Image upload to Cloudinary failed: {e}")
        raise


def cleanup_temp_file(temp_path: Path):
    """
    Delete temporary file after processing

    Args:
        temp_path: Path to temporary file
    """
    try:
        if temp_path.exists():
            temp_path.unlink()
            logger.debug(f"🗑️  Deleted temp file: {temp_path}")
    except Exception as e:
        logger.warning(f"Failed to delete temp file {temp_path}: {e}")


def cleanup_temp_directory(temp_dir: Path):
    """
    Delete temporary directory and all contents

    Args:
        temp_dir: Path to temporary directory
    """
    try:
        if temp_dir.exists() and temp_dir.is_dir():
            shutil.rmtree(temp_dir)
            logger.debug(f"🗑️  Deleted temp directory: {temp_dir}")
    except Exception as e:
        logger.warning(f"Failed to delete temp directory {temp_dir}: {e}")
