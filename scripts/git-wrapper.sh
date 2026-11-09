#!/usr/bin/env bash
# Shell function or wrapper for git status integration
# Usage: source scripts/git-wrapper.sh  (defines a `git` function in your shell)
# Or run: scripts/git-wrapper.sh status

git() {
    command git "$@"
    local exit_code=$?
    if [ $exit_code -eq 0 ]; then
        for arg in "$@"; do
            if [ "$arg" = "status" ]; then
                python3 -m minigit.status_indicator 2>/dev/null || true
                break
            elif [[ "$arg" != -* ]]; then
                break
            fi
        done
    fi
    return $exit_code
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    git "$@"
fi

