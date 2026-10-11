#!/usr/bin/env bash
# Report any git repos in this directory that are dirty or have unpushed commits.
# Uses the last-fetched remote state (no network access).

cd "$(dirname "$0")" || exit 1

problems=0
for dir in */; do
    dir="${dir%/}"
    [ -d "$dir/.git" ] || continue

    issues=()
    [ -n "$(git -C "$dir" status --porcelain)" ] && issues+=("uncommitted changes")
    [ -n "$(git -C "$dir" log --branches --not --remotes --oneline)" ] && issues+=("unpushed commits")
    git -C "$dir" rev-parse --abbrev-ref '@{upstream}' &>/dev/null || issues+=("no upstream branch")

    if [ ${#issues[@]} -gt 0 ]; then
        problems=1
        printf '%s: %s\n' "$dir" "$(IFS=,; echo "${issues[*]}" | sed 's/,/, /g')"
    fi
done

[ "$problems" -eq 0 ] && echo "All repos are committed and pushed."
exit "$problems"
