"""Agent core — the main LLM↔Tool orchestration loop (OpenAI-compatible).

Implements a manual agentic loop for full control over tool execution,
error handling, and streaming.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from openai import OpenAI

from create_agent.agent.conversation import ConversationManager
from create_agent.agent.prompts import build_system_prompt
from create_agent.tools.registry import ToolRegistry


@dataclass
class AgentResult:
    """Final result from an agent run."""

    success: bool
    final_message: str = ""
    iterations: int = 0
    tool_calls_made: int = 0
    error: str | None = None


class Agent:
    """Orchestrates LLM ↔ Tool interactions via OpenAI-compatible API.

    The agent receives a user task, sends it to the LLM with available tools,
    executes tools that the LLM requests, and continues until the LLM provides
    a final answer or the iteration limit is reached.

    Usage:
        client = OpenAI(base_url="...", api_key="...")
        agent = Agent(client, tools, model="gpt-4o")
        result = agent.run("Classify documents in ./docs into: Legal, HR, Finance")
        print(result.final_message)
    """

    def __init__(
        self,
        client: OpenAI,
        tools: ToolRegistry,
        model: str = "gpt-4o",
        max_tokens: int = 16000,
        temperature: float = 0.0,
        max_iterations: int = 20,
        verbose: bool = False,
        stream_output: bool = True,
    ) -> None:
        self._client = client
        self._tools = tools
        self._model = model
        self._max_tokens = max_tokens
        self._temperature = temperature
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
        system_prompt = build_system_prompt(
            tool_descriptions=self._tools.get_tool_descriptions(),
            max_iterations=self._max_iterations,
        )

        conversation = ConversationManager(system_prompt)
        conversation.add_user_message(user_input)

        tool_calls_made = 0
        iterations = 0
        final_text: list[str] = []
        tools_format = self._tools.get_openai_format()

        # --- Main agent loop ---
        while iterations < self._max_iterations:
            iterations += 1

            if self._verbose:
                print(f"\n[Agent] Iteration {iterations}/{self._max_iterations}")

            try:
                response = self._client.chat.completions.create(
                    model=self._model,
                    max_tokens=self._max_tokens,
                    temperature=self._temperature,
                    messages=conversation.get_messages(),
                    tools=tools_format if tools_format else None,
                )
            except Exception as e:
                return AgentResult(
                    success=False,
                    iterations=iterations,
                    tool_calls_made=tool_calls_made,
                    error=f"API error: {e}",
                )

            choice = response.choices[0]
            finish_reason = choice.finish_reason
            message = choice.message

            if self._verbose:
                print(f"[Agent] finish_reason: {finish_reason}")

            # --- Handle finish reasons ---
            if finish_reason == "stop":
                # LLM finished naturally
                content = message.content or ""
                if content and self._stream_output:
                    print(content)
                final_text.append(content)
                conversation.add_assistant_message(
                    {"role": "assistant", "content": content}
                )
                break

            elif finish_reason == "tool_calls":
                # LLM wants to use tools
                content = message.content or ""
                if content and self._stream_output:
                    print(content)

                tool_calls = message.tool_calls or []

                # Store assistant message with tool_calls
                conversation.add_assistant_message(
                    {
                        "role": "assistant",
                        "content": content,
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments,
                                },
                            }
                            for tc in tool_calls
                        ],
                    }
                )

                # Execute each tool call
                for tc in tool_calls:
                    result = self._execute_tool_call(tc)
                    conversation.add_tool_result(
                        tool_call_id=tc.id,
                        tool_name=tc.function.name,
                        content=result,
                    )
                    tool_calls_made += 1

            elif finish_reason == "length":
                # Output truncated
                content = message.content or ""
                if content:
                    final_text.append(content)
                    final_text.append(
                        "\n[Warning: response was truncated due to token limit]"
                    )
                conversation.add_assistant_message(
                    {"role": "assistant", "content": content}
                )
                break

            elif finish_reason == "content_filter":
                # Content filtered by provider
                final_text.append(
                    "[Content filtered: the request was blocked by the provider's content filter.]"
                )
                break

            else:
                # Unknown finish reason — capture what we have and stop
                if self._verbose:
                    print(f"[Agent] Unknown finish_reason: {finish_reason}")
                content = message.content or ""
                if content:
                    final_text.append(content)
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

    def _execute_tool_call(self, tool_call: Any) -> str:
        """Execute a single tool call and return the result string."""
        func = tool_call.function
        tool_name = func.name

        # Parse arguments JSON
        try:
            tool_input = json.loads(func.arguments)
        except json.JSONDecodeError:
            return f"Error: invalid JSON arguments: {func.arguments}"

        if self._verbose:
            print(
                f"\n[Tool] {tool_name}({json.dumps(tool_input, ensure_ascii=False)[:120]})"
            )

        tool = self._tools.get(tool_name)

        if tool is None:
            return (
                f"Error: Unknown tool '{tool_name}'. "
                f"Available: {[t.name for t in self._tools.list_tools()]}"
            )

        try:
            result = tool.execute(tool_input)
            if self._verbose and result.is_error:
                print(f"[Tool] ERROR: {result.content[:200]}")
            return result.content
        except Exception as e:
            error_msg = f"Tool execution failed: {e}"
            if self._verbose:
                print(f"[Tool] EXCEPTION: {error_msg}")
            return error_msg
