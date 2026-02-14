"""
Cloudinary Service
Handles all file uploads to Cloudinary cloud storage
NO LOCAL DISK STORAGE - Everything stored in Cloudinary cloud
"""
import cloudinary
import cloudinary.uploader
import cloudinary.api
from cloudinary.utils import cloudinary_url
from config import settings
from loguru import logger
from pathlib import Path
from typing import Dict, Optional
import requests
from io import BytesIO
import asyncio
from functools import partial


# Configure Cloudinary on module import
cloudinary.config(
    cloud_name=settings.cloudinary_cloud_name,
    api_key=settings.cloudinary_api_key,
    api_secret=settings.cloudinary_api_secret,
    secure=True
)

logger.success(f"✅ Cloudinary configured: {settings.cloudinary_cloud_name}")


async def upload_document(
    file_bytes: bytes,
    filename: str,
    user_id: str,
    session_id: str,
    document_type: str
) -> Dict[str, any]:
    """
    Upload document (PDF/DOCX) to Cloudinary cloud storage

    Args:
        file_bytes: File content as bytes
        filename: Original filename
        user_id: User ID for folder organization
        session_id: Session ID for folder organization
        document_type: Type of document (idf, transcription, claims)

    Returns:
        {
            "url": "https://res.cloudinary.com/dvmipqnww/raw/upload/v123.../file.pdf",
            "secure_url": "https://res.cloudinary.com/dvmipqnww/raw/upload/v123.../file.pdf",
            "public_id": "patmaster/user_123/sess_456/idf",
            "format": "pdf",
            "bytes": 1234567,
            "resource_type": "raw"
        }
    """
    try:
        # Cloudinary folder structure: patmaster/{user_id}/{session_id}/
        folder = f"patmaster/{user_id}/{session_id}"

        # Upload to Cloudinary (run in thread to avoid blocking async event loop)
        # resource_type="auto" detects: image (PNG/JPG) vs raw (PDF/DOCX)
        result = await asyncio.to_thread(
            cloudinary.uploader.upload,
            file_bytes,
            folder=folder,
            public_id=document_type,
            resource_type="auto",  # Auto-detect file type
            overwrite=True,  # Replace if exists
            invalidate=True  # Clear CDN cache
        )

        logger.success(f"📤 Uploaded {filename} to Cloudinary: {result['secure_url']}")
        logger.info(f"   Size: {result.get('bytes', 0) / 1024:.2f} KB")
        logger.info(f"   Type: {result.get('resource_type')}")

        return {
            "url": result["secure_url"],
            "secure_url": result["secure_url"],
            "public_id": result["public_id"],
            "format": result.get("format"),
            "bytes": result.get("bytes"),
            "resource_type": result.get("resource_type")
        }

    except Exception as e:
        logger.error(f"❌ Cloudinary upload failed for {filename}: {e}")
        raise


async def upload_extracted_image(
    image_bytes: bytes,
    user_id: str,
    session_id: str,
    image_id: str,
    image_format: str = "png"
) -> str:
    """
    Upload extracted image (PNG/JPG) to Cloudinary

    Args:
        image_bytes: Image content as bytes
        user_id: User ID for folder organization
        session_id: Session ID for folder organization
        image_id: Image identifier (e.g., "page3_img1")
        image_format: Image format (png, jpg)

    Returns:
        Cloudinary secure URL
    """
    try:
        folder = f"patmaster/{user_id}/{session_id}/images"

        result = await asyncio.to_thread(
            cloudinary.uploader.upload,
            image_bytes,
            folder=folder,
            public_id=image_id,
            resource_type="image",
            format=image_format,
            overwrite=True,
            invalidate=True
        )

        logger.info(f"📸 Uploaded image {image_id} to Cloudinary")

        return result["secure_url"]

    except Exception as e:
        logger.error(f"❌ Image upload failed for {image_id}: {e}")
        raise


async def upload_image_from_path(
    image_path: Path,
    user_id: str,
    session_id: str,
    image_id: str
) -> str:
    """
    Upload image from local file path to Cloudinary, then delete local file

    Args:
        image_path: Path to local image file
        user_id: User ID
        session_id: Session ID
        image_id: Image identifier

    Returns:
        Cloudinary secure URL
    """
    try:
        folder = f"patmaster/{user_id}/{session_id}/images"

        # Upload from file path (run in thread to avoid blocking async event loop)
        with open(image_path, "rb") as f:
            file_data = f.read()
        result = await asyncio.to_thread(
            cloudinary.uploader.upload,
            file_data,
            folder=folder,
            public_id=image_id,
            resource_type="image",
            overwrite=True,
            invalidate=True
        )

        # Delete local file after successful upload
        try:
            image_path.unlink()
            logger.debug(f"🗑️  Deleted local file: {image_path}")
        except Exception as e:
            logger.warning(f"Failed to delete local file {image_path}: {e}")

        logger.info(f"📸 Uploaded image {image_id} from path to Cloudinary")

        return result["secure_url"]

    except Exception as e:
        logger.error(f"❌ Image upload from path failed for {image_id}: {e}")
        raise


async def download_file(cloudinary_url: str) -> bytes:
    """
    Download file from Cloudinary URL

    Args:
        cloudinary_url: Cloudinary secure URL

    Returns:
        File content as bytes
    """
    try:
        response = await asyncio.to_thread(
            partial(requests.get, cloudinary_url, timeout=30)
        )
        response.raise_for_status()

        logger.debug(f"📥 Downloaded file from Cloudinary ({len(response.content) / 1024:.2f} KB)")

        return response.content

    except Exception as e:
        logger.error(f"❌ Failed to download from Cloudinary: {e}")
        raise


async def delete_project_files(user_id: str, session_id: str):
    """
    Delete all files for a project from Cloudinary

    Args:
        user_id: User ID
        session_id: Session ID
    """
    try:
        folder = f"patmaster/{user_id}/{session_id}"

        # Delete all resources in folder (run in thread)
        await asyncio.to_thread(cloudinary.api.delete_resources_by_prefix, folder)

        # Delete the folder itself
        try:
            await asyncio.to_thread(cloudinary.api.delete_folder, folder)
        except Exception as e:
            logger.debug(f"Folder deletion warning: {e}")

        logger.success(f"🗑️  Deleted Cloudinary folder: {folder}")

    except Exception as e:
        logger.warning(f"⚠️  Cloudinary deletion failed for {folder}: {e}")
        # Don't raise - deletion is not critical


async def get_file_url(public_id: str, resource_type: str = "auto") -> str:
    """
    Generate Cloudinary URL from public_id

    Args:
        public_id: Cloudinary public ID
        resource_type: Type (image, raw, auto)

    Returns:
        Secure URL
    """
    url, options = cloudinary_url(
        public_id,
        resource_type=resource_type,
        secure=True
    )
    return url


# Export key functions
__all__ = [
    'upload_document',
    'upload_extracted_image',
    'upload_image_from_path',
    'download_file',
    'delete_project_files',
    'get_file_url'
]
