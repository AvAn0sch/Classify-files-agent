"""Tests for the Agent core loop."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from create_agent.agent.core import Agent, AgentResult
from create_agent.tools.base import BaseTool, ToolResult
from create_agent.tools.registry import ToolRegistry


class MockScanTool(BaseTool):
    @property
    def name(self) -> str:
        return "scan_folder"

    @property
    def description(self) -> str:
        return "Scan a folder for files."

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "folder": {"type": "string", "description": "Folder to scan"}
            },
            "required": ["folder"],
        }

    def execute(self, input_data: dict) -> ToolResult:
        return ToolResult.ok('{"folder": "/test", "files": ["a.docx", "b.pdf"]}')


def make_text_block(text: str):
    """Create a mock text content block."""
    block = MagicMock()
    block.type = "text"
    block.text = text
    return block


def make_tool_use_block(name: str, input_data: dict, tool_id: str = "toolu_001"):
    """Create a mock tool_use content block."""
    block = MagicMock()
    block.type = "tool_use"
    block.name = name
    block.input = input_data
    block.id = tool_id
    return block


def make_mock_response(stop_reason: str, content_blocks: list):
    """Create a mock Anthropic API response."""
    response = MagicMock()
    response.stop_reason = stop_reason
    response.content = content_blocks
    return response


class TestAgentCore:
    """Tests for the main Agent orchestration loop."""

    def test_simple_end_turn(self, mock_anthropic_client):
        """Agent completes in one turn when Claude responds with end_turn."""
        mock_anthropic_client.messages.create.return_value = make_mock_response(
            stop_reason="end_turn",
            content_blocks=[make_text_block("Here is the answer.")],
        )

        registry = ToolRegistry()
        registry.register(MockScanTool())

        agent = Agent(
            client=mock_anthropic_client,
            tools=registry,
            stream_output=False,
            verbose=False,
        )

        result = agent.run("Hello")

        assert result.success
        assert "Here is the answer" in result.final_message
        assert result.iterations == 1
        assert result.tool_calls_made == 0

    def test_tool_use_and_end(self, mock_anthropic_client):
        """Agent calls a tool then finishes."""
        # First response: tool use
        response1 = make_mock_response(
            stop_reason="tool_use",
            content_blocks=[make_tool_use_block("scan_folder", {"folder": "/test"})],
        )
        # Second response: end turn
        response2 = make_mock_response(
            stop_reason="end_turn",
            content_blocks=[make_text_block("Found 2 files in /test.")],
        )
        mock_anthropic_client.messages.create.side_effect = [response1, response2]

        registry = ToolRegistry()
        registry.register(MockScanTool())

        agent = Agent(
            client=mock_anthropic_client,
            tools=registry,
            stream_output=False,
            verbose=False,
        )

        result = agent.run("Scan /test")

        assert result.success
        assert result.tool_calls_made == 1
        assert result.iterations == 2
        assert "Found 2 files" in result.final_message

    def test_max_iterations(self, mock_anthropic_client):
        """Agent stops when max_iterations is reached."""
        response = make_mock_response(
            stop_reason="tool_use",
            content_blocks=[make_tool_use_block("scan_folder", {"folder": "/test"})],
        )
        mock_anthropic_client.messages.create.return_value = response

        registry = ToolRegistry()
        registry.register(MockScanTool())

        agent = Agent(
            client=mock_anthropic_client,
            tools=registry,
            max_iterations=3,
            stream_output=False,
            verbose=False,
        )

        result = agent.run("Scan")

        assert result.iterations == 3

    def test_refusal(self, mock_anthropic_client):
        """Agent handles safety refusals."""
        mock_response = make_mock_response(
            stop_reason="refusal",
            content_blocks=[],
        )
        mock_response.stop_details = MagicMock()
        mock_response.stop_details.category = "safety"
        mock_anthropic_client.messages.create.return_value = mock_response

        registry = ToolRegistry()

        agent = Agent(
            client=mock_anthropic_client,
            tools=registry,
            stream_output=False,
            verbose=False,
        )

        result = agent.run("Do something unsafe")
        assert result.iterations == 1
        assert result.tool_calls_made == 0

    def test_unknown_tool_graceful(self, mock_anthropic_client):
        """Agent handles unknown tool requests gracefully."""
        response1 = make_mock_response(
            stop_reason="tool_use",
            content_blocks=[make_tool_use_block("nonexistent_tool", {})],
        )
        response2 = make_mock_response(
            stop_reason="end_turn",
            content_blocks=[make_text_block("I tried an unknown tool.")],
        )
        mock_anthropic_client.messages.create.side_effect = [response1, response2]

        registry = ToolRegistry()
        registry.register(MockScanTool())

        agent = Agent(
            client=mock_anthropic_client,
            tools=registry,
            stream_output=False,
            verbose=False,
        )

        result = agent.run("Use nonexistent tool")
        assert result.success
        assert result.tool_calls_made == 1  # Still counts as a call attempt

    def test_api_error_handling(self, mock_anthropic_client):
        """Agent handles API errors without crashing."""
        from anthropic import APIStatusError

        mock_anthropic_client.messages.create.side_effect = APIStatusError(
            "Rate limited",
            response=MagicMock(),
            body={"error": {"message": "Rate limited"}},
        )

        registry = ToolRegistry()

        agent = Agent(
            client=mock_anthropic_client,
            tools=registry,
            stream_output=False,
            verbose=False,
        )

        result = agent.run("Test")
        assert not result.success
        assert result.error is not None
        assert "Rate limited" in result.error or "API error" in result.error
