"""
Hybrid PDF Extraction Module
Runs THREE extraction engines in parallel and merges results:
1. LlamaParse V1 (old API) - text, tables, Mermaid diagrams
2. LlamaCloud V2 (new API) - structured items, bounding boxes, page screenshots
3. PyMuPDF - embedded images, fallback text

Combines best results from all three sources for maximum accuracy
"""
import asyncio
import time
from pathlib import Path
from typing import List, Dict, Any
from loguru import logger

from .pdf_extractor import PDFExtractor  # V1 - Old LlamaParse
from .pdf_extractor_v2 import PDFExtractorV2, LLAMACLOUD_AVAILABLE  # V2 - New LlamaCloud
from .models import ExtractedImage, ExtractedTable, DiagramDescription
from config import get_session_output_dir


class HybridPDFExtractor:
    """
    Orchestrates triple-layer PDF extraction:
    - Layer 1: LlamaParse V1 (proven, stable)
    - Layer 2: LlamaCloud V2 (advanced features, bounding boxes)
    - Layer 3: PyMuPDF (direct image extraction)
    """

    def __init__(self, user_id: str, session_id: str):
        self.user_id = user_id
        self.session_id = session_id
        self.output_dir = get_session_output_dir(user_id, session_id)

        # Initialize all extractors
        self.extractor_v1 = PDFExtractor(user_id, session_id)  # Includes PyMuPDF

        self.extractor_v2 = None
        if LLAMACLOUD_AVAILABLE:
            try:
                self.extractor_v2 = PDFExtractorV2(user_id, session_id)
                logger.info("LlamaCloud V2 extractor initialized")
            except Exception as e:
                logger.warning(f"LlamaCloud V2 extractor failed to initialize: {e}")
        else:
            logger.warning("LlamaCloud V2 not available, will use V1 + PyMuPDF only")

    async def extract_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """
        Run all three extraction layers in parallel and merge results

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Merged extraction results from all sources
        """
        logger.info(f"🚀 Starting TRIPLE-LAYER extraction for {pdf_path}")
        start_time = time.time()

        try:
            # Launch all extractors in parallel
            tasks = []

            # Layer 1: Old LlamaParse + PyMuPDF (always runs)
            logger.info("⚡ Launching Layer 1: LlamaParse V1 + PyMuPDF")
            tasks.append(self.extractor_v1.extract_pdf(pdf_path))

            # Layer 2: New LlamaCloud (if available)
            if self.extractor_v2:
                logger.info("⚡ Launching Layer 2: LlamaCloud V2")
                tasks.append(self.extractor_v2.extract_pdf(pdf_path))
            else:
                # Create dummy result if V2 unavailable
                logger.info("⚠️  Layer 2 skipped: LlamaCloud V2 not available")
                async def dummy_v2():
                    return {
                        "text_markdown": "",
                        "text_plain": "",
                        "images": [],
                        "tables": [],
                        "mermaid_diagrams": [],
                        "total_time": 0,
                        "extraction_method": "llamacloud_v2_unavailable"
                    }
                tasks.append(dummy_v2())

            # Run all tasks in parallel
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Unpack results
            v1_result = results[0] if not isinstance(results[0], Exception) else None
            v2_result = results[1] if len(results) > 1 and not isinstance(results[1], Exception) else None

            # Handle extraction failures
            if isinstance(results[0], Exception):
                logger.error(f"Layer 1 (V1) failed: {results[0]}")
                v1_result = self._get_empty_result("llamaparse_v1_failed")

            if len(results) > 1 and isinstance(results[1], Exception):
                logger.error(f"Layer 2 (V2) failed: {results[1]}")
                v2_result = self._get_empty_result("llamacloud_v2_failed")

            # Merge results from all layers
            logger.info("🔄 Merging results from all layers...")
            merged_result = self._merge_extraction_results(v1_result, v2_result)

            total_time = time.time() - start_time
            merged_result["total_time"] = total_time

            logger.success(f"✅ TRIPLE-LAYER extraction completed in {total_time:.2f}s")
            self._log_extraction_summary(v1_result, v2_result, merged_result)

            return merged_result

        except Exception as e:
            logger.error(f"Hybrid extraction failed: {e}")
            raise

    def _merge_extraction_results(
        self,
        v1_result: Dict[str, Any],
        v2_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Intelligently merge results from both extraction layers

        Strategy:
        - Text: Prefer V2 (page-level), fallback to V1
        - Tables: Combine both (V2 has bboxes, V1 may catch more)
        - Images: Combine both (V2 has screenshots, V1 has embedded via PyMuPDF)
        - Mermaid: Combine both (same source but good to merge)
        """

        # Text merging - prefer V2 for page-level structure
        text_markdown = v2_result.get("text_markdown") or v1_result.get("text_markdown", "")
        text_plain = v2_result.get("text_plain") or v1_result.get("text_plain", "")

        # If both available, use V2 (better page tracking)
        if v2_result.get("text_markdown") and v1_result.get("text_markdown"):
            logger.info("Using LlamaCloud V2 text (has page markers)")
        elif v1_result.get("text_markdown"):
            logger.info("Using LlamaParse V1 text (V2 unavailable)")

        # Tables merging - combine both sources
        tables_v1 = v1_result.get("tables", [])
        tables_v2 = v2_result.get("tables", [])

        # V2 tables have bounding boxes and exact page numbers
        # V1 tables may catch tables V2 missed
        merged_tables = self._merge_tables(tables_v1, tables_v2)

        # Images merging - combine all sources
        images_v1 = v1_result.get("images", [])  # Embedded images + presentation fallback
        images_v2 = v2_result.get("images", [])  # Page screenshots + embedded + layout

        merged_images = self._merge_images(images_v1, images_v2)

        # Mermaid diagrams - combine both (deduplicate by content)
        mermaid_v1 = v1_result.get("mermaid_diagrams", [])
        mermaid_v2 = v2_result.get("mermaid_diagrams", [])

        merged_mermaid = self._merge_mermaid_diagrams(mermaid_v1, mermaid_v2)

        # Metadata merging
        v1_time = v1_result.get("llamaparse_time", 0) + v1_result.get("pymupdf_time", 0)
        v2_time = v2_result.get("total_time", 0)

        return {
            "text_markdown": text_markdown,
            "text_plain": text_plain,
            "images": merged_images,
            "tables": merged_tables,
            "mermaid_diagrams": merged_mermaid,
            "confidence_score": v1_result.get("confidence_score") or v2_result.get("confidence_score"),
            "v1_processing_time": v1_time,
            "v2_processing_time": v2_time,
            "extraction_method": "hybrid_triple_layer (v1 + v2 + pymupdf)",
            "extraction_sources": {
                "v1": v1_result.get("extraction_method", "unknown"),
                "v2": v2_result.get("extraction_method", "unknown")
            }
        }

    def _merge_tables(
        self,
        tables_v1: List[ExtractedTable],
        tables_v2: List[ExtractedTable]
    ) -> List[ExtractedTable]:
        """
        Merge tables from both sources
        - Prefer V2 tables (have bounding boxes and exact page numbers)
        - Add V1 tables that V2 might have missed (deduplicate by content similarity)
        """
        merged = []

        # Add all V2 tables (priority - they have bounding boxes)
        for table in tables_v2:
            merged.append(table)

        # Add V1 tables that don't match V2 tables
        for v1_table in tables_v1:
            # Check if similar table exists in V2
            is_duplicate = False
            for v2_table in tables_v2:
                if self._tables_are_similar(v1_table, v2_table):
                    is_duplicate = True
                    break

            if not is_duplicate:
                merged.append(v1_table)

        logger.info(f"Tables merged: {len(tables_v2)} from V2, {len(tables_v1)} from V1, {len(merged)} total (deduped)")
        return merged

    def _tables_are_similar(self, table1: ExtractedTable, table2: ExtractedTable) -> bool:
        """Check if two tables are likely the same (for deduplication)"""
        # Same page and similar row/col counts
        if table1.page_number > 0 and table2.page_number > 0:
            if table1.page_number == table2.page_number:
                if abs(table1.num_rows - table2.num_rows) <= 1:
                    if abs(table1.num_cols - table2.num_cols) <= 1:
                        return True

        # Similar content (first row signature)
        if table1.headers and table2.headers:
            if len(table1.headers) == len(table2.headers):
                # Check if headers match
                matches = sum(1 for h1, h2 in zip(table1.headers, table2.headers) if h1.lower() == h2.lower())
                if matches / len(table1.headers) > 0.7:  # 70% header match
                    return True

        return False

    def _merge_images(
        self,
        images_v1: List[ExtractedImage],
        images_v2: List[ExtractedImage]
    ) -> List[ExtractedImage]:
        """
        Merge images from both sources
        - V1: Embedded images (PyMuPDF) + presentation fallback (pdf2image)
        - V2: Page screenshots + embedded + layout images
        - Keep all unique images
        """
        merged = []

        # Add all V2 images (page screenshots are unique to V2)
        for img in images_v2:
            merged.append(img)

        # Add V1 images that don't overlap with V2
        for v1_img in images_v1:
            # Check if same image exists in V2 (by page number and type)
            is_duplicate = False
            for v2_img in images_v2:
                if v1_img.page_number == v2_img.page_number:
                    # If both are from same page and similar type, likely duplicate
                    if v1_img.image_id.startswith("page") and v2_img.image_type == "screenshot":
                        is_duplicate = True
                        break

            if not is_duplicate:
                merged.append(v1_img)

        logger.info(f"Images merged: {len(images_v2)} from V2, {len(images_v1)} from V1, {len(merged)} total")
        return merged

    def _merge_mermaid_diagrams(
        self,
        diagrams_v1: List[DiagramDescription],
        diagrams_v2: List[DiagramDescription]
    ) -> List[DiagramDescription]:
        """Merge Mermaid diagrams (usually identical, but combine to be safe)"""
        # Mermaid diagrams come from markdown text, so V1 and V2 should find the same ones
        # Use V2 if available (better page tracking), otherwise V1
        if diagrams_v2:
            logger.info(f"Using {len(diagrams_v2)} Mermaid diagrams from V2")
            return diagrams_v2
        else:
            logger.info(f"Using {len(diagrams_v1)} Mermaid diagrams from V1")
            return diagrams_v1

    def _get_empty_result(self, method: str) -> Dict[str, Any]:
        """Return empty result structure for failed extractions"""
        return {
            "text_markdown": "",
            "text_plain": "",
            "images": [],
            "tables": [],
            "mermaid_diagrams": [],
            "total_time": 0,
            "extraction_method": method
        }

    def _log_extraction_summary(
        self,
        v1_result: Dict[str, Any],
        v2_result: Dict[str, Any],
        merged_result: Dict[str, Any]
    ):
        """Log detailed summary of extraction results"""
        logger.info("=" * 60)
        logger.info("EXTRACTION SUMMARY")
        logger.info("=" * 60)

        # Layer 1 stats
        v1_tables = len(v1_result.get("tables", []))
        v1_images = len(v1_result.get("images", []))
        v1_mermaid = len(v1_result.get("mermaid_diagrams", []))
        v1_time = v1_result.get("llamaparse_time", 0) + v1_result.get("pymupdf_time", 0)

        logger.info(f"Layer 1 (V1 + PyMuPDF):")
        logger.info(f"  - Tables: {v1_tables}")
        logger.info(f"  - Images: {v1_images}")
        logger.info(f"  - Mermaid: {v1_mermaid}")
        logger.info(f"  - Time: {v1_time:.2f}s")

        # Layer 2 stats
        v2_tables = len(v2_result.get("tables", []))
        v2_images = len(v2_result.get("images", []))
        v2_mermaid = len(v2_result.get("mermaid_diagrams", []))
        v2_time = v2_result.get("total_time", 0)

        logger.info(f"Layer 2 (LlamaCloud V2):")
        logger.info(f"  - Tables: {v2_tables} (with bboxes)")
        logger.info(f"  - Images: {v2_images} (screenshots + embedded)")
        logger.info(f"  - Mermaid: {v2_mermaid}")
        logger.info(f"  - Time: {v2_time:.2f}s")

        # Merged stats
        merged_tables = len(merged_result.get("tables", []))
        merged_images = len(merged_result.get("images", []))
        merged_mermaid = len(merged_result.get("mermaid_diagrams", []))
        merged_time = merged_result.get("total_time", 0)

        logger.info(f"MERGED RESULT:")
        logger.info(f"  - Tables: {merged_tables} ({merged_tables - max(v1_tables, v2_tables)} additional)")
        logger.info(f"  - Images: {merged_images} (combined from both)")
        logger.info(f"  - Mermaid: {merged_mermaid}")
        logger.info(f"  - Total Time: {merged_time:.2f}s")
        logger.info("=" * 60)


async def extract_pdf_hybrid(pdf_path: str, user_id: str, session_id: str) -> Dict[str, Any]:
    """
    Convenience function for hybrid triple-layer extraction

    Args:
        pdf_path: Path to PDF file
        user_id: User identifier
        session_id: Session identifier

    Returns:
        Merged extraction results from all layers
    """
    extractor = HybridPDFExtractor(user_id, session_id)
    return await extractor.extract_pdf(pdf_path)
