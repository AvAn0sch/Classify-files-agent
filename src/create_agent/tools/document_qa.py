"""Document Q&A tool — answer questions based on document content.

This tool is a HYBRID: from the agent's perspective it's a normal tool,
but internally it extracts text from all documents, concatenates them into
a context window, and calls Claude to answer the user's question.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from create_agent.extraction.dispatcher import extract_text
from create_agent.tools.base import BaseTool, ToolResult

if TYPE_CHECKING:
    import anthropic


class DocumentQATool(BaseTool):
    """Answer questions about document content using Claude.

    Scans a folder for documents, extracts their text, concatenates them
    into a context window, and calls Claude to answer the user's question
    with file references.
    """

    def __init__(
        self,
        client: "anthropic.Anthropic",
        model: str,
        supported_extensions: list[str] | None = None,
        max_chars_per_doc: int = 50000,
        pdf_library: str = "pdfplumber",
    ) -> None:
        self._client = client
        self._model = model
        self._supported = supported_extensions or [".docx", ".pptx", ".pdf"]
        self._max_chars_per_doc = max_chars_per_doc
        self._pdf_library = pdf_library

    @property
    def name(self) -> str:
        return "search_documents"

    @property
    def description(self) -> str:
        return (
            "Search through document contents and answer a question based on them. "
            "Call this when the user asks a specific question about their documents. "
            "Provide the folder path and the question. Returns an answer with "
            "references to which documents the information came from."
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "folder": {
                    "type": "string",
                    "description": "Path to the folder containing documents to search.",
                },
                "question": {
                    "type": "string",
                    "description": "The question to answer based on document content.",
                },
            },
            "required": ["folder", "question"],
        }

    def execute(self, input_data: dict) -> ToolResult:
        folder = input_data["folder"]
        question = input_data["question"]

        path = Path(folder).resolve()
        if not path.exists():
            return ToolResult.error(f"Folder not found: {folder}")
        if not path.is_dir():
            return ToolResult.error(f"Not a folder: {folder}")

        # Scan for documents
        doc_files: list[Path] = []
        for f in path.rglob("*"):
            if f.is_file() and f.suffix.lower() in self._supported:
                if not f.name.startswith("~$"):
                    doc_files.append(f)
        doc_files.sort(key=lambda x: x.name)

        if not doc_files:
            return ToolResult.error(
                f"No supported documents found in {path}. "
                f"Supported: {', '.join(self._supported)}"
            )

        # Extract text from all documents
        doc_texts: list[str] = []
        extraction_errors: list[str] = []

        for doc_path in doc_files:
            try:
                text = extract_text(
                    file_path=doc_path,
                    supported_extensions=self._supported,
                    max_chars=self._max_chars_per_doc,
                    pdf_library=self._pdf_library,
                )
                if text.strip():
                    doc_texts.append(
                        f"=== DOCUMENT: {doc_path.name} ===\n"
                        f"Path: {doc_path}\n\n{text}\n"
                    )
            except Exception as e:
                extraction_errors.append(f"{doc_path.name}: {e}")

        if not doc_texts:
            return ToolResult.error(
                "Could not extract text from any documents. "
                f"Errors: {', '.join(extraction_errors)}"
            )

        # Concatenate and query
        combined_text = "\n\n".join(doc_texts)

        # Truncate if too long (leaving room for system prompt + question + answer)
        max_context = 180000  # ~180K chars to leave room for Claude's max context
        if len(combined_text) > max_context:
            combined_text = (
                combined_text[:max_context]
                + "\n\n[... content truncated due to length]"
            )

        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=4000,
                system=(
                    "You are a precise document analyst. Answer questions based "
                    "ONLY on the provided document content. If the answer cannot "
                    "be found in the documents, say so clearly. Always cite which "
                    "document(s) your answer comes from. Be concise and factual."
                ),
                messages=[
                    {
                        "role": "user",
                        "content": (
                            f"Question: {question}\n\n"
                            f"Documents:\n\n{combined_text}\n\n"
                            f"Answer the question based ONLY on the documents above. "
                            f"Include document name references."
                        ),
                    }
                ],
            )

            answer = response.content[0].text

            return ToolResult.ok(
                json.dumps(
                    {
                        "question": question,
                        "documents_searched": len(doc_files),
                        "extraction_errors": extraction_errors,
                        "answer": answer,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )

        except Exception as e:
            return ToolResult.error(f"Document Q&A failed: {e}")
