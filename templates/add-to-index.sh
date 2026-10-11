#!/usr/bin/env bash
# Append any git repos in this directory that aren't listed in ../index.toml to the end of its repos list.

cd "$(dirname "$0")" || exit 1

listed="$(python3 -c 'import tomllib; print(*(u.rstrip("/").removesuffix(".git").rsplit("/", 1)[-1] for u in tomllib.load(open("../index.toml", "rb"))["repos"]), sep="\n")')" || exit 1

new=()
for dir in */; do
    dir="${dir%/}"
    [ -d "$dir/.git" ] || continue
    grep -qxF "$dir" <<< "$listed" && continue

    url="$(git -C "$dir" remote get-url origin 2>/dev/null)"
    if [ -z "$url" ]; then
        echo "$dir: no origin remote, skipping"
        continue
    fi
    # Normalize to the https form used in index.toml (git@host:path.git -> https://host/path)
    url="${url%.git}"
    [[ "$url" == git@* ]] && url="https://$(sed 's/^git@//; s/:/\//' <<< "$url")"

    echo "$dir: adding $url"
    new+=("$url")
done

[ ${#new[@]} -eq 0 ] && { echo "Nothing to add; index.toml already lists every repo."; exit 0; }

# Insert the new entries just before the closing bracket of the repos list
python3 - "${new[@]}" <<'PY'
import re, sys
path = "../index.toml"
text = open(path).read()
m = re.search(r"^repos\s*=\s*\[.*?^\]", text, re.S | re.M)
end = m.end() - 1
lines = "".join(f'    "{u}",\n' for u in sys.argv[1:])
open(path, "w").write(text[:end] + lines + text[end:])
PY
