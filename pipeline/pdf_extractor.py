"""
PDF Extraction Module
Uses LlamaParse (agentic mode) + PyMuPDF in parallel for maximum extraction quality
"""
import asyncio
import base64
import time
from pathlib import Path
from typing import List, Tuple, Dict, Any
import fitz  # PyMuPDF
from loguru import logger

try:
    from pdf2image import convert_from_path
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    logger.warning("pdf2image not available. Presentation-style PDF fallback disabled.")
    PDF2IMAGE_AVAILABLE = False

try:
    from llama_cloud_services import LlamaParse
except ImportError:
    logger.error("llama-cloud-services not installed. Run: pip install llama-cloud-services")
    raise

from .models import ExtractedImage, ExtractedTable, DiagramDescription
from .table_parser import TableParser
from .mermaid_parser import MermaidParser
from config import settings, get_session_output_dir


class PDFExtractor:
    """Handles PDF extraction using LlamaParse + PyMuPDF in parallel"""

    def __init__(self, user_id: str, session_id: str):
        self.user_id = user_id
        self.session_id = session_id
        self.output_dir = get_session_output_dir(user_id, session_id)

        # Initialize LlamaParse with agentic mode
        self.parser = LlamaParse(
            api_key=settings.llama_cloud_api_key,
            parse_mode="parse_page_with_agent",  # Agentic mode for best results
            model="gemini-2.5-flash",  # Best price/performance ratio
            high_res_ocr=True,  # Maximum OCR accuracy
            adaptive_long_table=True,  # Handle long tables across pages
            outlined_table_extraction=True,  # Better table detection
            output_tables_as_HTML=True,  # Tables as HTML for easy rendering
            result_type="markdown",  # Markdown output for structured text
            num_workers=4,  # Parallel processing for multi-page docs
        )

    async def extract_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extract all content from PDF using parallel LlamaParse + PyMuPDF

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Dictionary containing extracted text, images, tables, and metadata
        """
        logger.info(f"Starting PDF extraction for {pdf_path}")
        start_time = time.time()

        try:
            # Run LlamaParse and PyMuPDF extractions in parallel
            llamaparse_result, pymupdf_result = await asyncio.gather(
                self._extract_with_llamaparse(pdf_path),
                self._extract_with_pymupdf(pdf_path),
                return_exceptions=True
            )

            # Handle errors from either extraction method
            llamaparse_time = 0
            pymupdf_time = 0
            text_markdown = ""
            text_plain = ""
            tables = []
            images = []
            mermaid_diagrams = []
            confidence_score = None

            if isinstance(llamaparse_result, Exception):
                logger.error(f"LlamaParse extraction failed: {llamaparse_result}")
                # Fall back to PyMuPDF only
            else:
                text_markdown = llamaparse_result.get("text_markdown", "")
                text_plain = llamaparse_result.get("text_plain", "")
                tables = llamaparse_result.get("tables", [])
                mermaid_diagrams = llamaparse_result.get("mermaid_diagrams", [])
                confidence_score = llamaparse_result.get("confidence_score")
                llamaparse_time = llamaparse_result.get("processing_time", 0)
                logger.success(f"LlamaParse extraction completed in {llamaparse_time:.2f}s")

            if isinstance(pymupdf_result, Exception):
                logger.error(f"PyMuPDF extraction failed: {pymupdf_result}")
            else:
                images = pymupdf_result.get("images", [])
                pymupdf_time = pymupdf_result.get("processing_time", 0)

                # If LlamaParse failed, use PyMuPDF text as fallback
                if not text_plain and pymupdf_result.get("text_plain"):
                    text_plain = pymupdf_result["text_plain"]
                    logger.warning("Using PyMuPDF text extraction as LlamaParse fallback")

                logger.success(f"PyMuPDF extraction completed in {pymupdf_time:.2f}s")

            # Check if this is a presentation-style PDF and apply image fallback if needed
            if self._is_presentation_style_pdf(pdf_path, len(images), len(mermaid_diagrams)):
                logger.info("Detected presentation-style PDF - applying page image fallback")
                page_images = self._extract_page_images_fallback(pdf_path)
                images.extend(page_images)

            total_time = time.time() - start_time

            return {
                "text_markdown": text_markdown,
                "text_plain": text_plain,
                "images": images,
                "tables": tables,
                "mermaid_diagrams": mermaid_diagrams,
                "confidence_score": confidence_score,
                "llamaparse_time": llamaparse_time,
                "pymupdf_time": pymupdf_time,
                "total_time": total_time,
                "extraction_method": "llamaparse_agentic + pymupdf"
            }

        except Exception as e:
            logger.error(f"PDF extraction failed: {e}")
            raise

    async def _extract_with_llamaparse(self, pdf_path: str) -> Dict[str, Any]:
        """Extract text and tables using LlamaParse agentic mode"""
        start_time = time.time()

        try:
            logger.info("Starting LlamaParse extraction (agentic mode)")

            # Use async load to avoid blocking
            documents = await self.parser.aload_data(pdf_path)

            # Combine all document pages into single markdown and plain text
            text_markdown = ""
            text_plain = ""

            for doc in documents:
                text_markdown += doc.text + "\n\n"
                # Strip markdown formatting for plain text
                text_plain += self._markdown_to_plain(doc.text) + "\n\n"

            # Extract tables from markdown (LlamaParse includes tables in HTML format)
            tables = self._extract_tables_from_markdown(text_markdown)

            # Extract Mermaid diagrams from markdown
            mermaid_diagrams = self._extract_mermaid_diagrams(text_markdown)

            # Get confidence score if available from metadata
            confidence_score = None
            if documents and hasattr(documents[0], 'metadata'):
                confidence_score = documents[0].metadata.get('confidence_score')

            processing_time = time.time() - start_time

            return {
                "text_markdown": text_markdown.strip(),
                "text_plain": text_plain.strip(),
                "tables": tables,
                "mermaid_diagrams": mermaid_diagrams,
                "confidence_score": confidence_score,
                "processing_time": processing_time
            }

        except Exception as e:
            logger.error(f"LlamaParse extraction error: {e}")
            raise

    async def _extract_with_pymupdf(self, pdf_path: str) -> Dict[str, Any]:
        """Extract images and text using PyMuPDF (runs in parallel with LlamaParse)"""
        start_time = time.time()

        try:
            logger.info("Starting PyMuPDF extraction")

            # Run in thread pool to avoid blocking async event loop
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self._pymupdf_sync_extract, pdf_path)

            processing_time = time.time() - start_time
            result["processing_time"] = processing_time

            return result

        except Exception as e:
            logger.error(f"PyMuPDF extraction error: {e}")
            raise

    def _pymupdf_sync_extract(self, pdf_path: str) -> Dict[str, Any]:
        """Synchronous PyMuPDF extraction (called from thread pool)"""
        doc = fitz.open(pdf_path)
        images: List[ExtractedImage] = []
        text_blocks = []
        text_plain = ""

        for page_num, page in enumerate(doc):
            # Extract images from page
            image_list = page.get_images(full=True)

            for img_index, img in enumerate(image_list):
                try:
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]

                    # Save image to disk
                    img_filename = f"page{page_num + 1}_img{img_index + 1}.{image_ext}"
                    img_path = self.output_dir / img_filename

                    with open(img_path, "wb") as f:
                        f.write(image_bytes)

                    # Convert to base64 for frontend display
                    image_base64 = base64.b64encode(image_bytes).decode("utf-8")

                    # Create ExtractedImage object
                    extracted_image = ExtractedImage(
                        image_id=f"page{page_num + 1}_img{img_index + 1}",
                        page_number=page_num + 1,
                        image_path=str(img_path),
                        image_base64=image_base64,
                        width=base_image.get("width"),
                        height=base_image.get("height")
                    )

                    images.append(extracted_image)
                    logger.debug(f"Extracted image: {img_filename}")

                except Exception as e:
                    logger.warning(f"Failed to extract image on page {page_num + 1}: {e}")

            # Extract text with coordinates (for potential future use)
            text_dict = page.get_text("dict")
            text_blocks.append(text_dict)

            # Also extract plain text for fallback
            page_text = page.get_text("text")
            text_plain += f"\n--- Page {page_num + 1} ---\n{page_text}\n"

        doc.close()

        logger.info(f"PyMuPDF extracted {len(images)} images from {len(text_blocks)} pages")

        return {
            "images": images,
            "text_blocks": text_blocks,
            "text_plain": text_plain.strip()
        }

    def _markdown_to_plain(self, markdown: str) -> str:
        """Convert markdown to plain text by removing formatting"""
        # Simple markdown stripping (can be enhanced with libraries like markdown2 if needed)
        plain = markdown
        # Remove headers
        plain = plain.replace("#", "")
        # Remove bold/italic
        plain = plain.replace("**", "").replace("__", "").replace("*", "").replace("_", "")
        # Remove links but keep text
        import re
        plain = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', plain)
        return plain

    def _extract_tables_from_markdown(self, markdown: str) -> List[ExtractedTable]:
        """Extract tables from markdown text (LlamaParse returns tables as HTML)"""
        tables = []

        # LlamaParse with output_tables_as_HTML=True embeds tables as HTML
        # We need to find HTML table tags in the markdown
        import re

        html_pattern = r'<table.*?>(.*?)</table>'
        matches = re.findall(html_pattern, markdown, re.DOTALL | re.IGNORECASE)

        table_parser = TableParser()

        for idx, table_html in enumerate(matches):
            try:
                # Reconstruct full HTML table
                full_html = f"<table>{table_html}</table>"

                # Parse HTML to extract structured data
                headers, rows, num_rows, num_cols = table_parser.parse_html_table(full_html)

                # Try to detect page number from context
                page_number = table_parser.detect_table_page_from_context(full_html, markdown)

                table = ExtractedTable(
                    table_id=f"table_{idx + 1}",
                    page_number=page_number,
                    html_content=full_html,
                    headers=headers,
                    rows=rows,
                    num_rows=num_rows,
                    num_cols=num_cols
                )

                tables.append(table)
                logger.debug(f"Parsed table {idx + 1}: {num_rows} rows x {num_cols} cols on page {page_number}")

            except Exception as e:
                logger.warning(f"Failed to parse table {idx + 1}: {e}")

        return tables

    def _extract_mermaid_diagrams(self, markdown: str) -> List[DiagramDescription]:
        """Extract and parse Mermaid diagrams from markdown text"""
        try:
            mermaid_parser = MermaidParser()
            diagrams = mermaid_parser.extract_mermaid_diagrams(markdown)
            logger.info(f"Extracted {len(diagrams)} Mermaid diagrams from markdown")
            return diagrams
        except Exception as e:
            logger.warning(f"Failed to extract Mermaid diagrams: {e}")
            return []

    def _is_presentation_style_pdf(self, pdf_path: str, images_found: int, mermaid_diagrams_found: int) -> bool:
        """
        Detect if PDF is presentation-style (PPTX converted) that may have rendered diagrams

        Args:
            pdf_path: Path to PDF
            images_found: Number of embedded images found by PyMuPDF
            mermaid_diagrams_found: Number of Mermaid diagrams found in text

        Returns:
            True if PDF appears to be presentation-style
        """
        # If we found Mermaid diagrams but no embedded images, likely a presentation
        if mermaid_diagrams_found > 0 and images_found == 0:
            return True

        # Check page dimensions - presentations typically have landscape aspect ratio
        try:
            doc = fitz.open(pdf_path)
            if len(doc) == 0:
                return False

            first_page = doc[0]
            width = first_page.rect.width
            height = first_page.rect.height
            doc.close()

            # Landscape orientation (width > height) is common for presentations
            # Standard presentation: 10" x 7.5" = 1.33:1 ratio
            aspect_ratio = width / height if height > 0 else 0

            if aspect_ratio > 1.2:  # Landscape
                return True

        except Exception as e:
            logger.debug(f"Error checking PDF dimensions: {e}")

        return False

    def _extract_page_images_fallback(self, pdf_path: str, max_pages: int = 10) -> List[ExtractedImage]:
        """
        Fallback method to extract page images for presentation-style PDFs

        Args:
            pdf_path: Path to PDF
            max_pages: Maximum pages to convert (to avoid huge processing)

        Returns:
            List of ExtractedImage objects (one per page)
        """
        if not PDF2IMAGE_AVAILABLE:
            logger.warning("pdf2image not available, skipping page image extraction")
            return []

        try:
            logger.info(f"Converting PDF pages to images (presentation fallback)")

            # Convert PDF pages to images (limit to first max_pages)
            images = convert_from_path(
                pdf_path,
                dpi=150,  # Good balance of quality and file size
                fmt='png',
                first_page=1,
                last_page=max_pages
            )

            extracted_images = []

            for page_num, pil_image in enumerate(images, start=1):
                try:
                    # Save image to disk
                    img_filename = f"page{page_num}_fullpage.png"
                    img_path = self.output_dir / img_filename

                    pil_image.save(img_path, 'PNG')

                    # Convert to base64
                    import io
                    img_buffer = io.BytesIO()
                    pil_image.save(img_buffer, format='PNG')
                    image_base64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8')

                    # Create ExtractedImage object
                    extracted_image = ExtractedImage(
                        image_id=f"page{page_num}_fullpage",
                        page_number=page_num,
                        image_path=str(img_path),
                        image_base64=image_base64,
                        width=pil_image.width,
                        height=pil_image.height
                    )

                    extracted_images.append(extracted_image)
                    logger.debug(f"Extracted full-page image for page {page_num}")

                except Exception as e:
                    logger.warning(f"Failed to extract page {page_num} as image: {e}")

            logger.success(f"Extracted {len(extracted_images)} full-page images via fallback")
            return extracted_images

        except Exception as e:
            logger.error(f"Page image fallback failed: {e}")
            return []


async def extract_pdf_complete(pdf_path: str, user_id: str, session_id: str) -> Dict[str, Any]:
    """
    Convenience function to extract complete PDF data

    Args:
        pdf_path: Path to PDF file
        user_id: User identifier
        session_id: Session identifier

    Returns:
        Complete extraction result dictionary
    """
    extractor = PDFExtractor(user_id, session_id)
    return await extractor.extract_pdf(pdf_path)
