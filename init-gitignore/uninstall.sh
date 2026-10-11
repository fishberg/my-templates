#!/usr/bin/env bash
# Remove the init-gitignore symlink from ~/.local/bin (only if it points into this folder).
set -euo pipefail
DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
DEST="$HOME/.local/bin/init-gitignore"

if [[ -L "$DEST" && "$(readlink "$DEST")" == "$DIR/"* ]]; then
    rm "$DEST"
    echo "Uninstalled: $DEST"
elif [[ -e "$DEST" || -L "$DEST" ]]; then
    echo "error: $DEST was not installed from $DIR; leaving it alone" >&2
    exit 1
else
    echo "Not installed: $DEST"
fi
