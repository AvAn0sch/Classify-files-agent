"""Agent core — the main LLM↔Tool orchestration loop.

This implements a manual agentic loop (not the SDK's tool_runner) for full
control over tool execution, error handling, logging, and streaming.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import anthropic

from create_agent.agent.conversation import ConversationManager
from create_agent.agent.prompts import build_system_prompt
from create_agent.tools.registry import ToolRegistry

if TYPE_CHECKING:
    pass


@dataclass
class AgentResult:
    """Final result from an agent run."""

    success: bool
    final_message: str = ""
    iterations: int = 0
    tool_calls_made: int = 0
    error: str | None = None


class Agent:
    """Orchestrates Claude API ↔ Tool interactions.

    The agent receives a user task, sends it to Claude with available tools,
    executes tools that Claude requests, and continues until Claude provides
    a final answer or the iteration limit is reached.

    Usage:
        agent = Agent(client, tools, config)
        result = agent.run("Classify documents in ./docs into: Legal, HR, Finance")
        print(result.final_message)
    """

    def __init__(
        self,
        client: anthropic.Anthropic,
        tools: ToolRegistry,
        model: str = "claude-opus-4-8",
        max_tokens: int = 16000,
        max_iterations: int = 20,
        verbose: bool = False,
        stream_output: bool = True,
    ) -> None:
        self._client = client
        self._tools = tools
        self._model = model
        self._max_tokens = max_tokens
        self._max_iterations = max_iterations
        self._verbose = verbose
        self._stream_output = stream_output

    def run(self, user_input: str) -> AgentResult:
        """Execute one full agent run.

        Args:
            user_input: The user's task description or question.

        Returns:
            AgentResult with the final output and execution metadata.
        """
        # Build conversation
        system_prompt = build_system_prompt(
            tool_descriptions=self._tools.get_tool_descriptions(),
            max_iterations=self._max_iterations,
        )

        conversation = ConversationManager(system_prompt)
        conversation.add_user_message(user_input)

        tool_calls_made = 0
        iterations = 0
        final_text: list[str] = []

        # --- Main agent loop ---
        while iterations < self._max_iterations:
            iterations += 1

            if self._verbose:
                print(f"\n[Agent] Iteration {iterations}/{self._max_iterations}")

            try:
                response = self._client.messages.create(
                    model=self._model,
                    max_tokens=self._max_tokens,
                    system=[
                        {
                            "type": "text",
                            "text": system_prompt,
                            "cache_control": {"type": "ephemeral"},
                        }
                    ],
                    tools=self._tools.get_claude_format(),
                    messages=conversation.get_messages(),
                )
            except anthropic.APIStatusError as e:
                return AgentResult(
                    success=False,
                    iterations=iterations,
                    tool_calls_made=tool_calls_made,
                    error=f"API error (status {e.status_code}): {e.message}",
                )
            except Exception as e:
                return AgentResult(
                    success=False,
                    iterations=iterations,
                    tool_calls_made=tool_calls_made,
                    error=f"Unexpected error: {e}",
                )

            stop_reason = response.stop_reason
            content_blocks = response.content

            if self._verbose:
                print(f"[Agent] stop_reason: {stop_reason}")
                print(f"[Agent] content blocks: {len(content_blocks)}")

            # --- Handle stop reasons ---
            if stop_reason == "end_turn":
                # Claude finished naturally
                text = self._extract_text(content_blocks)
                if text:
                    final_text.append(text)
                conversation.add_assistant_response(content_blocks)
                break

            elif stop_reason == "tool_use":
                # Claude wants to use tools
                # First, extract and show any text
                text = self._extract_text(content_blocks)
                if text and self._stream_output:
                    print(text)

                # Add assistant response to history
                conversation.add_assistant_response(content_blocks)

                # Execute all tool_use blocks
                tool_results: list[dict] = []
                for block in content_blocks:
                    if getattr(block, "type", None) == "tool_use":
                        tool_results.append(self._execute_tool_block(block))
                        tool_calls_made += 1

                # Feed tool results back
                if tool_results:
                    conversation.add_tool_results(tool_results)

            elif stop_reason == "refusal":
                # Safety refusal
                refusal_details = getattr(response, "stop_details", {})
                category = refusal_details.get("category", "unknown")
                msg = f"[Refused: {category}] Claude declined this request for safety reasons."
                final_text.append(msg)
                break

            elif stop_reason == "max_tokens":
                # Output truncated — warn but use what we have
                text = self._extract_text(content_blocks)
                if text:
                    final_text.append(text)
                    final_text.append("\n[Warning: response was truncated due to token limit]")
                conversation.add_assistant_response(content_blocks)
                break

            else:
                # Unknown stop reason
                if self._verbose:
                    print(f"[Agent] Unknown stop_reason: {stop_reason}")
                text = self._extract_text(content_blocks)
                if text:
                    final_text.append(text)
                break

        # --- Post-loop ---
        if iterations >= self._max_iterations and not final_text:
            final_text.append(
                f"[Reached maximum iterations ({self._max_iterations}). "
                "The task may be incomplete.]"
            )

        return AgentResult(
            success=True,
            final_message="\n".join(final_text) if final_text else "[No output]",
            iterations=iterations,
            tool_calls_made=tool_calls_made,
        )

    def _execute_tool_block(self, tool_use_block: Any) -> dict:
        """Execute a single tool_use block and return the tool_result dict."""
        tool_name = getattr(tool_use_block, "name", "unknown")
        tool_id = getattr(tool_use_block, "id", "unknown")
        tool_input = getattr(tool_use_block, "input", {})

        if self._verbose:
            print(f"\n[Tool] {tool_name}({json.dumps(tool_input, ensure_ascii=False)[:120]})")

        tool = self._tools.get(tool_name)

        if tool is None:
            content = f"Error: Unknown tool '{tool_name}'. Available: {[t.name for t in self._tools.list_tools()]}"
            return {"tool_use_id": tool_id, "content": content}

        try:
            result = tool.execute(tool_input)
            if self._verbose and result.is_error:
                print(f"[Tool] ERROR: {result.content[:200]}")
            return {"tool_use_id": tool_id, "content": result.content}
        except Exception as e:
            error_msg = f"Tool execution failed: {e}"
            if self._verbose:
                print(f"[Tool] EXCEPTION: {error_msg}")
            return {"tool_use_id": tool_id, "content": error_msg}

    @staticmethod
    def _extract_text(content_blocks: list) -> str:
        """Extract text from content blocks for display."""
        texts = []
        for block in content_blocks:
            block_type = getattr(block, "type", None)
            if block_type == "text":
                texts.append(getattr(block, "text", ""))
        return "\n".join(texts)
