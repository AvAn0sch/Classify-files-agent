"""Organize files into category sub-folders."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from create_agent.tools.base import BaseTool, ToolResult


class FileOrganizerTool(BaseTool):
    """Create category sub-folders and move classified files into them."""

    @property
    def name(self) -> str:
        return "organize_files"

    @property
    def description(self) -> str:
        return (
            "Create category sub-folders and move files into them. "
            "Call this AFTER classification is complete to organize documents. "
            "Provide the base folder path and a list of file→category assignments."
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "base_folder": {
                    "type": "string",
                    "description": "The base folder containing the documents.",
                },
                "assignments": {
                    "type": "array",
                    "description": "List of file→category assignments from classification.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "Absolute path to the document.",
                            },
                            "category": {
                                "type": "string",
                                "description": "Category folder name to move into.",
                            },
                        },
                        "required": ["file_path", "category"],
                    },
                },
            },
            "required": ["base_folder", "assignments"],
        }

    def execute(self, input_data: dict) -> ToolResult:
        base_folder = Path(input_data["base_folder"]).resolve()
        assignments = input_data.get("assignments", [])

        if not base_folder.exists():
            return ToolResult.error(f"Base folder not found: {base_folder}")
        if not assignments:
            return ToolResult.ok(json.dumps({"moved": 0, "message": "No files to organize."}))

        results: dict = {
            "moved": 0,
            "skipped": 0,
            "folders_created": [],
            "errors": [],
        }

        for item in assignments:
            file_path = Path(item["file_path"])
            category = item["category"].strip().replace("/", "-").replace("\\", "-")

            if not file_path.exists():
                results["skipped"] += 1
                results["errors"].append(f"File not found: {file_path}")
                continue

            # Create category folder
            category_folder = base_folder / category
            if not category_folder.exists():
                try:
                    category_folder.mkdir(parents=True, exist_ok=True)
                    if str(category_folder) not in results["folders_created"]:
                        results["folders_created"].append(str(category_folder))
                except OSError as e:
                    results["errors"].append(f"Cannot create folder '{category}': {e}")
                    continue

            # Handle filename conflicts
            dest = category_folder / file_path.name
            if dest.exists():
                stem = file_path.stem
                suffix = file_path.suffix
                counter = 1
                while dest.exists():
                    dest = category_folder / f"{stem}_{counter}{suffix}"
                    counter += 1

            # Move the file
            try:
                shutil.move(str(file_path), str(dest))
                results["moved"] += 1
            except OSError as e:
                results["errors"].append(f"Cannot move {file_path.name}: {e}")

        return ToolResult.ok(json.dumps(results, ensure_ascii=False, indent=2))
