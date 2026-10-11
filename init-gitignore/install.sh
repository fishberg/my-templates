#!/usr/bin/env bash
# Symlink the init-gitignore command into ~/.local/bin.
set -euo pipefail
DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
SRC="$DIR/init-gitignore"
BIN="$HOME/.local/bin"
DEST="$BIN/init-gitignore"

mkdir -p "$BIN"
if [[ -L "$DEST" && "$(readlink -f "$DEST")" == "$SRC" ]]; then
    echo "Already installed: $DEST -> $SRC"
elif [[ -e "$DEST" || -L "$DEST" ]]; then
    echo "error: $DEST already exists and does not point to $SRC" >&2
    exit 1
else
    ln -s "$SRC" "$DEST"
    echo "Installed: $DEST -> $SRC"
fi

case ":$PATH:" in
    *":$BIN:"*) ;;
    *) echo "warning: $BIN is not on your PATH" ;;
esac
