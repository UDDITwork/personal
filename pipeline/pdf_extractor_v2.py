"""
PDF Extraction Module V2 - LlamaCloud API
Uses the new LlamaCloud API with advanced parsing options
Provides structured page-level results, bounding boxes, and page screenshots
"""
import asyncio
import base64
import time
import httpx
from pathlib import Path
from typing import List, Dict, Any, Optional
from loguru import logger

try:
    from llama_cloud import AsyncLlamaCloud
    from llama_cloud.types import ItemsPageStructuredResultPageItemTableItem
    LLAMACLOUD_AVAILABLE = True
except ImportError:
    logger.error("llama-cloud not installed. Run: pip install llama-cloud")
    LLAMACLOUD_AVAILABLE = False

from .models import ExtractedImage, ExtractedTable, DiagramDescription, BoundingBox
from .table_parser import TableParser
from .mermaid_parser import MermaidParser
from config import settings, get_session_output_dir


class PDFExtractorV2:
    """Handles PDF extraction using new LlamaCloud API with advanced features"""

    def __init__(self, user_id: str, session_id: str):
        if not LLAMACLOUD_AVAILABLE:
            raise ImportError("llama-cloud package not available")

        self.user_id = user_id
        self.session_id = session_id
        self.output_dir = get_session_output_dir(user_id, session_id)

        # Initialize LlamaCloud client
        self.client = AsyncLlamaCloud(api_key=settings.llama_cloud_api_key)

    async def extract_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extract all content from PDF using LlamaCloud API with advanced options

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Dictionary containing extracted text, images, tables, and metadata
        """
        logger.info(f"Starting LlamaCloud V2 extraction for {pdf_path}")
        start_time = time.time()

        try:
            # Step 1: Upload file to LlamaCloud
            upload_start = time.time()
            file_obj = await self.client.files.create(
                file=pdf_path,
                purpose="parse"
            )
            upload_time = time.time() - upload_start
            logger.info(f"File uploaded to LlamaCloud: {file_obj.id} ({upload_time:.2f}s)")

            # Step 2: Parse with advanced options
            parse_start = time.time()
            result = await self.client.parsing.parse(
                file_id=file_obj.id,
                tier="agentic",  # Highest quality parsing
                version="latest",  # Use latest parsing version

                # Advanced output options
                output_options={
                    "markdown": {
                        "annotate_links": True,  # Preserve URLs
                        "tables": {
                            "compact_markdown_tables": True,  # Better table formatting
                            "merge_continued_tables": True  # Merge multi-page tables
                        },
                        "inline_images": True  # Embed images in markdown
                    },
                    "images_to_save": ["embedded", "screenshot", "layout"],  # All image types
                    "spatial_text": {
                        "preserve_layout_alignment_across_pages": True,  # Better structure
                        "preserve_very_small_text": True  # Capture fine print
                    }
                },

                # Processing options
                processing_options={
                    "cost_optimizer": {
                        "enable": True  # Reduce API costs
                    }
                },

                # Expand to get all result fields
                expand=["text", "items", "markdown", "images_content_metadata"]
            )
            parse_time = time.time() - parse_start
            logger.success(f"LlamaCloud parsing completed ({parse_time:.2f}s)")

            # Step 3: Process results
            processing_start = time.time()

            # Extract text per page
            text_markdown = self._extract_markdown(result)
            text_plain = self._extract_plain_text(result)

            # Extract tables with bounding boxes from structured items
            tables = await self._extract_tables_from_items(result)

            # Extract Mermaid diagrams from markdown
            mermaid_diagrams = self._extract_mermaid_diagrams(text_markdown)

            # Extract images with presigned URLs
            images = await self._extract_images(result)

            processing_time = time.time() - processing_start
            logger.info(f"Result processing completed ({processing_time:.2f}s)")

            total_time = time.time() - start_time

            return {
                "text_markdown": text_markdown,
                "text_plain": text_plain,
                "images": images,
                "tables": tables,
                "mermaid_diagrams": mermaid_diagrams,
                "confidence_score": None,  # LlamaCloud doesn't provide this yet
                "upload_time": upload_time,
                "parse_time": parse_time,
                "processing_time": processing_time,
                "total_time": total_time,
                "extraction_method": "llamacloud_v2_agentic",
                "file_id": file_obj.id
            }

        except Exception as e:
            logger.error(f"LlamaCloud V2 extraction failed: {e}")
            raise

    def _extract_markdown(self, result) -> str:
        """Extract page-level markdown text"""
        try:
            if not hasattr(result, 'markdown') or not result.markdown:
                return ""

            markdown_text = ""
            for page in result.markdown.pages:
                markdown_text += f"\n<!-- Page {page.page_number} -->\n"
                markdown_text += page.markdown + "\n\n"

            return markdown_text.strip()
        except Exception as e:
            logger.warning(f"Failed to extract markdown: {e}")
            return ""

    def _extract_plain_text(self, result) -> str:
        """Extract page-level plain text"""
        try:
            if not hasattr(result, 'text') or not result.text:
                return ""

            plain_text = ""
            for page in result.text.pages:
                plain_text += f"\n--- Page {page.page_number} ---\n"
                plain_text += page.text + "\n\n"

            return plain_text.strip()
        except Exception as e:
            logger.warning(f"Failed to extract plain text: {e}")
            return ""

    async def _extract_tables_from_items(self, result) -> List[ExtractedTable]:
        """Extract tables from structured items with bounding boxes"""
        tables = []

        try:
            if not hasattr(result, 'items') or not result.items:
                logger.warning("No structured items in result")
                return tables

            table_counter = 0

            for page in result.items.pages:
                for item in page.items:
                    if isinstance(item, ItemsPageStructuredResultPageItemTableItem):
                        table_counter += 1

                        try:
                            # Extract table data
                            headers = []
                            rows = []

                            # First row is usually headers
                            if item.rows and len(item.rows) > 0:
                                first_row = item.rows[0]
                                if hasattr(first_row, 'cells'):
                                    headers = [cell.text if hasattr(cell, 'text') else str(cell)
                                             for cell in first_row.cells]

                                    # Remaining rows are data
                                    for row_idx in range(1, len(item.rows)):
                                        row_obj = item.rows[row_idx]
                                        if hasattr(row_obj, 'cells'):
                                            row_data = [cell.text if hasattr(cell, 'text') else str(cell)
                                                      for cell in row_obj.cells]
                                            rows.append(row_data)

                            # If no explicit headers, use all rows as data
                            if not headers and item.rows:
                                for row_obj in item.rows:
                                    if hasattr(row_obj, 'cells'):
                                        row_data = [cell.text if hasattr(cell, 'text') else str(cell)
                                                  for cell in row_obj.cells]
                                        rows.append(row_data)

                            # Extract bounding box if available
                            b_box = None
                            if hasattr(item, 'b_box') and item.b_box:
                                b_box = BoundingBox(
                                    x=item.b_box.x if hasattr(item.b_box, 'x') else 0,
                                    y=item.b_box.y if hasattr(item.b_box, 'y') else 0,
                                    width=item.b_box.width if hasattr(item.b_box, 'width') else 0,
                                    height=item.b_box.height if hasattr(item.b_box, 'height') else 0
                                )

                            # Generate HTML representation
                            html_content = self._rows_to_html(headers, rows)

                            table = ExtractedTable(
                                table_id=f"llamacloud_table_{table_counter}",
                                page_number=page.page_number,
                                html_content=html_content,
                                headers=headers,
                                rows=rows,
                                num_rows=len(rows),
                                num_cols=len(headers) if headers else (len(rows[0]) if rows else 0),
                                b_box=b_box,
                                extraction_source="llamacloud_v2"
                            )

                            tables.append(table)
                            logger.debug(f"Extracted table {table_counter} from page {page.page_number} with bbox")

                        except Exception as e:
                            logger.warning(f"Failed to process table {table_counter}: {e}")

            logger.info(f"Extracted {len(tables)} tables from LlamaCloud items")
            return tables

        except Exception as e:
            logger.error(f"Failed to extract tables from items: {e}")
            return tables

    def _rows_to_html(self, headers: List[str], rows: List[List[str]]) -> str:
        """Convert headers and rows to HTML table"""
        html = "<table>\n"

        if headers:
            html += "  <thead>\n    <tr>\n"
            for header in headers:
                html += f"      <th>{header}</th>\n"
            html += "    </tr>\n  </thead>\n"

        if rows:
            html += "  <tbody>\n"
            for row in rows:
                html += "    <tr>\n"
                for cell in row:
                    html += f"      <td>{cell}</td>\n"
                html += "    </tr>\n"
            html += "  </tbody>\n"

        html += "</table>"
        return html

    def _extract_mermaid_diagrams(self, markdown: str) -> List[DiagramDescription]:
        """Extract and parse Mermaid diagrams from markdown text"""
        try:
            mermaid_parser = MermaidParser()
            diagrams = mermaid_parser.extract_mermaid_diagrams(markdown)
            logger.info(f"Extracted {len(diagrams)} Mermaid diagrams from LlamaCloud markdown")
            return diagrams
        except Exception as e:
            logger.warning(f"Failed to extract Mermaid diagrams: {e}")
            return []

    async def _extract_images(self, result) -> List[ExtractedImage]:
        """Extract images from LlamaCloud result with presigned URLs"""
        images = []

        try:
            if not hasattr(result, 'images_content_metadata') or not result.images_content_metadata:
                logger.warning("No images_content_metadata in result")
                return images

            image_counter = 0

            for image_meta in result.images_content_metadata.images:
                try:
                    image_counter += 1

                    # Determine image type
                    import re
                    is_page_screenshot = re.match(r"^page_(\d+)\.jpg$", image_meta.filename) is not None
                    is_embedded = "embedded" in image_meta.filename.lower()
                    is_layout = "layout" in image_meta.filename.lower()

                    image_type = "screenshot" if is_page_screenshot else ("embedded" if is_embedded else "layout")

                    # Extract page number from filename
                    page_number = 0
                    if is_page_screenshot:
                        match = re.match(r"^page_(\d+)\.jpg$", image_meta.filename)
                        if match:
                            page_number = int(match.group(1))

                    # Download image if presigned URL available
                    image_path = None
                    image_base64 = None

                    if image_meta.presigned_url:
                        try:
                            # Download image
                            async with httpx.AsyncClient() as http_client:
                                response = await http_client.get(image_meta.presigned_url)
                                image_bytes = response.content

                            # Save to disk
                            img_filename = f"llamacloud_{image_meta.filename}"
                            img_path = self.output_dir / img_filename

                            with open(img_path, "wb") as img_file:
                                img_file.write(image_bytes)

                            # Convert to base64
                            image_base64 = base64.b64encode(image_bytes).decode("utf-8")
                            image_path = str(img_path)

                            logger.debug(f"Downloaded {image_meta.filename}, {image_meta.size_bytes} bytes")

                        except Exception as download_error:
                            logger.warning(f"Failed to download image {image_meta.filename}: {download_error}")

                    # Create ExtractedImage object
                    extracted_image = ExtractedImage(
                        image_id=f"llamacloud_img_{image_counter}",
                        page_number=page_number,
                        image_path=image_path or "",
                        image_base64=image_base64,
                        presigned_url=image_meta.presigned_url,
                        image_type=image_type,
                        width=None,  # Not provided in metadata
                        height=None
                    )

                    images.append(extracted_image)

                except Exception as e:
                    logger.warning(f"Failed to process image {image_counter}: {e}")

            logger.info(f"Extracted {len(images)} images from LlamaCloud")
            return images

        except Exception as e:
            logger.error(f"Failed to extract images: {e}")
            return images


async def extract_pdf_complete_v2(pdf_path: str, user_id: str, session_id: str) -> Dict[str, Any]:
    """
    Convenience function to extract complete PDF data using LlamaCloud V2 API

    Args:
        pdf_path: Path to PDF file
        user_id: User identifier
        session_id: Session identifier

    Returns:
        Complete extraction result dictionary
    """
    if not LLAMACLOUD_AVAILABLE:
        logger.error("LlamaCloud API not available, skipping V2 extraction")
        return {
            "text_markdown": "",
            "text_plain": "",
            "images": [],
            "tables": [],
            "mermaid_diagrams": [],
            "total_time": 0,
            "extraction_method": "llamacloud_v2_unavailable"
        }

    extractor = PDFExtractorV2(user_id, session_id)
    return await extractor.extract_pdf(pdf_path)
