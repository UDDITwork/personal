"""
Mermaid Diagram Parser
Extracts and parses Mermaid code blocks from markdown text
Converts them into structured DiagramDescription objects
"""
import re
from typing import List, Dict, Any, Optional
from loguru import logger

from .models import DiagramDescription


class MermaidParser:
    """Parses Mermaid code blocks and converts them to DiagramDescription objects"""

    def __init__(self):
        self.diagram_id_counter = 0

    def extract_mermaid_diagrams(self, markdown_text: str) -> List[DiagramDescription]:
        """
        Extract all Mermaid code blocks from markdown text and convert to DiagramDescription

        Args:
            markdown_text: Full markdown text containing mermaid code blocks

        Returns:
            List of DiagramDescription objects
        """
        diagrams = []

        # Find all mermaid code blocks
        mermaid_pattern = r'```mermaid\s+(.*?)```'
        matches = re.findall(mermaid_pattern, markdown_text, re.DOTALL | re.IGNORECASE)

        logger.info(f"Found {len(matches)} Mermaid code blocks in markdown")

        for idx, mermaid_code in enumerate(matches):
            try:
                diagram = self._parse_mermaid_code(mermaid_code, idx + 1)
                if diagram:
                    diagrams.append(diagram)
                    logger.debug(f"Parsed Mermaid diagram {idx + 1}: {diagram.diagram_type}")
            except Exception as e:
                logger.warning(f"Failed to parse Mermaid diagram {idx + 1}: {e}")

        return diagrams

    def _parse_mermaid_code(self, mermaid_code: str, diagram_number: int) -> Optional[DiagramDescription]:
        """
        Parse a single Mermaid code block

        Args:
            mermaid_code: The mermaid code string
            diagram_number: Sequential diagram number

        Returns:
            DiagramDescription object or None if parsing fails
        """
        # Determine diagram type from first line
        diagram_type = self._detect_diagram_type(mermaid_code)

        # Extract elements based on diagram type
        if diagram_type == "flowchart":
            return self._parse_flowchart(mermaid_code, diagram_number)
        elif diagram_type == "graph":
            return self._parse_graph(mermaid_code, diagram_number)
        elif diagram_type == "sequence":
            return self._parse_sequence_diagram(mermaid_code, diagram_number)
        elif diagram_type == "block_diagram":
            return self._parse_block_diagram(mermaid_code, diagram_number)
        else:
            # Generic parsing for unknown types
            return self._parse_generic(mermaid_code, diagram_number, diagram_type)

    def _detect_diagram_type(self, mermaid_code: str) -> str:
        """Detect the type of Mermaid diagram"""
        first_line = mermaid_code.strip().split('\n')[0].lower()

        if 'flowchart' in first_line:
            return "flowchart"
        elif 'graph' in first_line:
            return "graph"
        elif 'sequencediagram' in first_line or 'sequence' in first_line:
            return "sequence"
        elif 'block' in first_line:
            return "block_diagram"
        elif 'classDiagram' in first_line:
            return "class_diagram"
        elif 'stateDiagram' in first_line:
            return "state_diagram"
        elif 'erDiagram' in first_line:
            return "er_diagram"
        else:
            return "other"

    def _parse_flowchart(self, mermaid_code: str, diagram_number: int) -> DiagramDescription:
        """Parse a flowchart diagram"""
        lines = mermaid_code.strip().split('\n')[1:]  # Skip first line (flowchart declaration)

        outermost_elements = []
        shape_mapping = {}
        connections = []
        all_text_labels = []
        nested_components = {}

        for line in lines:
            line = line.strip()
            if not line or line.startswith('%%'):  # Skip empty lines and comments
                continue

            # Parse subgraph (nested components)
            if line.startswith('subgraph'):
                subgraph_match = re.match(r'subgraph\s+(\w+)\s*\[(.*?)\]', line)
                if subgraph_match:
                    subgraph_id = subgraph_match.group(1)
                    subgraph_label = subgraph_match.group(2)
                    outermost_elements.append(subgraph_label)
                    all_text_labels.append(subgraph_label)
                    nested_components[subgraph_label] = {"children": []}
                continue

            if line == 'end':
                continue

            # Parse node definitions: A[Label] or A(Label) or A{Label}
            node_pattern = r'(\w+)([\[\(\{<])([^\]\)\}>]+)([\]\)\}>])'
            node_matches = re.findall(node_pattern, line)

            for node_id, open_bracket, label, close_bracket in node_matches:
                shape_type = self._detect_shape_type(open_bracket, close_bracket)
                shape_mapping[node_id] = label
                all_text_labels.append(label)

                # Only add to outermost_elements if not already there
                if label not in [elem for elem in outermost_elements]:
                    outermost_elements.append(label)

            # Parse connections: A --> B or A --> |label| B
            connection_pattern = r'(\w+)\s*(-->|<-->|-.->|===>)\s*(?:\|([^\|]+)\|\s*)?(\w+)'
            connection_matches = re.findall(connection_pattern, line)

            for from_node, arrow, label, to_node in connection_matches:
                from_label = shape_mapping.get(from_node, from_node)
                to_label = shape_mapping.get(to_node, to_node)

                direction = "bidirectional" if "<-->" in arrow else "unidirectional"

                connection = {
                    "from": from_label,
                    "to": to_label,
                    "direction": direction,
                    "label": label.strip() if label else ""
                }
                connections.append(connection)

                if label:
                    all_text_labels.append(label.strip())

        description_summary = f"Flowchart diagram with {len(outermost_elements)} elements and {len(connections)} connections"

        return DiagramDescription(
            image_id=f"mermaid_diagram_{diagram_number}",
            is_diagram=True,
            diagram_type="flowchart",
            outermost_elements=outermost_elements,
            shape_mapping=shape_mapping,
            nested_components=nested_components,
            connections=connections,
            all_text_labels=all_text_labels,
            description_summary=description_summary
        )

    def _parse_graph(self, mermaid_code: str, diagram_number: int) -> DiagramDescription:
        """Parse a graph diagram (similar to flowchart)"""
        # Graph diagrams use similar syntax to flowcharts
        return self._parse_flowchart(mermaid_code, diagram_number)

    def _parse_sequence_diagram(self, mermaid_code: str, diagram_number: int) -> DiagramDescription:
        """Parse a sequence diagram"""
        lines = mermaid_code.strip().split('\n')[1:]  # Skip first line

        participants = []
        connections = []
        all_text_labels = []

        for line in lines:
            line = line.strip()
            if not line or line.startswith('%%'):
                continue

            # Parse participant declarations
            participant_match = re.match(r'participant\s+(\w+)(?:\s+as\s+(.+))?', line)
            if participant_match:
                participant_id = participant_match.group(1)
                participant_label = participant_match.group(2) if participant_match.group(2) else participant_id
                participants.append(participant_label)
                all_text_labels.append(participant_label)
                continue

            # Parse messages: A->>B: Message or A-->>B: Message
            message_pattern = r'(\w+)\s*(->>|-->>|->|-->)\s*(\w+)\s*:\s*(.+)'
            message_match = re.match(message_pattern, line)

            if message_match:
                from_participant = message_match.group(1)
                arrow = message_match.group(2)
                to_participant = message_match.group(3)
                message = message_match.group(4)

                connections.append({
                    "from": from_participant,
                    "to": to_participant,
                    "direction": "unidirectional",
                    "label": message
                })
                all_text_labels.append(message)

        description_summary = f"Sequence diagram with {len(participants)} participants and {len(connections)} interactions"

        return DiagramDescription(
            image_id=f"mermaid_diagram_{diagram_number}",
            is_diagram=True,
            diagram_type="sequence",
            outermost_elements=participants,
            shape_mapping={},
            nested_components={},
            connections=connections,
            all_text_labels=all_text_labels,
            description_summary=description_summary
        )

    def _parse_block_diagram(self, mermaid_code: str, diagram_number: int) -> DiagramDescription:
        """Parse a block diagram"""
        # Block diagrams are similar to flowcharts
        return self._parse_flowchart(mermaid_code, diagram_number)

    def _parse_generic(self, mermaid_code: str, diagram_number: int, diagram_type: str) -> DiagramDescription:
        """Generic parser for unknown Mermaid diagram types"""
        lines = mermaid_code.strip().split('\n')

        # Extract all text labels (anything in quotes or brackets)
        all_text_labels = []
        label_pattern = r'[\[\(\{<"]([^\]\)\}>\"]+)[\]\)\}>"]'
        for line in lines:
            matches = re.findall(label_pattern, line)
            all_text_labels.extend(matches)

        description_summary = f"{diagram_type} diagram with {len(lines)} lines of code"

        return DiagramDescription(
            image_id=f"mermaid_diagram_{diagram_number}",
            is_diagram=True,
            diagram_type=diagram_type,
            outermost_elements=[],
            shape_mapping={},
            nested_components={},
            connections=[],
            all_text_labels=all_text_labels,
            description_summary=description_summary
        )

    def _detect_shape_type(self, open_bracket: str, close_bracket: str) -> str:
        """Detect shape type from bracket notation"""
        bracket_map = {
            ('(', ')'): "rounded_rectangle",
            ('[', ']'): "rectangle",
            ('{', '}'): "diamond",
            ('<', '>'): "asymmetric",
            ('((', '))'): "circle",
            ('[(', ')]'): "stadium",
            ('[[', ']]'): "subroutine"
        }
        return bracket_map.get((open_bracket, close_bracket), "rectangle")


def extract_mermaid_diagrams_from_markdown(markdown_text: str) -> List[DiagramDescription]:
    """
    Convenience function to extract Mermaid diagrams from markdown

    Args:
        markdown_text: Full markdown text

    Returns:
        List of DiagramDescription objects
    """
    parser = MermaidParser()
    return parser.extract_mermaid_diagrams(markdown_text)
