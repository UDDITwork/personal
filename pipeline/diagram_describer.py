"""
Diagram Description Module
Uses Google Gemini 2.5 Flash Vision API to describe diagrams in structured format
"""
import asyncio
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from loguru import logger

try:
    from google import genai
except ImportError:
    logger.error("google-genai not installed. Run: pip install google-genai")
    raise

from .models import ExtractedImage, DiagramDescription
from config import settings


# Exact prompt as specified for patent diagram analysis
DIAGRAM_DESCRIPTION_PROMPT = """You are a technical patent diagram analyzer. Given this image from a patent document, provide a STRUCTURED description.

RULES:
1. Identify ALL outermost blocks/shapes in the diagram
2. Map each shape type to its meaning:
   - Rectangle/Box = component/module/block
   - Cylinder = database/storage
   - Cloud shape = network/WAN/internet
   - Diamond = decision point
   - Rounded rectangle = process/service
   - Parallelogram = input/output
   - Circle/Oval = start/end/terminal
3. For EVERY block, list what is inside it (nested components). Go as deep as the nesting goes.
4. For EVERY arrow/line connection:
   - State the FROM element
   - State the TO element
   - State if unidirectional (→) or bidirectional (↔)
   - State any label on the arrow
5. List ALL text/labels visible inside any shape or on any arrow
6. If there are numbered steps or sequences, preserve the order

OUTPUT FORMAT (strict JSON):
{
    "outermost_elements": ["element1", "element2"],
    "shape_mapping": {"shape_type": "element_name"},
    "nested_components": {
        "parent_element": {
            "children": ["child1", "child2"],
            "child_details": {
                "child1": {"children": ["grandchild1"]}
            }
        }
    },
    "connections": [
        {"from": "A", "to": "B", "direction": "unidirectional", "label": "data flow"},
        {"from": "C", "to": "D", "direction": "bidirectional", "label": ""}
    ],
    "all_text_labels": ["label1", "label2"],
    "diagram_type": "block_diagram | flowchart | architecture | sequence | cross_section | other",
    "description_summary": "One paragraph describing what this diagram shows"
}

If the image is NOT a diagram (just a photo/screenshot/logo), return:
{
    "is_diagram": false,
    "image_type": "photo | screenshot | logo | chart | graph",
    "description_summary": "What the image shows"
}

Be exhaustive. Miss NOTHING. Every shape, every arrow, every label."""


class DiagramDescriber:
    """Handles diagram description using Gemini Vision API"""

    def __init__(self):
        # Initialize Gemini client
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model = "gemini-2.5-flash"

    async def describe_diagram(self, image: ExtractedImage) -> Optional[DiagramDescription]:
        """
        Describe a single diagram/image using Gemini Vision

        Args:
            image: ExtractedImage object with path to image file

        Returns:
            DiagramDescription object or None if description fails
        """
        try:
            logger.info(f"Describing diagram: {image.image_id}")
            start_time = time.time()

            # Read image file
            image_path = Path(image.image_path)
            if not image_path.exists():
                logger.error(f"Image file not found: {image_path}")
                return None

            with open(image_path, "rb") as f:
                image_bytes = f.read()

            # Determine MIME type from file extension
            mime_type = self._get_mime_type(image_path.suffix)

            # Call Gemini Vision API
            response = await self._call_gemini_vision(image_bytes, mime_type)

            # Parse JSON response
            description_data = self._parse_gemini_response(response)

            if not description_data:
                logger.warning(f"Failed to parse Gemini response for {image.image_id}")
                return None

            # Create DiagramDescription object
            diagram_desc = DiagramDescription(
                image_id=image.image_id,
                is_diagram=description_data.get("is_diagram", True),
                diagram_type=description_data.get("diagram_type"),
                outermost_elements=description_data.get("outermost_elements", []),
                shape_mapping=description_data.get("shape_mapping", {}),
                nested_components=description_data.get("nested_components", {}),
                connections=description_data.get("connections", []),
                all_text_labels=description_data.get("all_text_labels", []),
                description_summary=description_data.get("description_summary", ""),
                image_type=description_data.get("image_type")
            )

            processing_time = time.time() - start_time
            logger.success(f"Diagram {image.image_id} described in {processing_time:.2f}s")

            return diagram_desc

        except Exception as e:
            logger.error(f"Failed to describe diagram {image.image_id}: {e}")
            return None

    async def describe_multiple_diagrams(
        self,
        images: List[ExtractedImage],
        max_concurrent: int = 5
    ) -> List[DiagramDescription]:
        """
        Describe multiple diagrams concurrently (with rate limiting)

        Args:
            images: List of ExtractedImage objects
            max_concurrent: Maximum concurrent API calls to Gemini

        Returns:
            List of DiagramDescription objects
        """
        logger.info(f"Starting batch description for {len(images)} images")

        # Create semaphore for rate limiting
        semaphore = asyncio.Semaphore(max_concurrent)

        async def describe_with_semaphore(img: ExtractedImage) -> Optional[DiagramDescription]:
            async with semaphore:
                return await self.describe_diagram(img)

        # Run all descriptions concurrently with rate limiting
        tasks = [describe_with_semaphore(img) for img in images]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out None results and exceptions
        descriptions = []
        for result in results:
            if isinstance(result, DiagramDescription):
                descriptions.append(result)
            elif isinstance(result, Exception):
                logger.error(f"Diagram description failed: {result}")

        logger.info(f"Successfully described {len(descriptions)}/{len(images)} diagrams")
        return descriptions

    async def _call_gemini_vision(self, image_bytes: bytes, mime_type: str) -> str:
        """
        Call Gemini Vision API with image and prompt

        Args:
            image_bytes: Image file bytes
            mime_type: MIME type of image

        Returns:
            Response text from Gemini
        """
        try:
            # Prepare content for Gemini API
            contents = [
                {
                    "mime_type": mime_type,
                    "data": image_bytes
                },
                DIAGRAM_DESCRIPTION_PROMPT
            ]

            # Make async API call
            response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=contents,
                config={
                    "temperature": 0.1,  # Low temperature for consistent structured output
                    "response_mime_type": "application/json"  # Request JSON response
                }
            )

            return response.text

        except Exception as e:
            logger.error(f"Gemini API call failed: {e}")
            # Retry once after a short delay
            logger.info("Retrying Gemini API call...")
            await asyncio.sleep(2)

            try:
                response = await self.client.aio.models.generate_content(
                    model=self.model,
                    contents=contents,
                    config={
                        "temperature": 0.1,
                        "response_mime_type": "application/json"
                    }
                )
                return response.text
            except Exception as retry_error:
                logger.error(f"Gemini API retry failed: {retry_error}")
                raise

    def _parse_gemini_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """
        Parse JSON response from Gemini

        Args:
            response_text: Raw text response from Gemini

        Returns:
            Parsed JSON dictionary or None if parsing fails
        """
        try:
            # Try to parse as JSON directly
            data = json.loads(response_text)
            return data

        except json.JSONDecodeError:
            # Sometimes Gemini returns JSON wrapped in markdown code blocks
            # Try to extract JSON from markdown code blocks
            import re

            # Look for JSON in code blocks
            json_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
            matches = re.findall(json_pattern, response_text, re.DOTALL)

            if matches:
                try:
                    data = json.loads(matches[0])
                    return data
                except json.JSONDecodeError:
                    pass

            # Try to find any JSON object in the response
            json_object_pattern = r'\{.*\}'
            matches = re.findall(json_object_pattern, response_text, re.DOTALL)

            if matches:
                for match in matches:
                    try:
                        data = json.loads(match)
                        return data
                    except json.JSONDecodeError:
                        continue

            logger.error(f"Failed to parse JSON from Gemini response: {response_text[:500]}")
            return None

    def _get_mime_type(self, file_extension: str) -> str:
        """Get MIME type from file extension"""
        mime_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".bmp": "image/bmp",
            ".webp": "image/webp",
            ".tiff": "image/tiff",
            ".tif": "image/tiff"
        }
        return mime_types.get(file_extension.lower(), "image/png")


async def describe_diagrams_batch(images: List[ExtractedImage]) -> List[DiagramDescription]:
    """
    Convenience function to describe multiple diagrams

    Args:
        images: List of ExtractedImage objects

    Returns:
        List of DiagramDescription objects
    """
    describer = DiagramDescriber()
    return await describer.describe_multiple_diagrams(images)
