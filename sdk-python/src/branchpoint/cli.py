"""branchpoint CLI.

Subcommands:
    branchpoint dashboard           Open the web UI at http://localhost:3089
    branchpoint sessions list       List all sessions
    branchpoint session show <id>   Show a session's events
    branchpoint session export <id> Export a session as JSON/YAML

Full implementation lands in Session 5 (dashboard) and later sessions.
"""
from __future__ import annotations

import sys

import click
from rich.console import Console
from rich.table import Table


console = Console()


@click.group()
@click.version_option()
def main() -> None:
    """Time-travel debugger for AI agents."""
    pass


@main.command()
@click.option("--port", default=3089, help="Port for the web UI")
@click.option("--no-open", is_flag=True, help="Don't open the browser")
def dashboard(port: int, no_open: bool) -> None:
    """Open the branchpoint dashboard in your browser."""
    console.print(
        "[yellow]Dashboard not yet implemented (Session 5).[/yellow]\n"
        f"Will launch at [cyan]http://localhost:{port}[/cyan]"
    )
    sys.exit(0)


@main.group()
def sessions() -> None:
    """List and inspect recorded sessions."""
    pass


@sessions.command("list")
def sessions_list() -> None:
    """List all recorded sessions."""
    # Session 2 will implement: scan ~/.branchpoint/sessions/ and print a table
    table = Table(title="Recorded sessions")
    table.add_column("Session", style="cyan")
    table.add_column("Name")
    table.add_column("Status")
    table.add_column("Cost (USD)", justify="right")
    table.add_column("Duration")
    console.print(table)
    console.print("[dim]No sessions yet — record one first.[/dim]")


if __name__ == "__main__":
    main()
