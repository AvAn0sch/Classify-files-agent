"""Conversation history management for the Claude API.

Enforces correct message ordering and provides token estimation.
"""

from __future__ import annotations


class ConversationManager:
    """Manages the stateless conversation history for Claude API calls.

    The Claude Messages API is stateless — each call must include the full
    conversation history. This manager tracks messages and ensures correct
    role ordering (user/assistant alternation with tool results in user role).
    """

    def __init__(self, system_prompt: str) -> None:
        self.system_prompt: str = system_prompt
        self._messages: list[dict] = []

    def add_user_message(self, content: str) -> None:
        """Add a plain-text user message."""
        self._messages.append({"role": "user", "content": content})

    def add_user_content_blocks(self, blocks: list[dict]) -> None:
        """Add a user message with content blocks (e.g., tool results)."""
        self._messages.append({"role": "user", "content": blocks})

    def add_assistant_response(self, content_blocks: list) -> None:
        """Add the assistant's response content blocks.

        IMPORTANT: Pass the FULL response.content list from the Anthropic SDK.
        This preserves tool_use blocks with their IDs intact.
        """
        self._messages.append({"role": "assistant", "content": content_blocks})

    def add_tool_results(self, results: list[dict]) -> None:
        """Add tool results as a user message.

        Each result must have 'tool_use_id' matching the triggering tool_use block,
        and 'content' with the tool's output string.

        Args:
            results: List of {"tool_use_id": "...", "content": "..."} dicts.
        """
        blocks = [
            {
                "type": "tool_result",
                "tool_use_id": r["tool_use_id"],
                "content": r["content"],
            }
            for r in results
        ]
        self._messages.append({"role": "user", "content": blocks})

    def get_messages(self) -> list[dict]:
        """Return the full message list for API calls."""
        return list(self._messages)

    def estimated_tokens(self) -> int:
        """Rough token count estimate (characters / 4).

        This is a fast heuristic. For accurate counts, use the
        Anthropic token-counting API.
        """
        total = len(self.system_prompt)
        for msg in self._messages:
            content = msg.get("content", "")
            if isinstance(content, str):
                total += len(content)
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict):
                        total += len(str(block))
        return total // 4

    def trim_oldest_turns(self, keep_turns: int = 10) -> None:
        """Remove oldest conversation turns, keeping the most recent N.

        A "turn" is one assistant + one user exchange. Ensures the first
        message stays as user role after trimming.

        Args:
            keep_turns: Number of recent turns to preserve.
        """
        min_messages = keep_turns * 2
        if len(self._messages) <= min_messages:
            return

        # Ensure we start with a user message after trimming
        to_remove = len(self._messages) - min_messages
        if self._messages[to_remove].get("role") != "user":
            to_remove -= 1  # Keep one more to maintain user→assistant→user pattern

        if to_remove > 0:
            self._messages = self._messages[to_remove:]

        # Safety: if first message is not user, prepend a system note
        if self._messages and self._messages[0].get("role") != "user":
            self._messages.insert(
                0,
                {
                    "role": "user",
                    "content": "[Earlier conversation history trimmed]",
                },
            )

    @property
    def turn_count(self) -> int:
        """Number of complete user→assistant exchanges."""
        return len(self._messages) // 2

    def __len__(self) -> int:
        return len(self._messages)
