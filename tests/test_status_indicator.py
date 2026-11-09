"""Tests for the visual file-status indicator (file-status.md)."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from minigit.status_indicator import (
    STATUS_FILENAME,
    format_file_entry,
    format_status_markdown,
    update_file_status,
)


def test_markdown_formatting():
    tracked = ["index.html", "app.js", "README.md"]
    untracked = ["new-feature.js", "test.py"]
    content = format_status_markdown(tracked, untracked)

    assert "**🔴 Untracked Files**" in content
    assert '<span style="color: red;">`new-feature.js`</span>' in content
    assert '<span style="color: red;">`test.py`</span>' in content

    assert "**🟢 Tracked Files**" in content
    assert '<span style="color: green;">`index.html`</span>' in content
    assert '<span style="color: green;">`app.js`</span>' in content
    assert '<span style="color: green;">`README.md`</span>' in content

    # Check ordering
    assert content.index("**🔴 Untracked Files**") < content.index("**🟢 Tracked Files**")


def test_special_characters_formatting():
    entry_space = format_file_entry("file with spaces.txt", "red")
    assert '<span style="color: red;">`file with spaces.txt`</span>' in entry_space

    entry_backtick = format_file_entry("file`tick.txt", "green")
    assert '<span style="color: green;">`` file`tick.txt ``</span>' in entry_backtick


def test_status_generates_file_status_md(repo, run, write):
    write("index.html", "<html></html>\n")
    write("app.js", "console.log(1);\n")
    write("README.md", "# Hello\n")
    run("add", "index.html", "app.js", "README.md")
    run("commit", "-m", "Initial commit")

    write("new-feature.js", "export const x = 1;\n")
    write("test.py", "print('test')\n")

    res = run("status")
    assert res.code == 0

    status_file = repo.worktree / STATUS_FILENAME
    assert status_file.is_file()
    content = status_file.read_text(encoding="utf-8")

    # Check untracked files in red
    assert "**🔴 Untracked Files**" in content
    assert '<span style="color: red;">`new-feature.js`</span>' in content
    assert '<span style="color: red;">`test.py`</span>' in content

    # Check tracked files in green
    assert "**🟢 Tracked Files**" in content
    assert '<span style="color: green;">`app.js`</span>' in content
    assert '<span style="color: green;">`index.html`</span>' in content
    assert '<span style="color: green;">`README.md`</span>' in content

    # file-status.md itself must never be listed
    assert f"`{STATUS_FILENAME}`" not in content
    # Normal minigit status output must not include file-status.md
    assert STATUS_FILENAME not in res.out


def test_live_updates_when_files_staged(repo, run, write):
    write("test.py", "print(1)\n")
    run("status")

    status_file = repo.worktree / STATUS_FILENAME
    content = status_file.read_text(encoding="utf-8")
    assert '<span style="color: red;">`test.py`</span>' in content

    # Stage the file
    run("add", "test.py")
    run("status")

    content_after = status_file.read_text(encoding="utf-8")
    # Now it should be in tracked, not untracked
    assert '<span style="color: green;">`test.py`</span>' in content_after
    assert '<span style="color: red;">`test.py`</span>' not in content_after


def test_live_updates_when_files_deleted(repo, run, write):
    write("keep.txt", "keep\n")
    write("remove.txt", "remove\n")
    run("add", "keep.txt", "remove.txt")
    run("commit", "-m", "Add two files")

    run("status")
    status_file = repo.worktree / STATUS_FILENAME
    assert "remove.txt" in status_file.read_text(encoding="utf-8")

    # Delete remove.txt
    (repo.worktree / "remove.txt").unlink()
    run("status")

    content_after = status_file.read_text(encoding="utf-8")
    assert "remove.txt" not in content_after
    assert "keep.txt" in content_after


def test_live_updates_when_files_renamed(repo, run, write):
    write("old_name.txt", "content\n")
    run("add", "old_name.txt")
    run("commit", "-m", "Commit old name")

    # Rename
    (repo.worktree / "old_name.txt").unlink()
    write("new_name.txt", "content\n")
    run("add", "new_name.txt")

    run("status")
    status_file = repo.worktree / STATUS_FILENAME
    content = status_file.read_text(encoding="utf-8")
    assert "old_name.txt" not in content
    assert '<span style="color: green;">`new_name.txt`</span>' in content


def test_ignored_files_not_classified_as_untracked(repo, run, write):
    write(".gitignore", "*.log\nbuild/\n")
    run("add", ".gitignore")
    run("commit", "-m", "Add gitignore")

    write("error.log", "some error\n")
    write("valid.py", "print(1)\n")

    run("status")
    status_file = repo.worktree / STATUS_FILENAME
    content = status_file.read_text(encoding="utf-8")

    assert "error.log" not in content
    assert '<span style="color: red;">`valid.py`</span>' in content


def test_git_wrapper_execution(workdir):
    """Test bin/git wrapper running on a real git repository."""
    # Initialize a real git repo
    subprocess.run(["git", "init", "-b", "main"], cwd=workdir, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=workdir, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=workdir, check=True)

    # Create tracked files
    (workdir / "index.html").write_text("hello", encoding="utf-8")
    subprocess.run(["git", "add", "index.html"], cwd=workdir, check=True)
    subprocess.run(["git", "commit", "-m", "Initial"], cwd=workdir, check=True)

    # Create untracked file
    (workdir / "new-feature.js").write_text("console.log(1)", encoding="utf-8")

    # Run wrapper
    wrapper_bin = Path(__file__).resolve().parent.parent / "bin" / "git"
    result = subprocess.run([str(wrapper_bin), "status"], cwd=workdir, capture_output=True, text=True)
    assert result.returncode == 0

    status_file = workdir / STATUS_FILENAME
    assert status_file.is_file()
    content = status_file.read_text(encoding="utf-8")

    assert '<span style="color: red;">`new-feature.js`</span>' in content
    assert '<span style="color: green;">`index.html`</span>' in content

