"""Classify documents using OpenAI-compatible structured output.

This tool is a HYBRID: from the agent's perspective it's a normal tool,
but internally it uses the LLM API with structured output (JSON schema)
to batch-classify documents with guaranteed format compliance.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from create_agent.tools.base import BaseTool, ToolResult

if TYPE_CHECKING:
    from openai import OpenAI

CLASSIFICATION_SCHEMA = {
    "type": "object",
    "properties": {
        "classifications": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the document being classified.",
                    },
                    "category": {
                        "type": "string",
                        "description": "The best-fit category for this document.",
                    },
                    "confidence": {
                        "type": "string",
                        "enum": ["high", "medium", "low"],
                        "description": "How confident the classification is.",
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "Brief reason for the classification (1 sentence).",
                    },
                },
                "required": ["file_path", "category", "confidence", "reasoning"],
            },
        },
    },
    "required": ["classifications"],
}


class ClassifyDocumentsTool(BaseTool):
    """Classify documents into user-defined categories using LLM structured output.

    Makes internal LLM API calls with JSON schema response_format to batch-classify
    documents. The agent sees this as a single tool call, but internally it
    batches documents, calls the LLM with a JSON schema, and returns structured results.
    """

    def __init__(
        self,
        client: "OpenAI",
        model: str,
        batch_size: int = 10,
        max_chars_per_doc: int = 8000,
    ) -> None:
        self._client = client
        self._model = model
        self._batch_size = batch_size
        self._max_chars_per_doc = max_chars_per_doc

    @property
    def name(self) -> str:
        return "classify_documents"

    @property
    def description(self) -> str:
        return (
            "Classify documents into user-defined categories. "
            "Call this AFTER extracting text from all documents. "
            "Provide the document texts (from extract_document_text results) "
            "and the list of categories to classify into. "
            "Returns classifications with confidence levels and reasoning."
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "documents": {
                    "type": "array",
                    "description": "List of documents with their extracted text.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "file_path": {"type": "string"},
                            "filename": {"type": "string"},
                            "content": {
                                "type": "string",
                                "description": "Extracted text (may be truncated).",
                            },
                        },
                        "required": ["file_path", "content"],
                    },
                },
                "categories": {
                    "type": "array",
                    "description": "List of category names to classify into.",
                    "items": {"type": "string"},
                },
            },
            "required": ["documents", "categories"],
        }

    def execute(self, input_data: dict) -> ToolResult:
        documents = input_data.get("documents", [])
        categories = input_data.get("categories", [])

        if not documents:
            return ToolResult.error("No documents provided for classification.")
        if not categories:
            return ToolResult.error("No categories provided for classification.")
        if len(categories) > 30:
            return ToolResult.error("Too many categories (max 30).")

        all_classifications: list[dict] = []

        for i in range(0, len(documents), self._batch_size):
            batch = documents[i : i + self._batch_size]
            try:
                batch_results = self._classify_batch(batch, categories)
                all_classifications.extend(batch_results)
            except Exception as e:
                for doc in batch:
                    all_classifications.append(
                        {
                            "file_path": doc["file_path"],
                            "category": "未分类",
                            "confidence": "low",
                            "reasoning": f"Classification failed: {e}",
                        }
                    )

        return ToolResult.ok(
            json.dumps(
                {"classifications": all_classifications},
                ensure_ascii=False,
                indent=2,
            )
        )

    def _classify_batch(self, documents: list[dict], categories: list[str]) -> list[dict]:
        """Internal call to LLM using structured output (JSON schema)."""
        doc_sections: list[str] = []
        category_list = ", ".join(categories)

        for doc in documents:
            content = doc.get("content", "")[: self._max_chars_per_doc]
            doc_sections.append(
                f"--- FILE: {doc['file_path']} ---\n"
                f"Filename: {doc.get('filename', '')}\n"
                f"Content:\n{content}\n"
            )

        doc_text = "\n".join(doc_sections)

        response = self._client.chat.completions.create(
            model=self._model,
            max_tokens=4000,
            temperature=0.0,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a precise document classifier. Classify each document into "
                        "exactly ONE of the provided categories. Consider: main topic, "
                        "key terminology, document type, and intended audience. "
                        "If a document truly does not fit any category, use '未分类' (Unclassified). "
                        "Always provide a 1-sentence reasoning for each classification."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Categories: {category_list}\n\n"
                        f"Classify each document below:\n\n{doc_text}"
                    ),
                },
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "classifications",
                    "schema": CLASSIFICATION_SCHEMA,
                },
            },
        )

        result_text = response.choices[0].message.content
        parsed = json.loads(result_text)
        return parsed.get("classifications", [])
