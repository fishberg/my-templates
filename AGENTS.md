# AGENTS.md

Personal landing repo (`fishberg/my-templates`, cloned to `~/templates`) that indexes
LaTeX template repos and holds small CLI tools for starting new projects.

## Layout

- `index.toml` — the `repos = [...]` list of template repo URLs (https form, no `.git`).
  Commented-out entries are intentionally disabled; leave them in place.
- `templates/` — the cloned template repos live here. Its `.gitignore` ignores everything
  except `*.sh`, so clones are never committed. The scripts operate on the git repos in
  this directory against `../index.toml`:
  - `do-clone-ssh.sh` / `do-clone-https.sh` — clone any listed repo that is missing.
  - `check-clone.sh` — diff `index.toml` against what is cloned.
  - `check-commit.sh` — report dirty / unpushed / no-upstream repos (offline).
  - `check-pull.sh` — fetch and report repos behind their remote.
  - `add-to-index.sh` — append cloned repos missing from `index.toml`.
- `init-template/` — curses fuzzy picker that copies a template from `../templates` into
  the cwd. Git templates copy tracked files with local edits, excluding untracked and
  ignored files; plain folders copy everything except the root `.git`.
- `init-gitignore/` — curses fuzzy picker that writes a `.gitignore` from
  github/gitignore, shallow-cloned into `init-gitignore/gitignore/` (git-ignored).
  Only touches the network on first clone or `--update`.
- `init-overleaf/` — pushes the cwd as the next commit of an Overleaf project's Git repo;
  accepts either the Git URL or the `overleaf.com/project/<id>` URL.

## Conventions for the `init-*` tools

Each tool folder has the same shape — keep new tools consistent with it:

- `init-<name>` — bash entry point that resolves its real path (following symlinks) and
  runs `uv run --quiet --project "$DIR" python "$DIR/init_<name>.py" "$@"`, preserving
  the caller's cwd.
- `init_<name>.py` — the implementation. Standard library only (`dependencies = []`),
  Python `>=3.10`. Uses `argparse` with an explicit `prog`, `sys.exit("error: ...")` for
  failures, and never overwrites existing files in the cwd.
- `install.sh` / `uninstall.sh` — symlink into / remove from `~/.local/bin`, refusing to
  touch a destination that doesn't point back into the folder.
- `pyproject.toml`, `uv.lock`, and a `.gitignore` containing `.venv/` and `__pycache__/`.

The curses pickers (`init-template`, `init-gitignore`) share the same menu idioms: fuzzy
in-order character matching, Ctrl-N/Ctrl-P navigation, `ESCDELAY=25`, and a query
argument that skips the menu when exactly one item matches.

## Style

- Bash scripts: `#!/usr/bin/env bash`, a one-line comment describing the script,
  `cd "$(dirname "$0")"` or `DIR="$(dirname "$(readlink -f ...)")"` so they work from any
  cwd. Inline `python3 -c` with `tomllib` is used to read `index.toml`.
- Short, purposeful comments; match the existing density.
- When adding a template repo or tool, update the tables/instructions in `README.md`.

## Testing

There is no test suite. Verify changes by running the tool directly from a scratch
directory (e.g. `/path/to/init-template/init-template -t paper`), not inside this repo.
