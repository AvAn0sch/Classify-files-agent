"""Tool registry for managing available agent tools."""

from __future__ import annotations

from create_agent.tools.base import BaseTool


class ToolRegistry:
    """Manages tool registration, lookup, and Claude-format conversion."""

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a tool.

        Args:
            tool: The tool instance to register.

        Raises:
            ValueError: If a tool with the same name is already registered.
        """
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' is already registered")
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool | None:
        """Look up a tool by name.

        Args:
            name: The tool name to look up.

        Returns:
            The tool instance, or None if not found.
        """
        return self._tools.get(name)

    def list_tools(self) -> list[BaseTool]:
        """Return all registered tools, sorted alphabetically by name.

        Sorting ensures deterministic serialization for prompt caching.
        """
        return sorted(self._tools.values(), key=lambda t: t.name)

    def get_claude_format(self) -> list[dict]:
        """Return all registered tools in Anthropic API format."""
        return [t.to_claude_format() for t in self.list_tools()]

    def get_tool_descriptions(self) -> str:
        """Generate a formatted string describing all tools for the system prompt."""
        lines = []
        for tool in self.list_tools():
            lines.append(f"- **{tool.name}**: {tool.description}")
            # Include parameter info from schema
            props = tool.input_schema.get("properties", {})
            required = tool.input_schema.get("required", [])
            if props:
                for pname, pinfo in props.items():
                    req_mark = " (required)" if pname in required else ""
                    lines.append(
                        f"  - `{pname}` ({pinfo.get('type', 'string')})"
                        f"{req_mark}: {pinfo.get('description', '')}"
                    )
        return "\n".join(lines)

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        return name in self._tools
