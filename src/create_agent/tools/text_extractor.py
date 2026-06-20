"""Extract text from document files for the agent to process."""

from __future__ import annotations

import json

from create_agent.extraction.dispatcher import extract_text
from create_agent.tools.base import BaseTool, ToolResult


class TextExtractorTool(BaseTool):
    """Extract text content from a document file.

    Dispatches to the correct extractor based on file extension.
    """

    def __init__(
        self,
        supported_extensions: list[str] | None = None,
        max_chars: int = 50000,
        pdf_library: str = "pdfplumber",
    ) -> None:
        self._supported = supported_extensions or [".docx", ".pptx", ".pdf"]
        self._max_chars = max_chars
        self._pdf_library = pdf_library

    @property
    def name(self) -> str:
        return "extract_document_text"

    @property
    def description(self) -> str:
        return (
            "Extract the full text content from a document file (.docx, .pptx, .pdf). "
            "Call this when you need to READ a document's content before classifying, "
            "searching, or analyzing it. You can call this tool multiple times in parallel "
            "for different files."
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Absolute or relative path to the document file.",
                },
            },
            "required": ["file_path"],
        }

    def execute(self, input_data: dict) -> ToolResult:
        file_path = input_data["file_path"]

        try:
            text = extract_text(
                file_path=file_path,
                supported_extensions=self._supported,
                max_chars=self._max_chars,
                pdf_library=self._pdf_library,
            )
        except FileNotFoundError as e:
            return ToolResult.error(str(e))
        except ValueError as e:
            return ToolResult.error(str(e))
        except ImportError as e:
            return ToolResult.error(f"Missing dependency: {e}")
        except Exception as e:
            return ToolResult.error(f"Extraction failed for {file_path}: {e}")

        if not text.strip():
            return ToolResult.ok(
                json.dumps(
                    {
                        "file_path": file_path,
                        "extracted": False,
                        "warning": "No text could be extracted. The file may be "
                        "empty, image-only, or contain only scanned pages.",
                    },
                    ensure_ascii=False,
                )
            )

        return ToolResult.ok(
            json.dumps(
                {
                    "file_path": file_path,
                    "extracted": True,
                    "char_count": len(text),
                    "content": text,
                },
                ensure_ascii=False,
            )
        )
