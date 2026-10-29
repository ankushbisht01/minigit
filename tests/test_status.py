"""Tests for what ``minigit status`` prints."""

import minigit.color as color
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


def test_status_uses_color_when_terminal(repo, run, write, monkeypatch):
    # Pretend stdout is a terminal so the color helpers emit ANSI codes.
    monkeypatch.setattr(color, "_should_color", lambda: True)

    write("a.txt", "a\n")
    run("add", "a.txt")
    write("a.txt", "changed\n")
    write("loose.txt", "x\n")

    out = run("status").out
    assert "\033[1mChanges to be committed:\033[0m" in out
    assert "\033[32m\tnew file:   a.txt\033[0m" in out
    assert "\033[31m\tmodified:   a.txt\033[0m" in out
    assert "\033[31m\tloose.txt\033[0m" in out


def test_status_has_no_color_codes_by_default(repo, run, write):
    write("a.txt", "a\n")
    run("add", "a.txt")
    out = run("status").out
    assert "\033[" not in out
