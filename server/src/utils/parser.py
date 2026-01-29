"""
Markdown tag-based output parsing module - based on project_reference.md
"""

import re
from typing import Dict, Any
from ..models import ParsedNodeOutput

class ResultParser:
    """
    Class for parsing LLM output results
    Extracts output based on markdown tags
    """

    def parse_node_output(self, raw_output: str) -> ParsedNodeOutput:
        """
        Parse LLM raw output to extract description and output

        Args:
            raw_output: Raw output string from LLM

        Returns:
            ParsedNodeOutput: Parsed description and output

        Raises:
            ValueError: On parsing failure
        """

        try:
            # Find <output>...</output> tag pattern
            # Use [\s\S]*? for safe multiline text matching
            output_patterns = [
                r'<output>([\s\S]*?)</output>',
                r'<출력>([\s\S]*?)</출력>'
            ]

            output_match = None
            for pattern in output_patterns:
                output_match = re.search(pattern, raw_output, re.IGNORECASE)
                if output_match:
                    break

            if output_match:
                # Extract output tag content
                output = output_match.group(1).strip()

                # description is full text (not used in streaming)
                description = raw_output.strip()

                return ParsedNodeOutput(
                    description=description,
                    output=output
                )
            else:
                # Use full text as output if no output tag
                return ParsedNodeOutput(
                    description=raw_output.strip(),
                    output=raw_output.strip()
                )

        except Exception as e:
            # Other errors
            raise ValueError(f"Result parsing failed: {str(e)}")

    def validate_output_format(self, raw_output: str) -> Dict[str, Any]:
        """
        Validate output format (markdown tag based)

        Args:
            raw_output: Output string to validate

        Returns:
            Dict: Validation result {"valid": bool, "errors": List[str]}
        """

        errors = []

        try:
            # Check for <output>...</output> tag pattern
            output_patterns = [
                r'<output>([\s\S]*?)</output>',
                r'<출력>([\s\S]*?)</출력>'
            ]

            output_match = None
            for pattern in output_patterns:
                output_match = re.search(pattern, raw_output, re.IGNORECASE)
                if output_match:
                    break

            if not output_match:
                errors.append("Missing <output>...</output> or <출력>...</출력> tags")
            else:
                output_content = output_match.group(1).strip()
                if not output_content:
                    errors.append("Empty content in <output> tags")

        except Exception as e:
            errors.append(f"Validation error: {str(e)}")

        return {
            "valid": len(errors) == 0,
            "errors": errors
        }