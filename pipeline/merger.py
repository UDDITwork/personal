"""
Merger Module
Combines extracted data from all sources into final ExtractionResult
"""
import time
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path
from loguru import logger

from .models import (
    ExtractionResult,
    ExtractedImage,
    DiagramDescription,
    ExtractedTable,
    ExtractionMetadata,
    FileType
)


class ExtractionMerger:
    """Merges data from different extraction stages into final result"""

    @staticmethod
    def merge_extraction_data(
        user_id: str,
        session_id: str,
        file_name: str,
        file_type: FileType,
        file_size: int,
        extraction_data: Dict[str, Any],
        diagram_descriptions: List[DiagramDescription],
        total_pages: int = 0
    ) -> ExtractionResult:
        """
        Merge all extraction data into final ExtractionResult

        Args:
            user_id: User identifier
            session_id: Session identifier
            file_name: Original file name
            file_type: PDF or DOCX
            file_size: File size in bytes
            extraction_data: Raw extraction data from PDF/DOCX extractor
            diagram_descriptions: List of diagram descriptions from Gemini
            total_pages: Total pages in document

        Returns:
            Complete ExtractionResult object
        """
        logger.info(f"Merging extraction data for {file_name}")

        # Extract components from extraction_data
        text_markdown = extraction_data.get("text_markdown", "")
        text_plain = extraction_data.get("text_plain", "")
        images = extraction_data.get("images", [])
        tables = extraction_data.get("tables", [])
        confidence_score = extraction_data.get("confidence_score")

        # Processing times
        llamaparse_time = extraction_data.get("llamaparse_time", 0)
        pymupdf_time = extraction_data.get("pymupdf_time", 0)
        gemini_time = extraction_data.get("gemini_time", 0)
        total_time = extraction_data.get("total_time", 0) + gemini_time
        extraction_method = extraction_data.get("extraction_method", "unknown")

        # Merge diagram descriptions with images
        images_merged = ExtractionMerger._merge_diagram_descriptions(
            images, diagram_descriptions
        )

        # Create metadata
        metadata = ExtractionMetadata(
            extraction_started_at=datetime.now(),
            extraction_completed_at=datetime.now(),
            processing_time_seconds=total_time,
            llamaparse_time_seconds=llamaparse_time,
            pymupdf_time_seconds=pymupdf_time,
            gemini_time_seconds=gemini_time,
            extraction_method=extraction_method,
            errors_encountered=[],
            warnings=[]
        )

        # Auto-detect total_pages if not provided
        if total_pages == 0 and file_type == FileType.PDF:
            # Try to infer from images (page numbers)
            page_numbers = [img.page_number for img in images if img.page_number > 0]
            if page_numbers:
                total_pages = max(page_numbers)

        # Create final result
        result = ExtractionResult(
            session_id=session_id,
            user_id=user_id,
            file_name=file_name,
            file_type=file_type,
            file_size_bytes=file_size,
            total_pages=total_pages,
            extracted_text_markdown=text_markdown,
            extracted_text_plain=text_plain,
            extracted_images=images_merged,
            diagram_descriptions=diagram_descriptions,
            extracted_tables=tables,
            confidence_score=confidence_score,
            metadata=metadata
        )

        logger.success(f"Extraction result merged successfully")
        logger.info(f"  - Text length: {len(text_plain)} chars")
        logger.info(f"  - Images: {len(images_merged)}")
        logger.info(f"  - Diagrams described: {len(diagram_descriptions)}")
        logger.info(f"  - Tables: {len(tables)}")
        logger.info(f"  - Processing time: {total_time:.2f}s")

        return result

    @staticmethod
    def _merge_diagram_descriptions(
        images: List[ExtractedImage],
        descriptions: List[DiagramDescription]
    ) -> List[ExtractedImage]:
        """
        Merge diagram descriptions into ExtractedImage objects

        Args:
            images: List of extracted images
            descriptions: List of diagram descriptions

        Returns:
            Updated list of images with diagram descriptions attached
        """
        # Create a mapping of image_id to description
        description_map = {desc.image_id: desc for desc in descriptions}

        # Attach descriptions to images
        merged_images = []
        for image in images:
            if image.image_id in description_map:
                desc = description_map[image.image_id]
                # Attach description summary to image
                image.diagram_description = desc.description_summary

            merged_images.append(image)

        logger.debug(f"Merged {len(description_map)} diagram descriptions with images")
        return merged_images

    @staticmethod
    def deduplicate_content(result: ExtractionResult) -> ExtractionResult:
        """
        Remove duplicate content that might come from multiple extraction sources

        Args:
            result: ExtractionResult to deduplicate

        Returns:
            Deduplicated ExtractionResult
        """
        # For now, no deduplication needed since we're merging cleanly
        # This can be enhanced in the future if LlamaParse also extracts images
        # and we need to deduplicate with PyMuPDF extractions

        return result

    @staticmethod
    def save_result_to_json(result: ExtractionResult, output_path: Path):
        """
        Save ExtractionResult to JSON file

        Args:
            result: ExtractionResult to save
            output_path: Path to save JSON file
        """
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(result.model_dump_json(indent=2))

            logger.success(f"Extraction result saved to {output_path}")

        except Exception as e:
            logger.error(f"Failed to save result to JSON: {e}")
            raise

    @staticmethod
    def load_result_from_json(json_path: Path) -> ExtractionResult:
        """
        Load ExtractionResult from JSON file

        Args:
            json_path: Path to JSON file

        Returns:
            Loaded ExtractionResult
        """
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = f.read()

            result = ExtractionResult.model_validate_json(data)
            logger.success(f"Extraction result loaded from {json_path}")

            return result

        except Exception as e:
            logger.error(f"Failed to load result from JSON: {e}")
            raise


def merge_complete_extraction(
    user_id: str,
    session_id: str,
    file_name: str,
    file_type: FileType,
    file_size: int,
    extraction_data: Dict[str, Any],
    diagram_descriptions: List[DiagramDescription],
    total_pages: int = 0
) -> ExtractionResult:
    """
    Convenience function to merge all extraction data

    Args:
        user_id: User identifier
        session_id: Session identifier
        file_name: Original file name
        file_type: PDF or DOCX
        file_size: File size in bytes
        extraction_data: Raw extraction data
        diagram_descriptions: Diagram descriptions from Gemini
        total_pages: Total pages in document

    Returns:
        Complete ExtractionResult
    """
    merger = ExtractionMerger()
    return merger.merge_extraction_data(
        user_id=user_id,
        session_id=session_id,
        file_name=file_name,
        file_type=file_type,
        file_size=file_size,
        extraction_data=extraction_data,
        diagram_descriptions=diagram_descriptions,
        total_pages=total_pages
    )
