"""CLI command definitions using Click."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import anthropic

from create_agent.agent.core import Agent
from create_agent.cli.display import (
    console,
    print_banner,
    print_classification_table,
    print_error,
    print_info,
    print_search_results,
    print_success,
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
        config_path: Optional path to config file.

    Returns:
        Configured Agent instance.
    """
    config = load_config(config_path)

    # Initialize Anthropic client
    if not config.api_keys.anthropic:
        print_error(
            "ANTHROPIC_API_KEY is not set. Set it as an environment variable "
            "or in config.yaml (api_keys.anthropic)."
        )
        sys.exit(1)

    client = anthropic.Anthropic(api_key=config.api_keys.anthropic)

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

    # Create agent
    return Agent(
        client=client,
        tools=registry,
        model=config.llm.model,
        max_tokens=config.llm.max_tokens,
        max_iterations=config.agent.max_iterations,
        verbose=config.agent.verbose,
        stream_output=config.agent.stream_output,
    )


def run_classify(folder: str, categories: str, config_path: str | None = None) -> None:
    """Run document classification.

    Args:
        folder: Path to the folder containing documents.
        categories: Comma-separated category names.
    """
    print_banner()
    print_info(f"Folder: {folder}")
    print_info(f"Categories: {categories}")

    agent = _build_agent(config_path)

    task = (
        f"Please classify all documents in '{folder}' into these categories: {categories}.\n\n"
        f"Steps:\n"
        f"1. Scan the folder with scan_folder\n"
        f"2. Extract text from all documents with extract_document_text\n"
        f"3. Classify all documents with classify_documents\n"
        f"4. Organize files into category sub-folders with organize_files\n"
        f"5. Show me a summary of the classification results"
    )

    console.print("\n[bold]Agent is working...[/bold]\n")

    result = agent.run(task)

    if result.success:
        console.print(f"\n[bold]Result:[/bold]\n{result.final_message}")
        console.print(
            f"\n[dim]Completed in {result.iterations} iterations, "
            f"{result.tool_calls_made} tool calls.[/dim]"
        )
    else:
        print_error(result.error or "Unknown error")


def run_search(query: str, max_results: int, config_path: str | None = None) -> None:
    """Run web search.

    Args:
        query: Search query string.
        max_results: Maximum number of results.
    """
    print_banner()
    print_info(f"Search query: {query}")

    agent = _build_agent(config_path)

    task = (
        f"Search the web for: {query}\n\n"
        f"Use the web_search tool with max_results={max_results}. "
        f"After getting results, synthesize them into a clear, concise answer."
    )

    console.print("\n[bold]Searching...[/bold]\n")

    result = agent.run(task)

    if result.success:
        console.print(f"\n[bold]Answer:[/bold]\n{result.final_message}")
    else:
        print_error(result.error or "Unknown error")


def run_ask(folder: str, question: str, config_path: str | None = None) -> None:
    """Ask a question about documents.

    Args:
        folder: Path to the folder containing documents.
        question: Question to answer.
    """
    print_banner()
    print_info(f"Folder: {folder}")
    print_info(f"Question: {question}")

    agent = _build_agent(config_path)

    task = (
        f"In the folder '{folder}', answer this question: {question}\n\n"
        f"Use the search_documents tool to search through the documents "
        f"and find the answer. Present the answer with document references."
    )

    console.print("\n[bold]Searching documents...[/bold]\n")

    result = agent.run(task)

    if result.success:
        console.print(f"\n[bold]Answer:[/bold]\n{result.final_message}")
    else:
        print_error(result.error or "Unknown error")


def run_chat(config_path: str | None = None) -> None:
    """Start an interactive chat session with the agent."""
    print_banner()
    print_info("Interactive chat mode. Type 'exit' or 'quit' to stop.\n")

    agent = _build_agent(config_path)

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
            console.print(f"[bold green]Agent:[/bold green] {result.final_message}\n")
        else:
            print_error(result.error or "Unknown error")
