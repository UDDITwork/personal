"""
Projects Router
Handles project management with row-level security
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from loguru import logger
import uuid

from database import get_db, User, Project, Document
from auth.dependencies import get_current_user

router = APIRouter(
    prefix="/api/v1/projects",
    tags=["Projects"]
)


# Request/Response Models
class ProjectCreate(BaseModel):
    """Project creation request"""
    name: str = Field(..., min_length=1, max_length=255, description="Project name")
    description: Optional[str] = Field(None, description="Project description")


class ProjectUpdate(BaseModel):
    """Project update request"""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="New project name")
    description: Optional[str] = Field(None, description="New project description")


class DocumentSummary(BaseModel):
    """Summary of a document in a project"""
    id: str
    document_type: str
    file_name: str
    file_type: str
    processing_status: str
    created_at: datetime


class ProjectResponse(BaseModel):
    """Project information response"""
    id: str
    name: str
    description: Optional[str]
    session_id: str
    created_at: datetime
    updated_at: datetime
    documents: List[DocumentSummary] = []


class ProjectListItem(BaseModel):
    """Project list item (without documents)"""
    id: str
    name: str
    description: Optional[str]
    session_id: str
    created_at: datetime
    updated_at: datetime
    document_count: int


# Endpoints

@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    request: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new project for the authenticated user

    Each project gets a unique session_id for file storage
    """
    logger.info(f"Creating project '{request.name}' for user {current_user.email}")

    # Generate unique session ID for file storage
    session_id = str(uuid.uuid4())

    # Create project
    project = Project(
        user_id=current_user.id,
        name=request.name,
        description=request.description,
        session_id=session_id
    )

    db.add(project)
    db.commit()
    db.refresh(project)

    logger.success(f"Project created: {project.name} (ID: {project.id}, Session: {session_id})")

    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        session_id=project.session_id,
        created_at=project.created_at,
        updated_at=project.updated_at,
        documents=[]
    )


@router.get("/", response_model=List[ProjectListItem])
async def list_projects(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all projects for the authenticated user

    ROW-LEVEL SECURITY: Only returns projects owned by current user
    """
    logger.info(f"Listing projects for user {current_user.email}")

    # Query projects for current user only (ROW-LEVEL SECURITY)
    projects = db.query(Project).filter(
        Project.user_id == current_user.id
    ).order_by(Project.created_at.desc()).all()

    # Build response with document counts
    response = []
    for project in projects:
        document_count = db.query(Document).filter(
            Document.project_id == project.id
        ).count()

        response.append(ProjectListItem(
            id=project.id,
            name=project.name,
            description=project.description,
            session_id=project.session_id,
            created_at=project.created_at,
            updated_at=project.updated_at,
            document_count=document_count
        ))

    logger.info(f"Found {len(response)} projects for user {current_user.email}")

    return response


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific project

    ROW-LEVEL SECURITY: Only allows access to user's own projects
    """
    logger.info(f"Getting project {project_id} for user {current_user.email}")

    # Query with row-level security check
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

    # Get documents for this project
    documents = db.query(Document).filter(
        Document.project_id == project_id
    ).order_by(Document.created_at.desc()).all()

    # Build document summaries
    document_summaries = [
        DocumentSummary(
            id=doc.id,
            document_type=doc.document_type,
            file_name=doc.file_name,
            file_type=doc.file_type,
            processing_status=doc.processing_status,
            created_at=doc.created_at
        )
        for doc in documents
    ]

    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        session_id=project.session_id,
        created_at=project.created_at,
        updated_at=project.updated_at,
        documents=document_summaries
    )


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    request: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update project details

    ROW-LEVEL SECURITY: Only allows updating user's own projects
    """
    logger.info(f"Updating project {project_id} for user {current_user.email}")

    # Query with row-level security check
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

    # Update fields if provided
    if request.name is not None:
        project.name = request.name

    if request.description is not None:
        project.description = request.description

    project.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(project)

    logger.success(f"Project {project_id} updated successfully")

    # Get documents for response
    documents = db.query(Document).filter(
        Document.project_id == project_id
    ).order_by(Document.created_at.desc()).all()

    document_summaries = [
        DocumentSummary(
            id=doc.id,
            document_type=doc.document_type,
            file_name=doc.file_name,
            file_type=doc.file_type,
            processing_status=doc.processing_status,
            created_at=doc.created_at
        )
        for doc in documents
    ]

    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        session_id=project.session_id,
        created_at=project.created_at,
        updated_at=project.updated_at,
        documents=document_summaries
    )


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a project and all its documents

    ROW-LEVEL SECURITY: Only allows deleting user's own projects
    """
    logger.info(f"Deleting project {project_id} for user {current_user.email}")

    # Query with row-level security check
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

    # Delete project (cascade will delete documents, extractions, etc.)
    db.delete(project)
    db.commit()

    logger.success(f"Project {project_id} deleted successfully")

    return None
