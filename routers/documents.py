"""
Documents Router
Handles document uploads for IDF, Transcription, and Claims
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from pathlib import Path
from loguru import logger

from database import get_db, User, Project, Document
from auth.dependencies import get_current_user
from config import get_session_output_dir
from services.cloudinary_service import upload_document

router = APIRouter(
    prefix="/api/v1/projects",
    tags=["Documents"]
)


# Response Models
class DocumentUploadResponse(BaseModel):
    """Document upload response"""
    success: bool
    message: str
    document_id: str
    project_id: str
    document_type: str
    file_name: str
    file_path: str
    processing_status: str


# Helper Functions

async def verify_project_access(
    project_id: str,
    current_user: User,
    db: Session
) -> Project:
    """
    Verify user has access to project

    ROW-LEVEL SECURITY: Checks project ownership
    """
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == current_user.id  # CRITICAL: Security check
    ).first()

    if not project:
        logger.warning(f"Project {project_id} not found or access denied for user {current_user.email}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    return project


async def check_document_exists(
    project_id: str,
    document_type: str,
    db: Session
) -> bool:
    """Check if document type already exists in project"""
    existing = db.query(Document).filter(
        Document.project_id == project_id,
        Document.document_type == document_type
    ).first()

    return existing is not None


async def save_uploaded_file_cloudinary(
    file: UploadFile,
    user_id: str,
    session_id: str,
    document_type: str,
    file_extension: str
) -> dict:
    """
    Upload file to Cloudinary cloud storage (NO LOCAL DISK)

    Returns:
        {
            "url": "https://res.cloudinary.com/...",
            "bytes": 1234567,
            ...
        }
    """
    # Read file content
    file_content = await file.read()

    # Upload to Cloudinary
    cloudinary_result = await upload_document(
        file_bytes=file_content,
        filename=file.filename,
        user_id=user_id,
        session_id=session_id,
        document_type=document_type
    )

    logger.info(f"☁️  Uploaded to Cloudinary: {cloudinary_result['url']} ({len(file_content)} bytes)")

    return cloudinary_result


# Upload Endpoints

@router.post("/{project_id}/upload/idf", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_idf(
    project_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload IDF document (PDF)

    IDF = Information Disclosure Form (Patent document)
    File naming: {user_id}_{session_id}_idf.pdf
    """
    logger.info(f"IDF upload request for project {project_id} by user {current_user.email}")

    # Verify project access (ROW-LEVEL SECURITY)
    project = await verify_project_access(project_id, current_user, db)

    # Check if IDF already exists
    if await check_document_exists(project_id, "idf", db):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="IDF document already uploaded for this project. Delete existing document first."
        )

    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are accepted for IDF documents"
        )

    # Upload to Cloudinary (NO local disk storage)
    cloudinary_result = await save_uploaded_file_cloudinary(
        file,
        current_user.id,
        project.session_id,
        "idf",
        "pdf"
    )

    # Create document record with Cloudinary URL
    document = Document(
        project_id=project_id,
        document_type="idf",
        file_name=file.filename,
        file_type="pdf",
        file_path=cloudinary_result["url"],  # ☁️ Cloudinary URL (not local path)
        file_size_bytes=cloudinary_result.get("bytes", 0),
        processing_status="pending"
    )

    db.add(document)
    db.commit()
    db.refresh(document)

    logger.success(f"IDF document uploaded: {document.id} for project {project_id}")

    # TODO: Trigger extraction pipeline (will be implemented in services/extraction_service.py)
    # await process_extraction(document, db)

    return DocumentUploadResponse(
        success=True,
        message="IDF document uploaded successfully to Cloudinary. Processing will begin shortly.",
        document_id=document.id,
        project_id=project_id,
        document_type="idf",
        file_name=file.filename,
        file_path=cloudinary_result["url"],  # ☁️ Cloudinary URL
        processing_status="pending"
    )


@router.post("/{project_id}/upload/transcription", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_transcription(
    project_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload Transcription document (DOCX)

    Transcription = Interview transcription document
    File naming: {user_id}_{session_id}_transcription.docx
    """
    logger.info(f"Transcription upload request for project {project_id} by user {current_user.email}")

    # Verify project access (ROW-LEVEL SECURITY)
    project = await verify_project_access(project_id, current_user, db)

    # Check if Transcription already exists
    if await check_document_exists(project_id, "transcription", db):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transcription document already uploaded for this project. Delete existing document first."
        )

    # Validate file type
    if not file.filename.lower().endswith('.docx'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only DOCX files are accepted for Transcription documents"
        )

    # Upload to Cloudinary (NO local disk storage)
    cloudinary_result = await save_uploaded_file_cloudinary(
        file,
        current_user.id,
        project.session_id,
        "transcription",
        "docx"
    )

    # Create document record with Cloudinary URL
    document = Document(
        project_id=project_id,
        document_type="transcription",
        file_name=file.filename,
        file_type="docx",
        file_path=cloudinary_result["url"],  # ☁️ Cloudinary URL (not local path)
        file_size_bytes=cloudinary_result.get("bytes", 0),
        processing_status="pending"
    )

    db.add(document)
    db.commit()
    db.refresh(document)

    logger.success(f"Transcription document uploaded: {document.id} for project {project_id}")

    # TODO: Trigger extraction pipeline
    # await process_extraction(document, db)

    return DocumentUploadResponse(
        success=True,
        message="Transcription document uploaded successfully to Cloudinary. Processing will begin shortly.",
        document_id=document.id,
        project_id=project_id,
        document_type="transcription",
        file_name=file.filename,
        file_path=cloudinary_result["url"],  # ☁️ Cloudinary URL
        processing_status="pending"
    )


@router.post("/{project_id}/upload/claims", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_claims(
    project_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload Claims document (DOCX)

    Claims = Patent claims document
    File naming: {user_id}_{session_id}_claims.docx
    """
    logger.info(f"Claims upload request for project {project_id} by user {current_user.email}")

    # Verify project access (ROW-LEVEL SECURITY)
    project = await verify_project_access(project_id, current_user, db)

    # Check if Claims already exists
    if await check_document_exists(project_id, "claims", db):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Claims document already uploaded for this project. Delete existing document first."
        )

    # Validate file type
    if not file.filename.lower().endswith('.docx'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only DOCX files are accepted for Claims documents"
        )

    # Upload to Cloudinary (NO local disk storage)
    cloudinary_result = await save_uploaded_file_cloudinary(
        file,
        current_user.id,
        project.session_id,
        "claims",
        "docx"
    )

    # Create document record with Cloudinary URL
    document = Document(
        project_id=project_id,
        document_type="claims",
        file_name=file.filename,
        file_type="docx",
        file_path=cloudinary_result["url"],  # ☁️ Cloudinary URL (not local path)
        file_size_bytes=cloudinary_result.get("bytes", 0),
        processing_status="pending"
    )

    db.add(document)
    db.commit()
    db.refresh(document)

    logger.success(f"Claims document uploaded: {document.id} for project {project_id}")

    # TODO: Trigger extraction pipeline
    # await process_extraction(document, db)

    return DocumentUploadResponse(
        success=True,
        message="Claims document uploaded successfully to Cloudinary. Processing will begin shortly.",
        document_id=document.id,
        project_id=project_id,
        document_type="claims",
        file_name=file.filename,
        file_path=cloudinary_result["url"],  # ☁️ Cloudinary URL
        processing_status="pending"
    )


@router.get("/{project_id}/documents/{document_id}")
async def get_document(
    project_id: str,
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get document details including extraction results

    ROW-LEVEL SECURITY: Only allows access to user's own project documents
    """
    logger.info(f"Getting document {document_id} for project {project_id}")

    # Verify project access
    project = await verify_project_access(project_id, current_user, db)

    # Get document
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.project_id == project_id  # Extra security check
    ).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    # Return document with extraction if available
    return {
        "id": document.id,
        "document_type": document.document_type,
        "file_name": document.file_name,
        "file_type": document.file_type,
        "file_size_bytes": document.file_size_bytes,
        "processing_status": document.processing_status,
        "error_message": document.error_message,
        "created_at": document.created_at,
        "extraction": document.extraction if document.extraction else None
    }


@router.delete("/{project_id}/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    project_id: str,
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a document and its extraction results

    ROW-LEVEL SECURITY: Only allows deleting user's own project documents
    """
    logger.info(f"Deleting document {document_id} for project {project_id}")

    # Verify project access
    project = await verify_project_access(project_id, current_user, db)

    # Get document
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.project_id == project_id  # Extra security check
    ).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    # Delete document (cascade will delete extraction)
    db.delete(document)
    db.commit()

    logger.success(f"Document {document_id} deleted successfully")

    return None
