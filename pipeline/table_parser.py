"""
HTML Table Parser
Parses HTML tables and extracts structured data (headers, rows, counts)
"""
from typing import List, Tuple
from bs4 import BeautifulSoup
from loguru import logger


class TableParser:
    """Parses HTML tables to extract structured data"""

    @staticmethod
    def parse_html_table(html_content: str) -> Tuple[List[str], List[List[str]], int, int]:
        """
        Parse HTML table to extract headers, rows, and counts

        Args:
            html_content: HTML table content

        Returns:
            Tuple of (headers, rows, num_rows, num_cols)
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            table = soup.find('table')

            if not table:
                logger.warning("No table tag found in HTML")
                return [], [], 0, 0

            headers = []
            rows = []

            # Extract headers from <thead> or first <tr> with <th> tags
            thead = table.find('thead')
            if thead:
                header_row = thead.find('tr')
                if header_row:
                    headers = [th.get_text(strip=True) for th in header_row.find_all('th')]
            else:
                # Try to find headers in first row
                first_row = table.find('tr')
                if first_row:
                    ths = first_row.find_all('th')
                    if ths:
                        headers = [th.get_text(strip=True) for th in ths]

            # Extract data rows from <tbody> or all <tr> tags
            tbody = table.find('tbody')
            tr_container = tbody if tbody else table

            for tr in tr_container.find_all('tr'):
                # Skip header rows
                if tr.find('th') and not headers:
                    headers = [th.get_text(strip=True) for th in tr.find_all('th')]
                    continue

                # Extract data cells
                tds = tr.find_all('td')
                if tds:
                    row_data = [td.get_text(strip=True) for td in tds]
                    rows.append(row_data)

            # Calculate dimensions
            num_rows = len(rows)
            num_cols = len(headers) if headers else (len(rows[0]) if rows else 0)

            # If no explicit headers but we have rows, use first row as headers
            if not headers and rows:
                headers = [f"Column {i+1}" for i in range(num_cols)]

            return headers, rows, num_rows, num_cols

        except Exception as e:
            logger.error(f"Failed to parse HTML table: {e}")
            return [], [], 0, 0

    @staticmethod
    def extract_table_caption(html_content: str) -> str:
        """
        Extract table caption if present

        Args:
            html_content: HTML table content

        Returns:
            Caption text or empty string
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            table = soup.find('table')

            if not table:
                return ""

            caption = table.find('caption')
            return caption.get_text(strip=True) if caption else ""

        except Exception as e:
            logger.error(f"Failed to extract table caption: {e}")
            return ""

    @staticmethod
    def detect_table_page_from_context(html_content: str, full_markdown: str) -> int:
        """
        Try to detect which page a table appears on by finding it in the full markdown

        Args:
            html_content: HTML table content
            full_markdown: Full markdown text with page markers

        Returns:
            Page number (0 if cannot determine)
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            table = soup.find('table')

            if not table:
                return 0

            # Extract some unique text from the table
            first_row = table.find('tr')
            if not first_row:
                return 0

            # Get first few cells as signature
            cells = first_row.find_all(['th', 'td'])
            signature = " ".join([cell.get_text(strip=True) for cell in cells[:3]])

            if not signature:
                return 0

            # Find this signature in the markdown and look for page markers
            import re

            # Split markdown by common page markers
            page_pattern = r'(?:Page\s+(\d+)|---\s*Page\s+(\d+)\s*---|<!-- Page (\d+) -->)'
            matches = list(re.finditer(page_pattern, full_markdown, re.IGNORECASE))

            # Find position of signature in markdown
            signature_pos = full_markdown.find(signature)

            if signature_pos == -1:
                return 0

            # Find the last page marker before the signature
            current_page = 0
            for match in matches:
                marker_pos = match.start()
                if marker_pos > signature_pos:
                    break
                # Extract page number from any of the groups
                page_num = match.group(1) or match.group(2) or match.group(3)
                if page_num:
                    current_page = int(page_num)

            return current_page

        except Exception as e:
            logger.debug(f"Could not detect table page from context: {e}")
            return 0


def parse_table_from_html(html_content: str) -> Tuple[List[str], List[List[str]], int, int]:
    """
    Convenience function to parse HTML table

    Args:
        html_content: HTML table content

    Returns:
        Tuple of (headers, rows, num_rows, num_cols)
    """
    parser = TableParser()
    return parser.parse_html_table(html_content)
