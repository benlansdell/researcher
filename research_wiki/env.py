from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv


def load_env(vault: Path | None = None) -> None:
    """Load `.env` files without overriding variables already in the environment.

    Precedence (highest first): existing environment, vault `.env`, cwd `.env`.
    """
    paths: list[Path] = []
    if vault is not None:
        paths.append(vault / ".env")
    cwd_env = Path.cwd() / ".env"
    if not paths or cwd_env.resolve() != paths[0].resolve():
        paths.append(cwd_env)
    for path in paths:
        if path.is_file():
            load_dotenv(path, override=False)
