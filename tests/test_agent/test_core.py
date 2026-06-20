"""Tests for the Agent core loop — OpenAI-compatible."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from create_agent.agent.core import Agent
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


def make_choice(finish_reason: str, content: str | None = None, tool_calls: list | None = None):
    """Create a mock OpenAI choice with message."""
    choice = MagicMock()
    choice.finish_reason = finish_reason

    msg = MagicMock()
    msg.content = content
    msg.tool_calls = tool_calls or []
    choice.message = msg
    return choice


def make_tool_call(tool_id: str, name: str, arguments: str):
    """Create a mock tool call object."""
    tc = MagicMock()
    tc.id = tool_id
    tc.function.name = name
    tc.function.arguments = arguments
    return tc


def make_response(choices: list):
    """Create a mock OpenAI chat completion response."""
    resp = MagicMock()
    resp.choices = choices
    return resp


class TestAgentCore:
    """Tests for the main Agent orchestration loop (OpenAI format)."""

    def test_simple_stop(self, mock_openai_client):
        """Agent completes in one turn when LLM responds with stop."""
        mock_openai_client.chat.completions.create.return_value = make_response(
            [make_choice(finish_reason="stop", content="Here is the answer.")]
        )

        registry = ToolRegistry()
        registry.register(MockScanTool())

        agent = Agent(
            client=mock_openai_client,
            tools=registry,
            stream_output=False,
            verbose=False,
        )

        result = agent.run("Hello")

        assert result.success
        assert "Here is the answer" in result.final_message
        assert result.iterations == 1
        assert result.tool_calls_made == 0

    def test_tool_calls_then_stop(self, mock_openai_client):
        """Agent calls a tool then finishes."""
        # First response: tool_calls
        response1 = make_response(
            [
                make_choice(
                    finish_reason="tool_calls",
                    content=None,
                    tool_calls=[
                        make_tool_call("call_001", "scan_folder", '{"folder": "/test"}')
                    ],
                )
            ]
        )
        # Second response: stop
        response2 = make_response(
            [make_choice(finish_reason="stop", content="Found 2 files in /test.")]
        )
        mock_openai_client.chat.completions.create.side_effect = [response1, response2]

        registry = ToolRegistry()
        registry.register(MockScanTool())

        agent = Agent(
            client=mock_openai_client,
            tools=registry,
            stream_output=False,
            verbose=False,
        )

        result = agent.run("Scan /test")

        assert result.success
        assert result.tool_calls_made == 1
        assert result.iterations == 2
        assert "Found 2 files" in result.final_message

    def test_max_iterations(self, mock_openai_client):
        """Agent stops when max_iterations is reached."""
        response = make_response(
            [
                make_choice(
                    finish_reason="tool_calls",
                    tool_calls=[
                        make_tool_call("call_001", "scan_folder", '{"folder": "/test"}')
                    ],
                )
            ]
        )
        mock_openai_client.chat.completions.create.return_value = response

        registry = ToolRegistry()
        registry.register(MockScanTool())

        agent = Agent(
            client=mock_openai_client,
            tools=registry,
            max_iterations=3,
            stream_output=False,
            verbose=False,
        )

        result = agent.run("Scan")
        assert result.iterations == 3

    def test_length_truncation(self, mock_openai_client):
        """Agent handles length (token limit) finish reason."""
        mock_openai_client.chat.completions.create.return_value = make_response(
            [make_choice(finish_reason="length", content="Partial answer...")]
        )

        registry = ToolRegistry()

        agent = Agent(
            client=mock_openai_client,
            tools=registry,
            stream_output=False,
            verbose=False,
        )

        result = agent.run("Long query")
        assert result.iterations == 1
        assert "truncated" in result.final_message.lower() or "Partial" in result.final_message

    def test_content_filter(self, mock_openai_client):
        """Agent handles content_filter finish reason."""
        mock_openai_client.chat.completions.create.return_value = make_response(
            [make_choice(finish_reason="content_filter", content=None)]
        )

        registry = ToolRegistry()

        agent = Agent(
            client=mock_openai_client,
            tools=registry,
            stream_output=False,
            verbose=False,
        )

        result = agent.run("Blocked content")
        assert result.iterations == 1
        assert "Content filtered" in result.final_message

    def test_unknown_tool_graceful(self, mock_openai_client):
        """Agent handles unknown tool requests gracefully."""
        response1 = make_response(
            [
                make_choice(
                    finish_reason="tool_calls",
                    tool_calls=[
                        make_tool_call("call_001", "nonexistent_tool", "{}")
                    ],
                )
            ]
        )
        response2 = make_response(
            [make_choice(finish_reason="stop", content="I tried an unknown tool.")]
        )
        mock_openai_client.chat.completions.create.side_effect = [response1, response2]

        registry = ToolRegistry()
        registry.register(MockScanTool())

        agent = Agent(
            client=mock_openai_client,
            tools=registry,
            stream_output=False,
            verbose=False,
        )

        result = agent.run("Use nonexistent tool")
        assert result.success
        assert result.tool_calls_made == 1

    def test_invalid_json_arguments(self, mock_openai_client):
        """Agent handles tool calls with invalid JSON arguments."""
        response1 = make_response(
            [
                make_choice(
                    finish_reason="tool_calls",
                    tool_calls=[
                        make_tool_call("call_001", "scan_folder", "not valid json")
                    ],
                )
            ]
        )
        response2 = make_response(
            [make_choice(finish_reason="stop", content="I fixed the error.")]
        )
        mock_openai_client.chat.completions.create.side_effect = [response1, response2]

        registry = ToolRegistry()
        registry.register(MockScanTool())

        agent = Agent(
            client=mock_openai_client,
            tools=registry,
            stream_output=False,
            verbose=False,
        )

        result = agent.run("Test")
        assert result.success
        assert result.tool_calls_made == 1  # Still attempted

    def test_api_error_handling(self, mock_openai_client):
        """Agent handles API errors without crashing."""
        mock_openai_client.chat.completions.create.side_effect = Exception("Connection failed")

        registry = ToolRegistry()

        agent = Agent(
            client=mock_openai_client,
            tools=registry,
            stream_output=False,
            verbose=False,
        )

        result = agent.run("Test")
        assert not result.success
        assert result.error is not None
        assert "Connection failed" in result.error
