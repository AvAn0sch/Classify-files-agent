"""Scan folders for supported document files."""

from __future__ import annotations

import json
import os
from pathlib import Path

from create_agent.tools.base import BaseTool, ToolResult


class FileScannerTool(BaseTool):
    """Scan a folder recursively for supported document files.

    Returns a JSON list with file metadata: path, name, extension, size.
    """

    def __init__(self, supported_extensions: list[str] | None = None) -> None:
        self._supported = supported_extensions or [".docx", ".pptx", ".pdf"]

    @property
    def name(self) -> str:
        return "scan_folder"

    @property
    def description(self) -> str:
        return (
            "Scan a folder for document files (.docx, .pptx, .pdf). "
            "Call this FIRST when you need to discover what documents exist in a folder. "
            "Returns a list of files with paths, names, extensions, and sizes."
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "folder": {
                    "type": "string",
                    "description": "Absolute or relative path to the folder to scan.",
                },
                "recursive": {
                    "type": "boolean",
                    "description": "Whether to scan sub-folders recursively. Default: true.",
                },
            },
            "required": ["folder"],
        }

    def execute(self, input_data: dict) -> ToolResult:
        folder = input_data.get("folder", ".")
        recursive = input_data.get("recursive", True)
        path = Path(folder).resolve()

        if not path.exists():
            return ToolResult.error(f"Folder not found: {folder}")
        if not path.is_dir():
            return ToolResult.error(f"Not a folder: {folder}")

        files: list[dict] = []
        extensions = tuple(self._supported)

        iterator = path.rglob("*") if recursive else path.glob("*")
        for f in iterator:
            if f.is_file() and f.suffix.lower() in extensions:
                # Skip temp files
                if f.name.startswith("~$"):
                    continue
                try:
                    stat = f.stat()
                except OSError:
                    continue
                files.append(
                    {
                        "path": str(f),
                        "filename": f.name,
                        "extension": f.suffix.lower(),
                        "size_bytes": stat.st_size,
                    }
                )

        # Sort by filename for deterministic output
        files.sort(key=lambda x: x["filename"])

        return ToolResult.ok(
            json.dumps(
                {
                    "folder": str(path),
                    "count": len(files),
                    "files": files,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
