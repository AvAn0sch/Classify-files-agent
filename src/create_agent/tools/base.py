"""Abstract base classes for agent tools."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolResult:
    """Result returned by a tool execution.

    Attributes:
        content: The tool's output as a string (may be JSON).
        is_error: Whether the tool encountered an error.
    """

    content: str
    is_error: bool = False

    @classmethod
    def ok(cls, content: str) -> "ToolResult":
        """Create a successful result."""
        return cls(content=content, is_error=False)

    @classmethod
    def error(cls, content: str) -> "ToolResult":
        """Create an error result."""
        return cls(content=content, is_error=True)


class BaseTool(ABC):
    """Abstract base class for all agent tools.

    Each tool must define: name, description, input_schema, and execute().
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique tool identifier (snake_case). Used for tool lookup and API calls."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of what the tool does AND when to use it.

        Follow Claude best practice: state the function and the trigger condition.
        Example: "Extract text from a document. Call this when you need to read
        document content before classifying, searching, or analyzing it."
        """
        ...

    @property
    @abstractmethod
    def input_schema(self) -> dict[str, Any]:
        """JSON Schema describing the tool's input parameters.

        Must include: type, properties, required (if any).
        Example:
        {
            "type": "object",
            "properties": {
                "folder": {"type": "string", "description": "Path to scan"}
            },
            "required": ["folder"]
        }
        """
        ...

    @abstractmethod
    def execute(self, input_data: dict[str, Any]) -> ToolResult:
        """Execute the tool with the given input parameters.

        Args:
            input_data: Dictionary matching the tool's input_schema.

        Returns:
            ToolResult with the execution output or error.
        """
        ...

    def to_claude_format(self) -> dict[str, Any]:
        """Convert to Anthropic API tool definition format."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }
