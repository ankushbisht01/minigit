"""Tests for staging preview colors in ``minigit add``."""

from __future__ import annotations

import minigit.color as color


class _FakeTTY:
    def isatty(self) -> bool:
        return True


def test_staging_preview_colored_when_tty(repo, run, write, monkeypatch):
    """Tracked files are green and untracked files are red when TTY is active."""
    write("a.txt", "hello\n")
    write("b.txt", "world\n")

    monkeypatch.setattr(color.sys.stdout, "isatty", lambda: True)
    monkeypatch.delenv("NO_COLOR", raising=False)
    color._force_off = False

    result = run("add", "a.txt")
    assert result.code == 0
    assert "Tracked files:" in result.out
    assert "\t\033[32ma.txt\033[0m" in result.out
    assert "Untracked files:" in result.out
    assert "\t\033[31mb.txt\033[0m" in result.out


def test_staging_preview_uncolored_when_not_tty(repo, run, write):
    """When stdout is not a TTY, output is plain text without ANSI codes."""
    write("a.txt", "hello\n")
    write("b.txt", "world\n")

    result = run("add", "a.txt")
    assert result.code == 0
    assert result.out == "Tracked files:\n\ta.txt\n\nUntracked files:\n\tb.txt\n"


def test_staging_preview_no_color_flag(repo, run, write, monkeypatch):
    """--no-color disables ANSI escape codes even when stdout is a TTY."""
    write("a.txt", "hello\n")
    write("b.txt", "world\n")

    monkeypatch.setattr(color.sys.stdout, "isatty", lambda: True)
    monkeypatch.delenv("NO_COLOR", raising=False)

    result = run("--no-color", "add", "a.txt")
    assert result.code == 0
    assert "\033[" not in result.out
    assert result.out == "Tracked files:\n\ta.txt\n\nUntracked files:\n\tb.txt\n"


def test_staging_preview_no_color_env_var(repo, run, write, monkeypatch):
    """NO_COLOR environment variable disables ANSI escape codes."""
    write("a.txt", "hello\n")
    write("b.txt", "world\n")

    monkeypatch.setattr(color.sys.stdout, "isatty", lambda: True)
    monkeypatch.setenv("NO_COLOR", "1")

    result = run("add", "a.txt")
    assert result.code == 0
    assert "\033[" not in result.out
    assert "Tracked files:\n\ta.txt" in result.out
    assert "Untracked files:\n\tb.txt" in result.out


def test_staging_preview_all_tracked(repo, run, write, monkeypatch):
    """When all files are staged, untracked files section is omitted."""
    write("a.txt", "hello\n")
    write("b.txt", "world\n")

    monkeypatch.setattr(color.sys.stdout, "isatty", lambda: True)
    monkeypatch.delenv("NO_COLOR", raising=False)
    color._force_off = False

    result = run("add", ".")
    assert result.code == 0
    assert "Tracked files:" in result.out
    assert "\t\033[32ma.txt\033[0m" in result.out
    assert "\t\033[32mb.txt\033[0m" in result.out
    assert "Untracked files:" not in result.out


def test_staging_preview_after_deletion(repo, run, write, monkeypatch):
    """Staging removal of a file updates the tracked files preview."""
    write("a.txt", "hello\n")
    write("b.txt", "world\n")
    run("add", ".")

    (repo.worktree / "a.txt").unlink()

    monkeypatch.setattr(color.sys.stdout, "isatty", lambda: True)
    monkeypatch.delenv("NO_COLOR", raising=False)
    color._force_off = False

    result = run("add", ".")
    assert result.code == 0
    assert "Tracked files:" in result.out
    assert "\t\033[32mb.txt\033[0m" in result.out
    assert "a.txt" not in result.out
