"""
FastAPI Router for Document Extraction Endpoints
Handles file uploads and extraction job management
"""
import os
import uuid
import time
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Path as PathParam
from fastapi.responses import HTMLResponse, JSONResponse
from loguru import logger

from .models import (
    UploadResponse,
    ExtractionResult,
    ExtractionStatus,
    FileType
)
from .pdf_extractor import extract_pdf_complete
from .docx_extractor import extract_docx_complete
from .diagram_describer import describe_diagrams_batch
from .merger import merge_complete_extraction, ExtractionMerger
from config import settings, get_session_output_dir

# Create router
router = APIRouter(prefix="/api/v1", tags=["extraction"])

# In-memory storage for extraction results (replace with Redis in production)
extraction_cache: dict = {}


@router.post("/{user_id}/{session_id}/upload_idf_pdf")
async def upload_idf_pdf(
    user_id: str = PathParam(..., description="User identifier"),
    session_id: str = PathParam(..., description="Session identifier"),
    file: UploadFile = File(..., description="PDF file to extract")
) -> UploadResponse:
    """
    Upload and extract content from PDF file (IDF - Invention Disclosure Form)

    This endpoint:
    1. Accepts a PDF file upload
    2. Extracts text using LlamaParse (agentic mode)
    3. Extracts images using PyMuPDF
    4. Describes diagrams using Gemini Vision
    5. Returns complete extraction result
    """
    logger.info(f"PDF upload received: {file.filename} for user {user_id}, session {session_id}")

    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    try:
        # Create output directory for this session
        output_dir = get_session_output_dir(user_id, session_id)

        # Save uploaded file
        upload_path = output_dir / file.filename
        file_content = await file.read()
        file_size = len(file_content)

        with open(upload_path, "wb") as f:
            f.write(file_content)

        logger.info(f"File saved to {upload_path} ({file_size} bytes)")

        # Start extraction process
        start_time = time.time()

        # Stage 1: Extract PDF (LlamaParse + PyMuPDF in parallel)
        extraction_data = await extract_pdf_complete(
            str(upload_path),
            user_id,
            session_id
        )

        # Get total pages from PyMuPDF
        import fitz
        doc = fitz.open(str(upload_path))
        total_pages = len(doc)
        doc.close()

        # Stage 2: Describe diagrams with Gemini Vision
        images = extraction_data.get("images", [])

        if images:
            logger.info(f"Describing {len(images)} diagrams with Gemini Vision")
            gemini_start = time.time()
            diagram_descriptions = await describe_diagrams_batch(images)
            gemini_time = time.time() - gemini_start
            extraction_data["gemini_time"] = gemini_time
        else:
            logger.info("No images found, skipping diagram description")
            diagram_descriptions = []

        # Stage 3: Merge all data into final result
        result = merge_complete_extraction(
            user_id=user_id,
            session_id=session_id,
            file_name=file.filename,
            file_type=FileType.PDF,
            file_size=file_size,
            extraction_data=extraction_data,
            diagram_descriptions=diagram_descriptions,
            total_pages=total_pages
        )

        # Save result to JSON for caching
        result_path = output_dir / "extraction_result.json"
        ExtractionMerger.save_result_to_json(result, result_path)

        # Cache result in memory
        cache_key = f"{user_id}_{session_id}"
        extraction_cache[cache_key] = result

        total_time = time.time() - start_time

        logger.success(f"PDF extraction completed in {total_time:.2f}s")

        return UploadResponse(
            success=True,
            message=f"PDF extraction completed successfully in {total_time:.2f} seconds",
            session_id=session_id,
            user_id=user_id,
            file_name=file.filename,
            file_type=FileType.PDF,
            estimated_time_seconds=int(total_time)
        )

    except Exception as e:
        logger.error(f"PDF extraction failed: {e}")
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")


@router.post("/{user_id}/{session_id}/upload_idf_transcription")
async def upload_idf_transcription(
    user_id: str = PathParam(..., description="User identifier"),
    session_id: str = PathParam(..., description="Session identifier"),
    file: UploadFile = File(..., description="DOCX file to extract")
) -> UploadResponse:
    """
    Upload and extract content from DOCX file (IDF Transcription)

    This endpoint:
    1. Accepts a DOCX file upload
    2. Extracts text, images, and tables using python-docx
    3. Describes diagrams using Gemini Vision
    4. Returns complete extraction result
    """
    logger.info(f"DOCX upload received: {file.filename} for user {user_id}, session {session_id}")

    # Validate file type
    if not file.filename.lower().endswith(('.docx', '.doc')):
        raise HTTPException(status_code=400, detail="Only DOCX files are accepted")

    try:
        # Create output directory for this session
        output_dir = get_session_output_dir(user_id, session_id)

        # Save uploaded file
        upload_path = output_dir / file.filename
        file_content = await file.read()
        file_size = len(file_content)

        with open(upload_path, "wb") as f:
            f.write(file_content)

        logger.info(f"File saved to {upload_path} ({file_size} bytes)")

        # Start extraction process
        start_time = time.time()

        # Stage 1: Extract DOCX
        extraction_data = await extract_docx_complete(
            str(upload_path),
            user_id,
            session_id
        )

        # Stage 2: Describe diagrams with Gemini Vision
        images = extraction_data.get("images", [])

        if images:
            logger.info(f"Describing {len(images)} diagrams with Gemini Vision")
            gemini_start = time.time()
            diagram_descriptions = await describe_diagrams_batch(images)
            gemini_time = time.time() - gemini_start
            extraction_data["gemini_time"] = gemini_time
        else:
            logger.info("No images found, skipping diagram description")
            diagram_descriptions = []

        # Stage 3: Merge all data into final result
        result = merge_complete_extraction(
            user_id=user_id,
            session_id=session_id,
            file_name=file.filename,
            file_type=FileType.DOCX,
            file_size=file_size,
            extraction_data=extraction_data,
            diagram_descriptions=diagram_descriptions,
            total_pages=0  # DOCX doesn't have traditional pages
        )

        # Save result to JSON for caching
        result_path = output_dir / "extraction_result.json"
        ExtractionMerger.save_result_to_json(result, result_path)

        # Cache result in memory
        cache_key = f"{user_id}_{session_id}"
        extraction_cache[cache_key] = result

        total_time = time.time() - start_time

        logger.success(f"DOCX extraction completed in {total_time:.2f}s")

        return UploadResponse(
            success=True,
            message=f"DOCX extraction completed successfully in {total_time:.2f} seconds",
            session_id=session_id,
            user_id=user_id,
            file_name=file.filename,
            file_type=FileType.DOCX,
            estimated_time_seconds=int(total_time)
        )

    except Exception as e:
        logger.error(f"DOCX extraction failed: {e}")
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")


@router.get("/{user_id}/{session_id}/extraction_result")
async def get_extraction_result(
    user_id: str = PathParam(..., description="User identifier"),
    session_id: str = PathParam(..., description="Session identifier")
) -> ExtractionResult:
    """
    Get extraction result for a specific session

    Returns the cached extraction result if available
    """
    cache_key = f"{user_id}_{session_id}"

    # Check in-memory cache first
    if cache_key in extraction_cache:
        logger.info(f"Returning cached result for {cache_key}")
        return extraction_cache[cache_key]

    # Try to load from JSON file
    output_dir = get_session_output_dir(user_id, session_id)
    result_path = output_dir / "extraction_result.json"

    if result_path.exists():
        logger.info(f"Loading result from {result_path}")
        result = ExtractionMerger.load_result_from_json(result_path)
        # Cache for future requests
        extraction_cache[cache_key] = result
        return result

    # No result found
    raise HTTPException(
        status_code=404,
        detail=f"No extraction result found for user {user_id}, session {session_id}"
    )


@router.get("/{user_id}/{session_id}/view")
async def view_extraction(
    user_id: str = PathParam(..., description="User identifier"),
    session_id: str = PathParam(..., description="Session identifier")
) -> HTMLResponse:
    """
    View extraction result in HTML viewer

    Returns an HTML page with all extracted data rendered visually
    """
    try:
        # Get extraction result
        cache_key = f"{user_id}_{session_id}"

        if cache_key in extraction_cache:
            result = extraction_cache[cache_key]
        else:
            output_dir = get_session_output_dir(user_id, session_id)
            result_path = output_dir / "extraction_result.json"

            if not result_path.exists():
                raise HTTPException(
                    status_code=404,
                    detail=f"No extraction result found for user {user_id}, session {session_id}"
                )

            result = ExtractionMerger.load_result_from_json(result_path)

        # Load HTML viewer template
        viewer_path = settings.static_dir / "viewer.html"

        if not viewer_path.exists():
            raise HTTPException(status_code=500, detail="Viewer template not found")

        with open(viewer_path, "r", encoding="utf-8") as f:
            html_template = f.read()

        # Inject result data as JSON into HTML
        import json
        result_json = result.model_dump_json(indent=2)

        # Replace placeholder in HTML with actual data
        html_content = html_template.replace(
            "{{EXTRACTION_RESULT_JSON}}",
            result_json
        )

        return HTMLResponse(content=html_content)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to render viewer: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to render viewer: {str(e)}")


@router.get("/{user_id}/{session_id}/status")
async def get_extraction_status(
    user_id: str = PathParam(..., description="User identifier"),
    session_id: str = PathParam(..., description="Session identifier")
) -> ExtractionStatus:
    """
    Get status of an extraction job

    Useful for polling during async extraction
    """
    cache_key = f"{user_id}_{session_id}"

    # Check if result exists
    if cache_key in extraction_cache:
        result = extraction_cache[cache_key]
        return ExtractionStatus(
            session_id=session_id,
            user_id=user_id,
            status="completed",
            progress_percentage=100.0,
            current_stage="completed",
            result=result
        )

    # Check if extraction is in progress (would be tracked via Celery in production)
    output_dir = get_session_output_dir(user_id, session_id)

    if output_dir.exists() and any(output_dir.iterdir()):
        return ExtractionStatus(
            session_id=session_id,
            user_id=user_id,
            status="processing",
            progress_percentage=50.0,
            current_stage="extracting"
        )

    # No extraction found
    return ExtractionStatus(
        session_id=session_id,
        user_id=user_id,
        status="pending",
        progress_percentage=0.0
    )
