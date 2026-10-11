#!/usr/bin/env bash
# Clone (over SSH) every repo in ../index.toml that isn't already in this directory.

cd "$(dirname "$0")" || exit 1

python3 -c '
import tomllib
for u in tomllib.load(open("../index.toml", "rb"))["repos"]:
    url = u.rstrip("/").removesuffix(".git")
    print(url.rsplit("/", 1)[-1], "git@" + url.split("://", 1)[1].replace("/", ":", 1) + ".git")
' | while read -r name url; do
    if [ -e "$name" ]; then
        echo "$name: already present, skipping"
    else
        echo "$name: cloning $url"
        git clone --quiet "$url" "$name" < /dev/null
    fi
done
