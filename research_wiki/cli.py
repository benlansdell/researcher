from __future__ import annotations

import time
import difflib
from pathlib import Path
import typer
from rich.console import Console
from rich.table import Table

from .config import AppConfig
from .processor import Processor

app = typer.Typer(no_args_is_help=True, help="LLM-powered curator for Obsidian Markdown vaults.")
console = Console()


def _vault(path: str) -> Path:
    p = Path(path).expanduser().resolve()
    if not p.exists() or not p.is_dir():
        raise typer.BadParameter(f"Vault does not exist or is not a directory: {p}")
    return p


@app.command()
def init(vault: str):
    """Initialize config/state directories in a vault."""
    root = _vault(vault)
    cfg = AppConfig()
    path = cfg.save(root)
    (root / cfg.processing.research_dir).mkdir(parents=True, exist_ok=True)
    (root / cfg.processing.research_runs_dir).mkdir(parents=True, exist_ok=True)
    (root / ".research-wiki").mkdir(parents=True, exist_ok=True)
    console.print(f"Initialized [bold]{root}[/bold]")
    console.print(f"Config: {path}")


@app.command()
def process(
    vault: str,
    dry_run: bool = typer.Option(False, "--dry-run", help="Show proposed changes without writing."),
    file: str | None = typer.Option(None, "--file", help="Process one vault-relative source note."),
):
    """Process changed source notes."""
    root = _vault(vault)
    result = Processor(root).process(dry_run=dry_run, only_file=file)
    table = Table(title="Proposed changes" if dry_run else "Applied changes")
    table.add_column("Action")
    table.add_column("Path")
    for change in result.changes:
        table.add_row(change.action, change.path)
    console.print(table)
    if dry_run and result.changes:
        console.print("\n[bold]Diffs[/bold]")
        # Show the final proposed content for each path.
        final_by_path = {c.path: c for c in result.changes}
        for relpath, change in final_by_path.items():
            path = root / relpath
            before = path.read_text(encoding="utf-8") if path.exists() else ""
            diff = difflib.unified_diff(
                before.splitlines(),
                change.content.splitlines(),
                fromfile=f"a/{relpath}",
                tofile=f"b/{relpath}",
                lineterm="",
            )
            console.print("\n" + "\n".join(diff))
    console.print(f"Changes: {len(result.changes)}; unchanged/skipped: {len(result.skipped)}")


class _Handler:
    def __init__(self, root: Path, debounce_seconds: float = 1.5):
        self.root = root
        self.debounce = debounce_seconds
        self.last = 0.0

    def on_any_event(self, event):
        if event.is_directory or not event.src_path.endswith(".md"):
            return
        now = time.monotonic()
        if now - self.last < self.debounce:
            return
        self.last = now
        try:
            result = Processor(self.root).process()
            if result.changes:
                console.print(f"[green]Processed {len(result.changes)} change(s).[/green]")
        except Exception as exc:
            console.print(f"[red]Processing failed:[/red] {exc}")


@app.command()
def watch(vault: str):
    """Watch a vault and process changed Markdown notes."""
    root = _vault(vault)
    console.print(f"Watching {root}. Press Ctrl-C to stop.")
    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler
    except ImportError as exc:
        raise typer.BadParameter("watch mode requires watchdog; install package dependencies first") from exc

    # Dynamically adapt our handler so importing the CLI does not require watchdog.
    class Handler(FileSystemEventHandler, _Handler):
        def __init__(self, root):
            FileSystemEventHandler.__init__(self)
            _Handler.__init__(self, root)

    handler = Handler(root)
    observer = Observer()
    observer.schedule(handler, str(root), recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
