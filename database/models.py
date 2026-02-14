"""
SQLAlchemy Models for Multi-Tenant Authentication System
Defines database schema for Turso SQLite database
"""
from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey, Boolean, Index
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime
import uuid

Base = declarative_base()


class User(Base):
    """User account with email/password authentication"""
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    password_salt = Column(String(64), nullable=False)
    full_name = Column(String(255))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    projects = relationship("Project", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")


class UserSession(Base):
    """JWT token sessions for authentication"""
    __tablename__ = "user_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    access_token = Column(String(512), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="sessions")


class Project(Base):
    """User projects containing documents for extraction"""
    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    session_id = Column(String(255), unique=True, nullable=False, index=True)  # For file storage
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="projects")
    documents = relationship("Document", back_populates="project", cascade="all, delete-orphan")


class Document(Base):
    """Documents uploaded to projects (IDF, Transcription, Claims)"""
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    document_type = Column(String(50), nullable=False)  # idf, transcription, claims
    file_name = Column(String(255), nullable=False)
    file_type = Column(String(20), nullable=False)  # pdf, docx
    file_path = Column(String(512))
    file_size_bytes = Column(Integer, default=0)
    processing_status = Column(String(50), default="pending")  # pending, processing, completed, failed
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="documents")
    extraction = relationship("Extraction", back_populates="document", uselist=False, cascade="all, delete-orphan")

    # Index for faster lookups
    __table_args__ = (
        Index('idx_project_doctype', 'project_id', 'document_type'),
    )


class Extraction(Base):
    """Extraction results from document processing"""
    __tablename__ = "extractions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    extracted_text_markdown = Column(Text)
    extracted_text_plain = Column(Text)
    total_pages = Column(Integer)
    confidence_score = Column(Integer)  # 0-100
    llamaparse_time = Column(Integer)  # milliseconds
    pymupdf_time = Column(Integer)
    gemini_time = Column(Integer)
    total_time = Column(Integer)
    extraction_method = Column(String(255))  # e.g., "hybrid_triple_layer (v1 + v2 + pymupdf)"
    extraction_metadata = Column(Text)  # JSON
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    document = relationship("Document", back_populates="extraction")
    images = relationship("ExtractedImage", back_populates="extraction", cascade="all, delete-orphan")
    tables = relationship("ExtractedTable", back_populates="extraction", cascade="all, delete-orphan")
    diagrams = relationship("DiagramDescription", back_populates="extraction", cascade="all, delete-orphan")


class ExtractedImage(Base):
    """Images extracted from documents"""
    __tablename__ = "extracted_images"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    extraction_id = Column(String(36), ForeignKey("extractions.id", ondelete="CASCADE"), nullable=False, index=True)
    image_id = Column(String(255), nullable=False)  # e.g., "page3_img1"
    page_number = Column(Integer, nullable=False)
    image_path = Column(String(512))
    image_type = Column(String(50))  # embedded, screenshot, layout
    width = Column(Integer)
    height = Column(Integer)
    presigned_url = Column(String(1024))
    diagram_description = Column(Text)  # Summary from Gemini Vision
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    extraction = relationship("Extraction", back_populates="images")

    # Index for faster page lookups
    __table_args__ = (
        Index('idx_extraction_page', 'extraction_id', 'page_number'),
    )


class DiagramDescription(Base):
    """Structured diagram descriptions from Gemini Vision and Mermaid parsing"""
    __tablename__ = "diagram_descriptions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    extraction_id = Column(String(36), ForeignKey("extractions.id", ondelete="CASCADE"), nullable=False, index=True)
    image_id = Column(String(255), nullable=False)
    is_diagram = Column(Boolean, default=True)
    diagram_type = Column(String(100))  # flowchart, block_diagram, architecture, sequence, etc.
    outermost_elements = Column(Text)  # JSON array
    shape_mapping = Column(Text)  # JSON object
    nested_components = Column(Text)  # JSON object
    connections = Column(Text)  # JSON array
    all_text_labels = Column(Text)  # JSON array
    description_summary = Column(Text)
    image_type = Column(String(50))  # If not diagram: photo, screenshot, logo, chart, graph
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    extraction = relationship("Extraction", back_populates="diagrams")


class ExtractedTable(Base):
    """Tables extracted from documents"""
    __tablename__ = "extracted_tables"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    extraction_id = Column(String(36), ForeignKey("extractions.id", ondelete="CASCADE"), nullable=False, index=True)
    table_id = Column(String(255), nullable=False)  # e.g., "page5_table1"
    page_number = Column(Integer, nullable=False)
    html_content = Column(Text)
    headers_json = Column(Text)  # JSON array
    rows_json = Column(Text)  # JSON array of arrays
    num_rows = Column(Integer, default=0)
    num_cols = Column(Integer, default=0)
    b_box_x = Column(Integer)  # Bounding box coordinates
    b_box_y = Column(Integer)
    b_box_width = Column(Integer)
    b_box_height = Column(Integer)
    extraction_source = Column(String(50))  # llamaparse_v1, llamacloud_v2, merged
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    extraction = relationship("Extraction", back_populates="tables")

    # Index for faster page lookups
    __table_args__ = (
        Index('idx_extraction_table_page', 'extraction_id', 'page_number'),
    )
