"""Web search tool using Tavily API."""

from __future__ import annotations

import json

from create_agent.tools.base import BaseTool, ToolResult


class WebSearchTool(BaseTool):
    """Search the web using Tavily API.

    Returns formatted search results with titles, URLs, and content snippets.
    """

    def __init__(
        self,
        api_key: str,
        max_results: int = 5,
        include_domains: list[str] | None = None,
        exclude_domains: list[str] | None = None,
    ) -> None:
        self._api_key = api_key
        self._max_results = max_results
        self._include_domains = include_domains or []
        self._exclude_domains = exclude_domains or []

    @property
    def name(self) -> str:
        return "web_search"

    @property
    def description(self) -> str:
        return (
            "Search the web for current information using Tavily. "
            "Call this when you need information beyond your knowledge cutoff, "
            "current events, recent data, or real-time facts. "
            "Returns results with titles, URLs, and content snippets."
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query string.",
                },
                "max_results": {
                    "type": "integer",
                    "description": f"Maximum number of results (1-20, default {self._max_results}).",
                },
            },
            "required": ["query"],
        }

    def execute(self, input_data: dict) -> ToolResult:
        query = input_data.get("query", "")
        max_results = input_data.get("max_results", self._max_results)

        if not query.strip():
            return ToolResult.error("Search query is empty.")

        if not self._api_key:
            return ToolResult.error(
                "Tavily API key is not configured. Set TAVILY_API_KEY "
                "environment variable or add it to config.yaml."
            )

        try:
            from tavily import TavilyClient

            client = TavilyClient(api_key=self._api_key)
            response = client.search(
                query=query,
                max_results=min(max_results, 20),
                include_domains=self._include_domains or None,
                exclude_domains=self._exclude_domains or None,
            )

            results = response.get("results", [])
            formatted = []
            for r in results:
                formatted.append(
                    {
                        "title": r.get("title", ""),
                        "url": r.get("url", ""),
                        "content": r.get("content", ""),
                        "score": r.get("score", 0),
                    }
                )

            return ToolResult.ok(
                json.dumps(
                    {
                        "query": query,
                        "count": len(formatted),
                        "results": formatted,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )

        except ImportError:
            return ToolResult.error(
                "tavily-python package is not installed. Run: pip install tavily-python"
            )
        except Exception as e:
            return ToolResult.error(f"Web search failed: {e}")
