"""Rich console output formatting for create-agent."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


def print_banner() -> None:
    """Print the application banner."""
    console.print(
        Panel.fit(
            "[bold cyan]create-agent[/bold cyan] — "
            "Document classification, search, and Q&A agent",
            border_style="cyan",
        )
    )


def print_error(message: str) -> None:
    """Print an error message."""
    console.print(f"[bold red]Error:[/bold red] {message}")


def print_warning(message: str) -> None:
    """Print a warning message."""
    console.print(f"[bold yellow]Warning:[/bold yellow] {message}")


def print_success(message: str) -> None:
    """Print a success message."""
    console.print(f"[bold green]✓[/bold green] {message}")


def print_info(message: str) -> None:
    """Print an informational message."""
    console.print(f"[dim]{message}[/dim]")


def print_classification_table(classifications: list[dict]) -> None:
    """Print classification results as a Rich table.

    Args:
        classifications: List of {file_path, category, confidence, reasoning} dicts.
    """
    if not classifications:
        print_warning("No classifications to display.")
        return

    table = Table(
        title="Classification Results",
        title_style="bold cyan",
        border_style="dim",
    )
    table.add_column("File", style="cyan", no_wrap=False)
    table.add_column("Category", style="green")
    table.add_column("Confidence", style="yellow")
    table.add_column("Reasoning", style="dim", no_wrap=False)

    for c in classifications:
        confidence_style = {
            "high": "[green]high[/green]",
            "medium": "[yellow]medium[/yellow]",
            "low": "[red]low[/red]",
        }.get(c.get("confidence", "low"), "low")
        table.add_row(
            c.get("file_path", ""),
            c.get("category", ""),
            confidence_style,
            c.get("reasoning", ""),
        )

    console.print(table)


def print_search_results(results: list[dict]) -> None:
    """Print web search results as a Rich table.

    Args:
        results: List of {title, url, content, score} dicts.
    """
    if not results:
        print_warning("No search results.")
        return

    for i, r in enumerate(results, 1):
        console.print(f"\n[bold cyan]{i}.[/bold cyan] [bold]{r.get('title', 'No title')}[/bold]")
        console.print(f"   [dim]{r.get('url', '')}[/dim]")
        content = r.get("content", "")
        if len(content) > 300:
            content = content[:300] + "..."
        console.print(f"   {content}")


def print_agent_progress(text: str) -> None:
    """Print agent thinking/action progress."""
    console.print(f"  [dim italic]{text}[/dim italic]")


def create_spinner(message: str = "Processing...") -> Progress:
    """Create a Rich progress spinner.

    Args:
        message: Text to display next to the spinner.

    Returns:
        A Progress context manager.
    """
    return Progress(
        SpinnerColumn(),
        TextColumn(f"[dim]{message}[/dim]"),
        console=console,
    )
