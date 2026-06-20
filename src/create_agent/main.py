"""Entry point for create-agent CLI."""

from __future__ import annotations

import click

from create_agent.cli.commands import run_ask, run_chat, run_classify, run_search


@click.group()
@click.option(
    "--config",
    "-c",
    default=None,
    help="Path to config.yaml file.",
    type=click.Path(exists=True),
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output.")
@click.pass_context
def main(ctx: click.Context, config: str | None, verbose: bool) -> None:
    """create-agent: Document classification, search, and Q&A agent.

    An intelligent agent that can classify documents, search the web,
    and answer questions about your files.

    \b
    Examples:
      create-agent classify --folder ./docs --categories "Contract,Invoice,Report"
      create-agent search --query "latest AI regulation news 2026"
      create-agent ask --folder ./reports --question "What was Q4 revenue?"
      create-agent chat
    """
    ctx.ensure_object(dict)
    ctx.obj["config"] = config
    ctx.obj["verbose"] = verbose


@main.command()
@click.option(
    "--folder",
    "-f",
    required=True,
    help="Folder containing documents to classify.",
    type=click.Path(exists=True, file_okay=False),
)
@click.option(
    "--categories",
    "-c",
    required=True,
    help="Comma-separated category names (e.g. 'Contract,Invoice,Report').",
)
@click.pass_context
def classify(ctx: click.Context, folder: str, categories: str) -> None:
    """Classify documents into categories and organize into sub-folders.

    Scans the folder for .docx, .pptx, .pdf files, extracts text,
    classifies each document using AI, and moves files into category
    sub-folders.
    """
    run_classify(
        folder=folder,
        categories=categories,
        config_path=ctx.obj.get("config"),
    )


@main.command()
@click.option(
    "--query",
    "-q",
    required=True,
    help="Search query string.",
)
@click.option(
    "--max-results",
    "-n",
    default=5,
    type=int,
    help="Maximum number of search results (1-20).",
)
@click.pass_context
def search(ctx: click.Context, query: str, max_results: int) -> None:
    """Search the web using Tavily and get AI-synthesized answers."""
    run_search(
        query=query,
        max_results=max_results,
        config_path=ctx.obj.get("config"),
    )


@main.command()
@click.option(
    "--folder",
    "-f",
    required=True,
    help="Folder containing documents to search.",
    type=click.Path(exists=True, file_okay=False),
)
@click.option(
    "--question",
    "-q",
    required=True,
    help="Question to answer based on document content.",
)
@click.pass_context
def ask(ctx: click.Context, folder: str, question: str) -> None:
    """Ask a question about documents in a folder.

    Extracts text from all documents and uses AI to answer your question
    with references to source documents.
    """
    run_ask(
        folder=folder,
        question=question,
        config_path=ctx.obj.get("config"),
    )


@main.command()
@click.pass_context
def chat(ctx: click.Context) -> None:
    """Start an interactive chat session with the agent.

    Chat with the agent naturally — it can classify, search, and
    answer questions as needed.
    """
    run_chat(config_path=ctx.obj.get("config"))


if __name__ == "__main__":
    main()
