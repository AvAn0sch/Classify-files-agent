"""Tests for tool behaviors."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from create_agent.tools.base import ToolResult
from create_agent.tools.file_scanner import FileScannerTool
from create_agent.tools.file_organizer import FileOrganizerTool
from create_agent.tools.registry import ToolRegistry


class TestFileScannerTool:
    """Tests for the file_scanner tool."""

    def test_scans_supported_files(self, temp_dir):
        """Scanner finds .docx, .pptx, .pdf files."""
        # Create test files
        (temp_dir / "report.docx").touch()
        (temp_dir / "presentation.pptx").touch()
        (temp_dir / "doc.pdf").touch()
        (temp_dir / "notes.txt").touch()  # Should be ignored
        # Hidden temp file should be ignored
        (temp_dir / "~$temp.docx").touch()

        tool = FileScannerTool()
        result = tool.execute({"folder": str(temp_dir)})

        assert not result.is_error
        data = json.loads(result.content)
        assert data["count"] == 3
        assert len(data["files"]) == 3

        filenames = {f["filename"] for f in data["files"]}
        assert filenames == {"report.docx", "presentation.pptx", "doc.pdf"}

    def test_missing_folder(self):
        """Scanner returns error for nonexistent folder."""
        tool = FileScannerTool()
        result = tool.execute({"folder": "/nonexistent/path"})
        assert result.is_error


class TestFileOrganizerTool:
    """Tests for the file_organizer tool."""

    def test_creates_folders_and_moves_files(self, temp_dir):
        """Organizer creates category folders and moves files."""
        # Create test files
        (temp_dir / "contract1.docx").write_text("test")
        (temp_dir / "report1.pdf").write_text("test")

        tool = FileOrganizerTool()
        result = tool.execute(
            {
                "base_folder": str(temp_dir),
                "assignments": [
                    {"file_path": str(temp_dir / "contract1.docx"), "category": "合同"},
                    {"file_path": str(temp_dir / "report1.pdf"), "category": "报告"},
                ],
            }
        )

        assert not result.is_error
        data = json.loads(result.content)
        assert data["moved"] == 2
        assert len(data["folders_created"]) == 2

        # Verify files were actually moved
        assert (temp_dir / "合同" / "contract1.docx").exists()
        assert (temp_dir / "报告" / "report1.pdf").exists()
        assert not (temp_dir / "contract1.docx").exists()
        assert not (temp_dir / "report1.pdf").exists()

    def test_handles_missing_files(self, temp_dir):
        """Organizer skips files that don't exist."""
        tool = FileOrganizerTool()
        result = tool.execute(
            {
                "base_folder": str(temp_dir),
                "assignments": [
                    {"file_path": str(temp_dir / "nonexistent.docx"), "category": "合同"},
                ],
            }
        )

        data = json.loads(result.content)
        assert data["moved"] == 0
        assert len(data["errors"]) == 1

    def test_sanitizes_category_names(self, temp_dir):
        """Organizer replaces slashes in category names."""
        (temp_dir / "file.docx").write_text("test")

        tool = FileOrganizerTool()
        result = tool.execute(
            {
                "base_folder": str(temp_dir),
                "assignments": [
                    {"file_path": str(temp_dir / "file.docx"), "category": "a/b/c"},
                ],
            }
        )

        data = json.loads(result.content)
        assert data["moved"] == 1
        # Category folder should use hyphens not slashes
        assert (temp_dir / "a-b-c" / "file.docx").exists()


class TestToolRegistry:
    """Tests for the ToolRegistry."""

    def test_register_and_lookup(self):
        """Tools can be registered and retrieved."""
        registry = ToolRegistry()
        tool = FileScannerTool()
        registry.register(tool)

        assert registry.get("scan_folder") is tool
        assert "scan_folder" in registry

    def test_duplicate_registration(self):
        """Registering duplicate tool names raises error."""
        registry = ToolRegistry()
        registry.register(FileScannerTool())

        with pytest.raises(ValueError, match="already registered"):
            registry.register(FileScannerTool())

    def test_openai_format(self):
        """Registry outputs tools in OpenAI function-calling format."""
        registry = ToolRegistry()
        registry.register(FileScannerTool())

        tools = registry.get_openai_format()
        assert len(tools) == 1
        assert tools[0]["type"] == "function"
        assert tools[0]["function"]["name"] == "scan_folder"
        assert "parameters" in tools[0]["function"]
        assert "description" in tools[0]["function"]
