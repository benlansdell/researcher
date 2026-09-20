import os
from pathlib import Path

from research_wiki.env import load_env


def test_load_env_reads_vault_dotenv(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / ".env").write_text("OPENAI_API_KEY=sk-from-vault\n")
    load_env(vault)
    assert os.environ["OPENAI_API_KEY"] == "sk-from-vault"


def test_load_env_does_not_override_existing(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-from-shell")
    (tmp_path / ".env").write_text("OPENAI_API_KEY=sk-from-file\n")
    load_env(tmp_path)
    assert os.environ["OPENAI_API_KEY"] == "sk-from-shell"


def test_vault_dotenv_beats_cwd(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    cwd = tmp_path / "cwd"
    vault = tmp_path / "vault"
    cwd.mkdir()
    vault.mkdir()
    monkeypatch.chdir(cwd)
    (cwd / ".env").write_text("OPENAI_API_KEY=sk-from-cwd\n")
    (vault / ".env").write_text("OPENAI_API_KEY=sk-from-vault\n")
    load_env(vault)
    assert os.environ["OPENAI_API_KEY"] == "sk-from-vault"
