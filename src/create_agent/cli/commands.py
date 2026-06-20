"""Agent initialization and interactive chat loop."""

from __future__ import annotations

import sys
from pathlib import Path

from openai import OpenAI

from create_agent.agent.core import Agent
from create_agent.cli.display import (
    console,
    print_banner,
    print_error,
    print_info,
)
from create_agent.config.loader import load_config
from create_agent.tools.classifier import ClassifyDocumentsTool
from create_agent.tools.document_qa import DocumentQATool
from create_agent.tools.file_organizer import FileOrganizerTool
from create_agent.tools.file_scanner import FileScannerTool
from create_agent.tools.registry import ToolRegistry
from create_agent.tools.text_extractor import TextExtractorTool
from create_agent.tools.web_search import WebSearchTool


def _build_agent(config_path: str | None = None) -> Agent:
    """Initialize the agent with all tools based on configuration.

    Args:
        config_path: Optional path to config.yaml.

    Returns:
        Configured Agent instance.
    """
    config = load_config(config_path)

    # Resolve API key: config value first, then env var
    api_key = config.llm.api_key or config.api_keys.openai
    if not api_key:
        print_error(
            "OPENAI_API_KEY is not set. Set it as an environment variable "
            "or in config.yaml (llm.api_key or api_keys.openai)."
        )
        sys.exit(1)

    # Initialize OpenAI-compatible client
    client = OpenAI(
        base_url=config.llm.base_url,
        api_key=api_key,
    )

    # Build tool registry
    registry = ToolRegistry()
    registry.register(
        FileScannerTool(supported_extensions=config.extraction.supported_extensions)
    )
    registry.register(
        TextExtractorTool(
            supported_extensions=config.extraction.supported_extensions,
            max_chars=config.extraction.max_chars_per_doc,
            pdf_library=config.extraction.pdf_library,
        )
    )
    registry.register(
        ClassifyDocumentsTool(
            client=client,
            model=config.llm.model,
            batch_size=config.tools.classification.batch_size,
            max_chars_per_doc=config.tools.classification.max_chars_per_doc,
        )
    )
    registry.register(FileOrganizerTool())

    if config.tools.web_search.enabled and config.api_keys.tavily:
        registry.register(
            WebSearchTool(
                api_key=config.api_keys.tavily,
                max_results=config.tools.web_search.max_results,
                include_domains=config.tools.web_search.include_domains,
                exclude_domains=config.tools.web_search.exclude_domains,
            )
        )

    registry.register(
        DocumentQATool(
            client=client,
            model=config.llm.model,
            supported_extensions=config.extraction.supported_extensions,
            max_chars_per_doc=config.extraction.max_chars_per_doc,
            pdf_library=config.extraction.pdf_library,
        )
    )

    return Agent(
        client=client,
        tools=registry,
        model=config.llm.model,
        max_tokens=config.llm.max_tokens,
        temperature=config.llm.temperature,
        max_iterations=config.agent.max_iterations,
        verbose=config.agent.verbose,
        stream_output=config.agent.stream_output,
    )


def start_chat(config_path: str | None = None) -> None:
    """Start an interactive chat session with the agent.

    This is the main entry point. Run `python main.py` to start.
    """
    print_banner()

    # Locate config
    if config_path is None:
        cwd_config = Path("config.yaml")
        if cwd_config.exists():
            config_path = str(cwd_config)

    try:
        agent = _build_agent(config_path)
    except FileNotFoundError as e:
        print_error(str(e))
        print_info(
            "Copy config.example.yaml to config.yaml and set your API keys:\n"
            "  cp config.example.yaml config.yaml\n"
            "  set OPENAI_API_KEY=sk-..."
        )
        return

    console.print("\n[bold green]Agent ready. Type your request or 'exit' to quit.[/bold green]")
    console.print("[dim]Examples:[/dim]")
    console.print("  [dim]• 帮我把 ./docs 里的文件按合同、报告、发票分类[/dim]")
    console.print("  [dim]• 搜索最新的 AI 法规进展[/dim]")
    console.print("  [dim]• Q4 营收报告里关于成本的内容是什么？[/dim]")
    console.print()

    while True:
        try:
            user_input = console.input("[bold cyan]You:[/bold cyan] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Goodbye![/dim]")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit", "q"):
            console.print("[dim]Goodbye![/dim]")
            break

        console.print()
        result = agent.run(user_input)

        if result.success:
            if result.final_message:
                console.print(f"[bold green]Agent:[/bold green] {result.final_message}\n")
            console.print(
                f"[dim]({result.iterations} iterations, {result.tool_calls_made} tool calls)[/dim]\n"
            )
        else:
            print_error(result.error or "Unknown error")
