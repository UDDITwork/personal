"""
Celery Worker Configuration
Handles async extraction jobs for scalability
"""
from celery import Celery
from loguru import logger
import asyncio
from pathlib import Path

from config import settings

# Initialize Celery app
celery_app = Celery(
    "patmaster_extraction",
    broker=settings.redis_url,
    backend=settings.redis_url
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=settings.extraction_timeout,  # Hard timeout
    task_soft_time_limit=settings.extraction_timeout - 30,  # Soft timeout (warning)
    worker_prefetch_multiplier=1,  # Process one task at a time per worker
    worker_max_tasks_per_child=50,  # Restart worker after 50 tasks (prevent memory leaks)
)


@celery_app.task(name="extract_pdf_async", bind=True)
def extract_pdf_async(self, pdf_path: str, user_id: str, session_id: str):
    """
    Async Celery task for PDF extraction

    Args:
        pdf_path: Path to PDF file
        user_id: User identifier
        session_id: Session identifier

    Returns:
        Extraction result dictionary
    """
    logger.info(f"Starting async PDF extraction: {pdf_path}")

    try:
        # Update task state
        self.update_state(
            state="PROCESSING",
            meta={"stage": "pdf_extraction", "progress": 0.1}
        )

        # Import here to avoid circular imports
        from pipeline.pdf_extractor import extract_pdf_complete
        from pipeline.diagram_describer import describe_diagrams_batch
        from pipeline.merger import merge_complete_extraction, ExtractionMerger
        from pipeline.models import FileType
        import fitz

        # Run async extraction in event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Stage 1: Extract PDF
        self.update_state(
            state="PROCESSING",
            meta={"stage": "extracting_pdf", "progress": 0.2}
        )

        extraction_data = loop.run_until_complete(
            extract_pdf_complete(pdf_path, user_id, session_id)
        )

        # Get total pages
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        file_size = Path(pdf_path).stat().st_size
        file_name = Path(pdf_path).name
        doc.close()

        # Stage 2: Describe diagrams
        images = extraction_data.get("images", [])

        if images:
            self.update_state(
                state="PROCESSING",
                meta={"stage": "describing_diagrams", "progress": 0.6}
            )

            diagram_descriptions = loop.run_until_complete(
                describe_diagrams_batch(images)
            )
        else:
            diagram_descriptions = []

        # Stage 3: Merge results
        self.update_state(
            state="PROCESSING",
            meta={"stage": "merging_results", "progress": 0.9}
        )

        result = merge_complete_extraction(
            user_id=user_id,
            session_id=session_id,
            file_name=file_name,
            file_type=FileType.PDF,
            file_size=file_size,
            extraction_data=extraction_data,
            diagram_descriptions=diagram_descriptions,
            total_pages=total_pages
        )

        # Save result
        from config import get_session_output_dir
        output_dir = get_session_output_dir(user_id, session_id)
        result_path = output_dir / "extraction_result.json"
        ExtractionMerger.save_result_to_json(result, result_path)

        loop.close()

        logger.success(f"Async PDF extraction completed: {pdf_path}")

        return {
            "success": True,
            "session_id": session_id,
            "user_id": user_id,
            "result_path": str(result_path)
        }

    except Exception as e:
        logger.error(f"Async PDF extraction failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@celery_app.task(name="extract_docx_async", bind=True)
def extract_docx_async(self, docx_path: str, user_id: str, session_id: str):
    """
    Async Celery task for DOCX extraction

    Args:
        docx_path: Path to DOCX file
        user_id: User identifier
        session_id: Session identifier

    Returns:
        Extraction result dictionary
    """
    logger.info(f"Starting async DOCX extraction: {docx_path}")

    try:
        # Update task state
        self.update_state(
            state="PROCESSING",
            meta={"stage": "docx_extraction", "progress": 0.1}
        )

        # Import here to avoid circular imports
        from pipeline.docx_extractor import extract_docx_complete
        from pipeline.diagram_describer import describe_diagrams_batch
        from pipeline.merger import merge_complete_extraction, ExtractionMerger
        from pipeline.models import FileType

        # Run async extraction in event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Stage 1: Extract DOCX
        self.update_state(
            state="PROCESSING",
            meta={"stage": "extracting_docx", "progress": 0.2}
        )

        extraction_data = loop.run_until_complete(
            extract_docx_complete(docx_path, user_id, session_id)
        )

        file_size = Path(docx_path).stat().st_size
        file_name = Path(docx_path).name

        # Stage 2: Describe diagrams
        images = extraction_data.get("images", [])

        if images:
            self.update_state(
                state="PROCESSING",
                meta={"stage": "describing_diagrams", "progress": 0.6}
            )

            diagram_descriptions = loop.run_until_complete(
                describe_diagrams_batch(images)
            )
        else:
            diagram_descriptions = []

        # Stage 3: Merge results
        self.update_state(
            state="PROCESSING",
            meta={"stage": "merging_results", "progress": 0.9}
        )

        result = merge_complete_extraction(
            user_id=user_id,
            session_id=session_id,
            file_name=file_name,
            file_type=FileType.DOCX,
            file_size=file_size,
            extraction_data=extraction_data,
            diagram_descriptions=diagram_descriptions,
            total_pages=0
        )

        # Save result
        from config import get_session_output_dir
        output_dir = get_session_output_dir(user_id, session_id)
        result_path = output_dir / "extraction_result.json"
        ExtractionMerger.save_result_to_json(result, result_path)

        loop.close()

        logger.success(f"Async DOCX extraction completed: {docx_path}")

        return {
            "success": True,
            "session_id": session_id,
            "user_id": user_id,
            "result_path": str(result_path)
        }

    except Exception as e:
        logger.error(f"Async DOCX extraction failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@celery_app.task(name="cleanup_old_extractions")
def cleanup_old_extractions(age_hours: int = 24):
    """
    Cleanup extraction files older than specified hours

    Args:
        age_hours: Age in hours after which to delete extraction files
    """
    logger.info(f"Starting cleanup of extractions older than {age_hours} hours")

    try:
        import time
        from config import settings

        output_dir = settings.extracted_output_dir
        current_time = time.time()
        cutoff_time = current_time - (age_hours * 3600)

        deleted_count = 0

        for session_dir in output_dir.iterdir():
            if session_dir.is_dir():
                # Check directory modification time
                mtime = session_dir.stat().st_mtime

                if mtime < cutoff_time:
                    # Delete directory
                    import shutil
                    shutil.rmtree(session_dir)
                    deleted_count += 1
                    logger.info(f"Deleted old extraction: {session_dir.name}")

        logger.success(f"Cleanup completed. Deleted {deleted_count} old extractions")

        return {
            "success": True,
            "deleted_count": deleted_count
        }

    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


# Periodic task configuration (optional - requires celery beat)
celery_app.conf.beat_schedule = {
    "cleanup-every-24-hours": {
        "task": "cleanup_old_extractions",
        "schedule": 86400.0,  # Run every 24 hours
        "args": (24,)  # Delete files older than 24 hours
    }
}
