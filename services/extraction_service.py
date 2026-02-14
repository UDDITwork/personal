"""
Extraction Service
Integrates document uploads with the extraction pipeline
Saves results to database
"""
import asyncio
import json
from sqlalchemy.orm import Session
from loguru import logger
from typing import List

from database.models import (
    Document,
    Extraction,
    ExtractedImage,
    DiagramDescription,
    ExtractedTable
)

# Import existing extraction pipeline modules
from pipeline.pdf_extractor_hybrid import extract_pdf_hybrid
from pipeline.docx_extractor import extract_docx_complete
from pipeline.diagram_describer import describe_diagrams_batch


async def process_extraction(document: Document, db: Session):
    """
    Process document extraction and save results to database

    Args:
        document: Document model instance to process
        db: Database session

    This function:
    1. Updates document status to 'processing'
    2. Calls appropriate extraction pipeline based on file type
    3. Saves extraction results to database
    4. Updates document status to 'completed' or 'failed'
    """
    try:
        logger.info(f"Starting extraction for document {document.id} ({document.document_type})")

        # Update status to processing
        document.processing_status = "processing"
        db.commit()

        # Get project details for user_id and session_id
        project = document.project
        user_id = project.user.id
        session_id = project.session_id

        # Extract based on file type
        if document.file_type == "pdf":
            logger.info(f"Running hybrid PDF extraction for {document.file_path}")
            extraction_data = await extract_pdf_hybrid(
                document.file_path,
                user_id,
                session_id
            )

        elif document.file_type == "docx":
            logger.info(f"Running DOCX extraction for {document.file_path}")
            extraction_data = await extract_docx_complete(
                document.file_path,
                user_id,
                session_id
            )

        else:
            raise ValueError(f"Unsupported file type: {document.file_type}")

        # Describe diagrams using Gemini Vision
        images = extraction_data.get("images", [])
        diagram_descriptions = []

        if images:
            logger.info(f"Describing {len(images)} diagrams with Gemini Vision")
            try:
                diagram_descriptions = await describe_diagrams_batch(images)
            except Exception as e:
                logger.warning(f"Diagram description failed: {e}")
                # Continue without diagram descriptions

        # Save extraction results to database
        await save_extraction_to_db(document, extraction_data, diagram_descriptions, db)

        # Update document status
        document.processing_status = "completed"
        db.commit()

        logger.success(f"Extraction completed for document {document.id}")

    except Exception as e:
        logger.error(f"Extraction failed for document {document.id}: {e}")

        # Update document status to failed
        document.processing_status = "failed"
        document.error_message = str(e)
        db.commit()

        raise


async def save_extraction_to_db(
    document: Document,
    extraction_data: dict,
    diagram_descriptions: List,
    db: Session
):
    """
    Save extraction results to database

    Args:
        document: Document being processed
        extraction_data: Extraction results from pipeline
        diagram_descriptions: Diagram descriptions from Gemini
        db: Database session
    """
    logger.info(f"Saving extraction results to database for document {document.id}")

    # Create extraction record
    extraction = Extraction(
        document_id=document.id,
        extracted_text_markdown=extraction_data.get("text_markdown", ""),
        extracted_text_plain=extraction_data.get("text_plain", ""),
        total_pages=len(extraction_data.get("images", [])) if extraction_data.get("images") else 0,
        confidence_score=int(extraction_data.get("confidence_score", 0) * 100) if extraction_data.get("confidence_score") else None,
        llamaparse_time=int(extraction_data.get("v1_processing_time", 0) * 1000),  # Convert to ms
        pymupdf_time=int(extraction_data.get("v2_processing_time", 0) * 1000),
        gemini_time=int(extraction_data.get("gemini_time", 0) * 1000),
        total_time=int(extraction_data.get("total_time", 0) * 1000),
        extraction_method=extraction_data.get("extraction_method", "unknown"),
        extraction_metadata=json.dumps(extraction_data.get("extraction_sources", {}))
    )

    db.add(extraction)
    db.flush()  # Get extraction.id before adding related records

    # Save images
    for img in extraction_data.get("images", []):
        image = ExtractedImage(
            extraction_id=extraction.id,
            image_id=img.image_id if hasattr(img, 'image_id') else img.get("image_id", ""),
            page_number=img.page_number if hasattr(img, 'page_number') else img.get("page_number", 0),
            image_path=img.image_path if hasattr(img, 'image_path') else img.get("image_path", ""),
            image_type=img.image_type if hasattr(img, 'image_type') else img.get("image_type"),
            width=img.width if hasattr(img, 'width') else img.get("width"),
            height=img.height if hasattr(img, 'height') else img.get("height"),
            presigned_url=img.presigned_url if hasattr(img, 'presigned_url') else img.get("presigned_url"),
            diagram_description=img.diagram_description if hasattr(img, 'diagram_description') else img.get("diagram_description")
        )
        db.add(image)

    logger.info(f"Saved {len(extraction_data.get('images', []))} images")

    # Save diagram descriptions
    for desc in diagram_descriptions:
        diagram = DiagramDescription(
            extraction_id=extraction.id,
            image_id=desc.image_id if hasattr(desc, 'image_id') else desc.get("image_id", ""),
            is_diagram=desc.is_diagram if hasattr(desc, 'is_diagram') else desc.get("is_diagram", True),
            diagram_type=desc.diagram_type if hasattr(desc, 'diagram_type') else desc.get("diagram_type"),
            outermost_elements=json.dumps(desc.outermost_elements if hasattr(desc, 'outermost_elements') else desc.get("outermost_elements", [])),
            shape_mapping=json.dumps(desc.shape_mapping if hasattr(desc, 'shape_mapping') else desc.get("shape_mapping", {})),
            nested_components=json.dumps(desc.nested_components if hasattr(desc, 'nested_components') else desc.get("nested_components", {})),
            connections=json.dumps(desc.connections if hasattr(desc, 'connections') else desc.get("connections", [])),
            all_text_labels=json.dumps(desc.all_text_labels if hasattr(desc, 'all_text_labels') else desc.get("all_text_labels", [])),
            description_summary=desc.description_summary if hasattr(desc, 'description_summary') else desc.get("description_summary", ""),
            image_type=desc.image_type if hasattr(desc, 'image_type') else desc.get("image_type")
        )
        db.add(diagram)

    logger.info(f"Saved {len(diagram_descriptions)} diagram descriptions")

    # Save tables
    for tbl in extraction_data.get("tables", []):
        table = ExtractedTable(
            extraction_id=extraction.id,
            table_id=tbl.table_id if hasattr(tbl, 'table_id') else tbl.get("table_id", ""),
            page_number=tbl.page_number if hasattr(tbl, 'page_number') else tbl.get("page_number", 0),
            html_content=tbl.html_content if hasattr(tbl, 'html_content') else tbl.get("html_content", ""),
            headers_json=json.dumps(tbl.headers if hasattr(tbl, 'headers') else tbl.get("headers", [])),
            rows_json=json.dumps(tbl.rows if hasattr(tbl, 'rows') else tbl.get("rows", [])),
            num_rows=tbl.num_rows if hasattr(tbl, 'num_rows') else tbl.get("num_rows", 0),
            num_cols=tbl.num_cols if hasattr(tbl, 'num_cols') else tbl.get("num_cols", 0),
            b_box_x=tbl.b_box.x if (hasattr(tbl, 'b_box') and tbl.b_box) else None,
            b_box_y=tbl.b_box.y if (hasattr(tbl, 'b_box') and tbl.b_box) else None,
            b_box_width=tbl.b_box.width if (hasattr(tbl, 'b_box') and tbl.b_box) else None,
            b_box_height=tbl.b_box.height if (hasattr(tbl, 'b_box') and tbl.b_box) else None,
            extraction_source=tbl.extraction_source if hasattr(tbl, 'extraction_source') else tbl.get("extraction_source")
        )
        db.add(table)

    logger.info(f"Saved {len(extraction_data.get('tables', []))} tables")

    # Commit all changes
    db.commit()

    logger.success(f"Extraction results saved successfully to database")
