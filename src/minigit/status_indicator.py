"""Visual file-status indicator for minigit and git.

Generates and maintains `file-status.md` in the repository root,
displaying tracked files in green and untracked files in red.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from minigit.repo import Repository

STATUS_FILENAME = "file-status.md"


def format_file_entry(path: str, color: str) -> str:
    """Format a single filename as a markdown list item with color styling.

    Uses HTML span styling to ensure the color renders across markdown previewers
    while retaining code backtick formatting.
    """
    if "`" in path:
        code_span = f"`` {path} ``"
    else:
        code_span = f"`{path}`"
    return f'- <span style="color: {color};">{code_span}</span>'


def format_status_markdown(tracked_files: list[str], untracked_files: list[str]) -> str:
    """Generate the full markdown content for file-status.md.

    Contains two sections:
    - 🔴 Untracked Files (filenames in red)
    - 🟢 Tracked Files (filenames in green)
    """
    lines: list[str] = ["**🔴 Untracked Files**"]
    for path in sorted(set(untracked_files)):
        lines.append(format_file_entry(path, "red"))

    lines.append("")
    lines.append("**🟢 Tracked Files**")
    for path in sorted(set(tracked_files)):
        lines.append(format_file_entry(path, "green"))

    return "\n".join(lines) + "\n"


def get_status_from_minigit(repo: Repository) -> tuple[list[str], list[str]]:
    """Determine tracked and untracked files for a minigit repository."""
    from minigit.changes import staged_changes, untracked_files
    from minigit.index import Index
    from minigit.objects import flatten_tree, peel_to_tree
    from minigit.refs import head_commit

    # Tracked files: anything in HEAD or the index, excluding staged deletions
    tracked_candidates: set[str] = set()

    head = head_commit(repo)
    if head is not None:
        try:
            head_candidates = flatten_tree(repo, peel_to_tree(repo, head)).keys()
            tracked_candidates.update(head_candidates)
        except Exception:
            pass

    for entry in Index.load(repo):
        tracked_candidates.add(entry.path)

    # Exclude files staged for deletion
    try:
        staged = staged_changes(repo)
        for path, state in staged.items():
            if state == "deleted":
                tracked_candidates.discard(path)
    except Exception:
        pass

    # Tracked files must currently exist on disk in the working tree
    tracked = [
        path
        for path in tracked_candidates
        if path != STATUS_FILENAME and (repo.worktree / path).is_file()
    ]

    # Untracked files in working tree
    untracked = [
        path
        for path in untracked_files(repo)
        if path != STATUS_FILENAME and (repo.worktree / path).is_file()
    ]

    return sorted(set(tracked)), sorted(set(untracked))


def get_status_from_git(repo_root: Path) -> tuple[list[str], list[str]]:
    """Determine tracked and untracked files using git command line."""
    # Tracked files: git ls-files -z
    tracked_raw = subprocess.check_output(["git", "ls-files", "-z"], cwd=repo_root)
    tracked_all = [p for p in tracked_raw.decode("utf-8", errors="replace").split("\0") if p]
    tracked = [
        p
        for p in tracked_all
        if p != STATUS_FILENAME and (repo_root / p).is_file()
    ]

    # Untracked files: git ls-files --others --exclude-standard -z
    untracked_raw = subprocess.check_output(
        ["git", "ls-files", "--others", "--exclude-standard", "-z"],
        cwd=repo_root,
    )
    untracked_all = [p for p in untracked_raw.decode("utf-8", errors="replace").split("\0") if p]
    untracked = [
        p
        for p in untracked_all
        if p != STATUS_FILENAME and (repo_root / p).is_file()
    ]

    return sorted(set(tracked)), sorted(set(untracked))


def ensure_git_exclude(repo_root: Path) -> None:
    """Ensure file-status.md is ignored by Git locally via .git/info/exclude."""
    git_dir = repo_root / ".git"
    if git_dir.is_dir():
        exclude_file = git_dir / "info" / "exclude"
        try:
            exclude_file.parent.mkdir(parents=True, exist_ok=True)
            current = exclude_file.read_text(encoding="utf-8") if exclude_file.exists() else ""
            if STATUS_FILENAME not in current.splitlines():
                with exclude_file.open("a", encoding="utf-8") as f:
                    if current and not current.endswith("\n"):
                        f.write("\n")
                    f.write(f"{STATUS_FILENAME}\n")
        except Exception:
            pass


def update_file_status(repo: Repository | Path | str | None = None) -> Path | None:
    """Generate or update file-status.md in the repository root."""
    repo_root: Path | None = None
    minigit_repo: Repository | None = None

    if repo is not None and hasattr(repo, "worktree"):
        minigit_repo = repo
        repo_root = repo.worktree
    elif repo is not None:
        repo_root = Path(repo).resolve()
    else:
        # Check if in a minigit repository
        try:
            from minigit.repo import Repository as MiniRepo
            minigit_repo = MiniRepo.find()
            repo_root = minigit_repo.worktree
        except Exception:
            minigit_repo = None

        if repo_root is None:
            # Check if in a git repository
            try:
                out = subprocess.check_output(
                    ["git", "rev-parse", "--show-toplevel"],
                    stderr=subprocess.DEVNULL,
                    text=True,
                ).strip()
                if out:
                    repo_root = Path(out).resolve()
            except Exception:
                repo_root = None

    if repo_root is None:
        return None

    tracked: list[str] = []
    untracked: list[str] = []

    if (repo_root / ".git").is_dir():
        ensure_git_exclude(repo_root)
        try:
            tracked, untracked = get_status_from_git(repo_root)
        except Exception:
            if minigit_repo is not None:
                tracked, untracked = get_status_from_minigit(minigit_repo)
    elif minigit_repo is not None or (repo_root / ".minigit").is_dir():
        if minigit_repo is None:
            from minigit.repo import Repository as MiniRepo
            minigit_repo = MiniRepo(repo_root)
        tracked, untracked = get_status_from_minigit(minigit_repo)
    else:
        return None

    content = format_status_markdown(tracked, untracked)
    target = repo_root / STATUS_FILENAME

    # Avoid writing if content is unchanged (prevents infinite loops / unnecessary I/O)
    if target.exists():
        try:
            if target.read_text(encoding="utf-8") == content:
                return target
        except Exception:
            pass

    target.write_text(content, encoding="utf-8")
    return target


if __name__ == "__main__":
    update_file_status()

