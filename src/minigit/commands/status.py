"""minigit status: what's staged, what isn't, and what isn't tracked at all.

The comparing is done by ``minigit.changes``; this file only prints.
"""

from minigit import color
from minigit.changes import staged_changes, unstaged_changes, untracked_files
from minigit.refs import current_branch, head_commit

NAME = "status"
HELP = "Show staged, unstaged and untracked files"

# Git lines these up in a 12-character column.
_LABELS = {"added": "new file:", "modified": "modified:", "deleted": "deleted:"}


def configure(parser):
    pass


def _header(repo) -> list[str]:
    branch = current_branch(repo)
    sha = head_commit(repo)
    if branch is None:
        # A detached HEAD always holds a commit SHA.
        assert sha is not None
        return [f"HEAD detached at {sha[:7]}"]
    if sha is None:
        # Git puts a blank line on either side of this line.
        return [f"On branch {branch}", "", "No commits yet", ""]
    return [f"On branch {branch}"]


def _section(title: str, changes: dict[str, str], entry_color) -> list[str]:
    if not changes:
        return []
    lines = [color.bold(title)]
    lines += [
        entry_color(f"\t{_LABELS[state]:<12}{path}") for path, state in sorted(changes.items())
    ]
    return lines + [""]


def run(args, repo):
    staged = staged_changes(repo)
    unstaged = unstaged_changes(repo)
    untracked = untracked_files(repo)

    lines = _header(repo)
    lines += _section("Changes to be committed:", staged, color.green)
    lines += _section("Changes not staged for commit:", unstaged, color.red)
    if untracked:
        lines += (
            [color.bold("Untracked files:")] + [color.red(f"\t{path}") for path in untracked] + [""]
        )
    if not (staged or unstaged or untracked):
        lines.append("nothing to commit, working tree clean")

    print("\n".join(lines).rstrip("\n"))
    return 0
