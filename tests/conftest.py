"""Shared test fixtures — OpenAI-compatible."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def temp_dir():
    """Create a temporary directory for file-based tests."""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def mock_openai_client():
    """Create a mock OpenAI client."""
    return MagicMock()


@pytest.fixture
def sample_config_dict():
    """Sample config dictionary for testing."""
    return {
        "llm": {
            "base_url": "https://api.openai.com/v1",
            "api_key": "test-key",
            "model": "gpt-4o",
            "max_tokens": 16000,
            "temperature": 0.0,
        },
        "api_keys": {
            "openai": "test-key",
            "tavily": "test-tavily-key",
        },
        "tools": {
            "web_search": {"max_results": 3},
            "classification": {"batch_size": 5, "max_chars_per_doc": 2000},
        },
        "extraction": {
            "pdf_library": "pdfplumber",
            "max_chars_per_doc": 10000,
            "supported_extensions": [".docx", ".pptx", ".pdf"],
        },
        "agent": {
            "max_iterations": 5,
            "verbose": False,
            "stream_output": False,
        },
    }
