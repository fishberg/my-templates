#!/usr/bin/env bash
# Fetch each git repo in this directory and report any that are behind their remote.

cd "$(dirname "$0")" || exit 1

problems=0
for dir in */; do
    dir="${dir%/}"
    [ -d "$dir/.git" ] || continue

    if ! git -C "$dir" rev-parse --abbrev-ref '@{upstream}' &>/dev/null; then
        echo "$dir: no upstream branch"
        problems=1
        continue
    fi

    if ! git -C "$dir" fetch --quiet; then
        echo "$dir: fetch failed"
        problems=1
        continue
    fi

    behind="$(git -C "$dir" rev-list --count 'HEAD..@{upstream}')"
    if [ "$behind" -gt 0 ]; then
        echo "$dir: behind remote by $behind commit(s) (needs pull)"
        problems=1
    fi
done

[ "$problems" -eq 0 ] && echo "All repos are up-to-date with their remotes."
exit "$problems"
