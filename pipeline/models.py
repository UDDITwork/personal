"""
Pydantic models for document extraction pipeline
Defines all data structures used throughout the extraction process
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime


class FileType(str, Enum):
    """Supported file types for document extraction"""
    PDF = "pdf"
    DOCX = "docx"


class ExtractedImage(BaseModel):
    """Represents an image extracted from a document"""
    image_id: str = Field(..., description="Unique identifier like 'page3_img1'")
    page_number: int = Field(..., description="Page number where image was found")
    image_path: str = Field(..., description="Local path to saved image file")
    image_base64: Optional[str] = Field(None, description="Base64 encoded image for frontend display")
    diagram_description: Optional[str] = Field(None, description="Structured description from Gemini")
    width: Optional[int] = Field(None, description="Image width in pixels")
    height: Optional[int] = Field(None, description="Image height in pixels")


class DiagramDescription(BaseModel):
    """Structured description of a diagram from Gemini Vision API"""
    image_id: str = Field(..., description="References the ExtractedImage.image_id")
    is_diagram: bool = Field(True, description="Whether this image is actually a diagram")
    diagram_type: Optional[str] = Field(None, description="Type: block_diagram, flowchart, architecture, sequence, cross_section, other")
    outermost_elements: List[str] = Field(default_factory=list, description="Top-level blocks/shapes in the diagram")
    shape_mapping: Dict[str, str] = Field(default_factory=dict, description="Maps shape types to element names")
    nested_components: Dict[str, Any] = Field(default_factory=dict, description="Hierarchical nesting structure")
    connections: List[Dict[str, str]] = Field(default_factory=list, description="Arrow/line connections with direction")
    all_text_labels: List[str] = Field(default_factory=list, description="All text/labels visible in diagram")
    description_summary: str = Field(..., description="One paragraph describing the diagram")
    image_type: Optional[str] = Field(None, description="If not a diagram: photo, screenshot, logo, chart, graph")


class ExtractedTable(BaseModel):
    """Represents a table extracted from a document"""
    table_id: str = Field(..., description="Unique identifier like 'page5_table1'")
    page_number: int = Field(..., description="Page number where table was found")
    html_content: str = Field(..., description="Table rendered as HTML")
    headers: List[str] = Field(default_factory=list, description="Column headers")
    rows: List[List[str]] = Field(default_factory=list, description="Table data rows")
    num_rows: int = Field(0, description="Number of rows in table")
    num_cols: int = Field(0, description="Number of columns in table")


class ExtractionMetadata(BaseModel):
    """Metadata about the extraction process"""
    extraction_started_at: datetime = Field(default_factory=datetime.now)
    extraction_completed_at: Optional[datetime] = None
    processing_time_seconds: float = Field(0.0, description="Total processing time")
    llamaparse_time_seconds: Optional[float] = None
    pymupdf_time_seconds: Optional[float] = None
    gemini_time_seconds: Optional[float] = None
    extraction_method: str = Field(..., description="Methods used for extraction")
    errors_encountered: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class ExtractionResult(BaseModel):
    """Complete extraction result for a document"""
    session_id: str = Field(..., description="Unique session identifier")
    user_id: str = Field(..., description="User identifier")
    file_name: str = Field(..., description="Original uploaded file name")
    file_type: FileType = Field(..., description="Type of document (PDF or DOCX)")
    file_size_bytes: int = Field(0, description="Size of uploaded file")
    total_pages: int = Field(..., description="Total number of pages in document")

    # Extracted Content
    extracted_text_markdown: str = Field("", description="Full text in markdown format")
    extracted_text_plain: str = Field("", description="Full text in plain format")
    extracted_images: List[ExtractedImage] = Field(default_factory=list)
    diagram_descriptions: List[DiagramDescription] = Field(default_factory=list)
    extracted_tables: List[ExtractedTable] = Field(default_factory=list)

    # Quality Metrics
    confidence_score: Optional[float] = Field(None, description="Overall extraction confidence from LlamaParse")
    ocr_quality_score: Optional[float] = Field(None, description="OCR quality assessment")

    # Processing Metadata
    metadata: ExtractionMetadata = Field(default_factory=ExtractionMetadata)

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "sess_123456",
                "user_id": "user_789",
                "file_name": "patent_US12345678.pdf",
                "file_type": "pdf",
                "file_size_bytes": 2048000,
                "total_pages": 25,
                "extracted_text_markdown": "# Patent Title\n\n## Abstract\n...",
                "extracted_images": [
                    {
                        "image_id": "page3_img1",
                        "page_number": 3,
                        "image_path": "/extracted_output/user_789_sess_123456/page3_img1.png"
                    }
                ],
                "confidence_score": 0.95,
                "metadata": {
                    "processing_time_seconds": 45.2,
                    "extraction_method": "llamaparse_agentic + gemini_vision + pymupdf"
                }
            }
        }


class UploadResponse(BaseModel):
    """Response returned after file upload"""
    success: bool
    message: str
    session_id: str
    user_id: str
    file_name: str
    file_type: FileType
    task_id: Optional[str] = Field(None, description="Celery task ID for async processing")
    estimated_time_seconds: Optional[int] = Field(None, description="Estimated processing time")


class ExtractionStatus(BaseModel):
    """Status of an ongoing extraction job"""
    session_id: str
    user_id: str
    status: str = Field(..., description="pending, processing, completed, failed")
    progress_percentage: Optional[float] = Field(None, description="0-100 progress indicator")
    current_stage: Optional[str] = Field(None, description="Current processing stage")
    estimated_time_remaining: Optional[int] = Field(None, description="Seconds remaining")
    result: Optional[ExtractionResult] = Field(None, description="Available when status=completed")
    error_message: Optional[str] = Field(None, description="Error details if status=failed")
