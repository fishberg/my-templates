#!/usr/bin/env bash
# Clone (over HTTPS) every repo in ../index.toml that isn't already in this directory.

cd "$(dirname "$0")" || exit 1

python3 -c '
import tomllib
for u in tomllib.load(open("../index.toml", "rb"))["repos"]:
    url = u.rstrip("/").removesuffix(".git")
    print(url.rsplit("/", 1)[-1], url)
' | while read -r name url; do
    if [ -e "$name" ]; then
        echo "$name: already present, skipping"
    else
        echo "$name: cloning $url"
        git clone --quiet "$url" "$name" < /dev/null
    fi
done
