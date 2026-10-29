"""minigit add: stage file contents for the next commit.

For each file, ``add`` stores its content as a blob object and records
``path -> blob sha`` in the index.
"""

import argparse
from pathlib import Path

from minigit import color
from minigit.changes import untracked_files
from minigit.errors import MinigitError
from minigit.index import Index, IndexEntry
from minigit.objects import FILE_MODE, write_object
from minigit.repo import Repository
from minigit.worktree import iter_files, repo_relative

NAME = "add"
HELP = "Add file contents to the staging area"


def configure(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("paths", nargs="+", help="files or directories to stage")


def run(args: argparse.Namespace, repo: Repository | None) -> int:
    assert repo is not None
    index = Index.load(repo)
    for raw in args.paths:
        _stage_deletions(index, repo, raw)
        if not Path(raw).exists():
            continue
        for path in _expand(repo, raw):
            sha = write_object(repo, (repo.worktree / path).read_bytes(), "blob")
            index.add(IndexEntry(FILE_MODE, sha, path))
    index.save(repo)
    _print_preview(repo, index)
    return 0


def _print_preview(repo: Repository, index: Index) -> None:
    """Print preview showing tracked files in green and untracked files in red."""
    tracked = [e.path for e in index]
    untracked = untracked_files(repo)
    lines: list[str] = []
    if tracked:
        lines.append("Tracked files:")
        lines.extend(f"\t{color.green(path)}" for path in tracked)
    if untracked:
        if lines:
            lines.append("")
        lines.append("Untracked files:")
        lines.extend(f"\t{color.red(path)}" for path in untracked)
    if lines:
        print("\n".join(lines))


def _stage_deletions(index, repo, raw):
    """Remove staged entries under ``raw`` whose files no longer exist on disk.

    Raises if ``raw`` doesn't exist and nothing staged matches it.
    """
    relative = repo_relative(repo, raw)
    deleted = [
        e.path
        for e in index
        if (relative == "" or e.path == relative or e.path.startswith(relative + "/"))
        and not (repo.worktree / e.path).exists()
    ]
    for path in deleted:
        index.remove(path)
    if not deleted and not Path(raw).exists():
        raise MinigitError(f"pathspec '{raw}' did not match any files")


def _expand(repo, raw):
    """Turn one path argument into the list of files it names."""
    path = Path(raw)
    relative = repo_relative(repo, path)
    if not path.is_dir():
        return [relative]
    prefix = f"{relative}/" if relative else ""
    return [f for f in iter_files(repo) if f.startswith(prefix)]
