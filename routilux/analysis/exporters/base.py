"""
Base formatter class for analysis results.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Union


class BaseFormatter(ABC):
    """Base class for all analysis formatters.

    Formatters convert analysis JSON results into various output formats
    such as Markdown, D2, HTML, etc.
    """

    @abstractmethod
    def format(self, data: Dict[str, Any]) -> str:
        """Format analysis data into output string.

        Args:
            data: Analysis result dictionary.

        Returns:
            Formatted string output.
        """
        pass

    def save(self, data: Dict[str, Any], output_path: Union[str, Path]) -> None:
        """Save formatted output to file.

        Args:
            data: Analysis result dictionary.
            output_path: Path to output file.

        Raises:
            OSError: If directory creation fails or file cannot be written.
            ValueError: If formatter returns None.
        """
        output_path = Path(output_path)

        # MEDIUM fix: Add error handling for directory creation and file writing
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise OSError(f"Failed to create output directory {output_path.parent}: {e}")

        formatted_content = self.format(data)

        # MEDIUM fix: Validate formatted_content is not None
        if formatted_content is None:
            raise ValueError(f"Formatter {self.__class__.__name__} returned None for format()")

        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(formatted_content)
        except OSError as e:
            raise OSError(f"Failed to write to output file {output_path}: {e}")
