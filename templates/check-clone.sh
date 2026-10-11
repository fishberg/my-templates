#!/usr/bin/env bash
# Compare the repos listed in ../index.toml against the git repos in this directory.

cd "$(dirname "$0")" || exit 1

listed="$(python3 -c 'import tomllib; print(*(u.rstrip("/").removesuffix(".git").rsplit("/", 1)[-1] for u in tomllib.load(open("../index.toml", "rb"))["repos"]), sep="\n")')" || exit 1
present="$(for dir in */; do [ -d "$dir/.git" ] && echo "${dir%/}"; done)"

problems=0
while read -r name; do
    [ -z "$name" ] && continue
    grep -qxF "$name" <<< "$present" || { echo "$name: in index.toml but not cloned"; problems=1; }
done <<< "$listed"
while read -r name; do
    [ -z "$name" ] && continue
    grep -qxF "$name" <<< "$listed" || { echo "$name: cloned but not in index.toml"; problems=1; }
done <<< "$present"

[ "$problems" -eq 0 ] && echo "All repos in index.toml are cloned, and nothing extra is present."
exit "$problems"
