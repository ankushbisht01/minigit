"""Tests for what ``minigit status`` prints."""

import sys

from minigit.refs import head_commit, set_head


def test_clean_repository(repo, run, write):
    write("a.txt", "a\n")
    run("add", "a.txt")
    run("commit", "-m", "first")
    result = run("status")
    assert result.code == 0
    assert result.out == "On branch main\nnothing to commit, working tree clean\n"


def test_empty_repository_says_no_commits_yet(repo, run):
    out = run("status").out
    assert out.startswith("On branch main\n\nNo commits yet\n")
    assert "nothing to commit, working tree clean" in out


def test_staged_section(repo, run, write):
    write("notes.txt", "n\n")
    run("add", "notes.txt")
    out = run("status").out
    assert "Changes to be committed:" in out
    assert "\tnew file:   notes.txt" in out


def test_all_three_sections(repo, run, write):
    write("hello.txt", "hello\n")
    write("old.txt", "old\n")
    run("add", "hello.txt", "old.txt")
    run("commit", "-m", "first")

    write("hello.txt", "staged edit\n")
    run("add", "hello.txt")
    write("hello.txt", "unstaged edit\n")
    (repo.worktree / "old.txt").unlink()
    write("scratch.py", "print(1)\n")

    out = run("status").out
    assert "\tmodified:   hello.txt" in out
    assert "\tdeleted:    old.txt" in out
    assert "\tscratch.py" in out
    assert out.index("Changes to be committed:") < out.index("Changes not staged for commit:")
    assert out.index("Changes not staged for commit:") < out.index("Untracked files:")


def test_detached_head(repo, run, write):
    write("a.txt", "a\n")
    run("add", "a.txt")
    run("commit", "-m", "first")
    commit = head_commit(repo)
    set_head(repo, commit, symbolic=False)
    assert run("status").out.startswith(f"HEAD detached at {commit[:7]}")


# ── colours ───────────────────────────────────────────────────────────────────

GREEN, RED, RESET = "\033[32m", "\033[31m", "\033[0m"


def _mixed_changes(run, write):
    """Leave one staged, one unstaged and one untracked file in the worktree."""
    write("tracked.txt", "one\n")
    run("add", "tracked.txt")
    run("commit", "-m", "first")
    write("tracked.txt", "one\ntwo\n")
    write("staged.txt", "s\n")
    run("add", "staged.txt")
    write("new.txt", "n\n")


def _pretend_terminal(monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)


def test_status_colours_entries_on_a_terminal(repo, run, write, monkeypatch):
    _mixed_changes(run, write)
    _pretend_terminal(monkeypatch)
    out = run("status").out
    assert f"\t{GREEN}new file:   staged.txt{RESET}" in out
    assert f"\t{RED}modified:   tracked.txt{RESET}" in out
    assert f"\t{RED}new.txt{RESET}" in out
    # Section titles stay plain, as in Git.
    assert "\nChanges to be committed:\n" in out


def test_status_no_color_flag(repo, run, write, monkeypatch):
    _mixed_changes(run, write)
    _pretend_terminal(monkeypatch)
    assert "\033[" not in run("--no-color", "status").out


def test_status_no_color_env(repo, run, write, monkeypatch):
    _mixed_changes(run, write)
    _pretend_terminal(monkeypatch)
    monkeypatch.setenv("NO_COLOR", "1")
    assert "\033[" not in run("status").out
