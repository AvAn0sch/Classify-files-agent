"""Conversation history management for OpenAI-compatible chat API.

The OpenAI chat completions API is stateless — each call must include the full
conversation history. This manager tracks messages in the correct format.
"""

from __future__ import annotations


class ConversationManager:
    """Manages the stateless conversation history for OpenAI chat API calls.

    Messages follow the OpenAI format:
    - {"role": "system", "content": "..."} — system prompt (first message)
    - {"role": "user", "content": "..."} — user input
    - {"role": "assistant", "content": "...", "tool_calls": [...]} — LLM response
    - {"role": "tool", "tool_call_id": "...", "content": "..."} — tool execution result
    """

    def __init__(self, system_prompt: str) -> None:
        self.system_prompt: str = system_prompt
        self._messages: list[dict] = []

    def get_messages(self) -> list[dict]:
        """Return the full message list for API calls.

        The system message is always first, followed by the conversation history.
        """
        return [{"role": "system", "content": self.system_prompt}] + self._messages

    def add_user_message(self, content: str) -> None:
        """Add a user text message."""
        self._messages.append({"role": "user", "content": content})

    def add_assistant_message(self, message: dict) -> None:
        """Add the assistant's response message.

        The message dict should include 'content' (may be None if tool_calls present)
        and optionally 'tool_calls'.

        Args:
            message: The full assistant message dict, e.g.:
                {"role": "assistant", "content": "Hello!", "tool_calls": None}
        """
        clean = {"role": "assistant", "content": message.get("content")}
        if message.get("tool_calls"):
            clean["tool_calls"] = message["tool_calls"]
        self._messages.append(clean)

    def add_tool_result(self, tool_call_id: str, tool_name: str, content: str) -> None:
        """Add a tool execution result message.

        Args:
            tool_call_id: The ID of the tool call this result responds to.
            tool_name: The name of the tool (for logging).
            content: The tool's output string.
        """
        self._messages.append(
            {
                "role": "tool",
                "tool_call_id": tool_call_id,
                "content": content,
            }
        )

    def estimated_tokens(self) -> int:
        """Rough token count estimate (characters / 4)."""
        total = len(self.system_prompt)
        for msg in self._messages:
            content = msg.get("content", "") or ""
            total += len(content)
            # Account for tool_calls serialization
            if msg.get("tool_calls"):
                total += len(str(msg["tool_calls"]))
        return total // 4

    def trim_oldest_turns(self, keep_turns: int = 10) -> None:
        """Remove oldest conversation turns, keeping the most recent N.

        A "turn" is one assistant + one user/tool exchange.
        """
        # Count assistant messages as turn boundaries
        assistant_indices = [
            i for i, m in enumerate(self._messages) if m["role"] == "assistant"
        ]
        if len(assistant_indices) <= keep_turns:
            return

        # Find the cutoff: keep the last `keep_turns` assistant turns
        cutoff = assistant_indices[-(keep_turns)]
        self._messages = self._messages[cutoff:]

        # Ensure first message after trim is user or tool
        if self._messages and self._messages[0]["role"] == "assistant":
            self._messages.insert(
                0,
                {
                    "role": "user",
                    "content": "[Earlier conversation history trimmed]",
                },
            )

    @property
    def turn_count(self) -> int:
        """Number of assistant turns (tool calls or final answers)."""
        return sum(1 for m in self._messages if m["role"] == "assistant")

    def __len__(self) -> int:
        return len(self._messages)
