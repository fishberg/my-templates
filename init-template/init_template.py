"""Searchable curses menu that copies a template from ../templates into the cwd."""

import argparse
import curses
import os
import shutil
import subprocess
import sys
from pathlib import Path

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

KEY_ESC = 27
KEY_CTRL_N = 14
KEY_CTRL_P = 16
KEYS_BACKSPACE = (curses.KEY_BACKSPACE, 127, 8)
KEYS_ENTER = (curses.KEY_ENTER, 10, 13)


def list_templates() -> list[str]:
    return sorted(
        p.name for p in TEMPLATES_DIR.iterdir() if p.is_dir() and not p.name.startswith(".")
    )


def dest_taken(name: str) -> bool:
    dest = Path.cwd() / name
    return dest.exists() or dest.is_symlink()


def valid_name(name: str) -> bool:
    return name not in ("", ".", "..") and "/" not in name and "\0" not in name


def fuzzy_match(query: str, name: str) -> bool:
    """True if every character of query appears in name, in order."""
    it = iter(name.lower())
    return all(ch in it for ch in query.lower())


def filter_templates(query: str, names: list[str]) -> list[str]:
    query = query.strip()
    if not query:
        return names
    matches = [n for n in names if fuzzy_match(query, n)]
    # Substring matches first, then fuzzy-only matches; each group alphabetical.
    return sorted(matches, key=lambda n: (query.lower() not in n.lower(), n))


def addstr(win, y: int, x: int, text: str, attr: int = 0) -> None:
    height, width = win.getmaxyx()
    if 0 <= y < height and x < width:
        win.addnstr(y, x, text, width - x - 1, attr)


def menu(stdscr, names: list[str], query: str, dest_name: str | None) -> str | None:
    selected = 0
    scroll = 0

    while True:
        matches = filter_templates(query, names)
        selected = max(0, min(selected, len(matches) - 1))

        stdscr.erase()
        height, _ = stdscr.getmaxyx()
        list_top = 2
        list_height = max(1, height - list_top - 3)
        if selected < scroll:
            scroll = selected
        elif selected >= scroll + list_height:
            scroll = selected - list_height + 1

        addstr(stdscr, 1, 0, f"Templates in {TEMPLATES_DIR}", curses.A_DIM)
        if not matches:
            addstr(stdscr, list_top, 2, "(no matches)", curses.A_DIM)
        for row, name in enumerate(matches[scroll : scroll + list_height]):
            idx = scroll + row
            attr = curses.A_NORMAL
            if idx == selected:
                attr |= curses.A_REVERSE
            addstr(stdscr, list_top + row, 0, ("> " if idx == selected else "  ") + name, attr)

        if dest_name is not None:
            addstr(stdscr, height - 3, 0, f"Destination: {Path.cwd() / dest_name}")
        else:
            addstr(stdscr, height - 3, 0, f"Copy into {Path.cwd()} (name prompted next)")
        addstr(stdscr, height - 1, 0, "Type to search · ↑/↓ move · Enter select · Esc cancel", curses.A_DIM)
        addstr(stdscr, 0, 0, f"Search: {query}")
        stdscr.move(0, min(len("Search: ") + len(query), stdscr.getmaxyx()[1] - 1))
        stdscr.refresh()

        key = stdscr.get_wch()
        if key == curses.KEY_RESIZE:
            continue
        if isinstance(key, str):
            code = ord(key)
            if code == KEY_ESC:
                return None
            if code in KEYS_ENTER:
                key = curses.KEY_ENTER
            elif code in KEYS_BACKSPACE:
                key = curses.KEY_BACKSPACE
            elif code == KEY_CTRL_N:
                key = curses.KEY_DOWN
            elif code == KEY_CTRL_P:
                key = curses.KEY_UP
            elif key.isprintable():
                query += key
                selected = 0
                continue
            else:
                continue

        if key in KEYS_ENTER:
            if not matches:
                continue
            return matches[selected]
        if key in KEYS_BACKSPACE:
            query = query[:-1]
            selected = 0
        elif key == curses.KEY_UP:
            selected = max(0, selected - 1)
        elif key == curses.KEY_DOWN:
            selected = min(len(matches) - 1, selected + 1)


def prompt_name(stdscr, template: str) -> str | None:
    name = ""
    while True:
        stdscr.erase()
        height, width = stdscr.getmaxyx()
        addstr(stdscr, 1, 0, f"Template: {template}", curses.A_DIM)
        addstr(stdscr, 2, 0, f"Default name: {template}", curses.A_DIM)
        addstr(stdscr, 3, 0, f"Destination parent: {Path.cwd()}")
        addstr(stdscr, height - 1, 0, "Enter confirm (empty uses default) · Esc cancel", curses.A_DIM)
        line = f"Name: {name}"
        start = max(0, len(line) - width + 2)
        addstr(stdscr, 0, 0, line[start:])
        stdscr.move(0, min(len(line) - start, width - 1))
        stdscr.refresh()

        key = stdscr.get_wch()
        if key == curses.KEY_RESIZE:
            continue
        if isinstance(key, str):
            code = ord(key)
            if code == KEY_ESC:
                return None
            if code in KEYS_ENTER:
                return name or template
            if code in KEYS_BACKSPACE:
                name = name[:-1]
            elif key.isprintable():
                name += key
        elif key in KEYS_ENTER:
            return name or template
        elif key in KEYS_BACKSPACE:
            name = name[:-1]


def select_destination(
    stdscr, names: list[str], query: str, choice: str | None, dest_name: str | None,
) -> tuple[str, str] | None:
    curses.curs_set(1)
    curses.use_default_colors()
    stdscr.keypad(True)
    if choice is None:
        choice = menu(stdscr, names, query, dest_name)
    if choice is None:
        return None
    if dest_name is None:
        dest_name = prompt_name(stdscr, choice)
    if dest_name is None:
        return None
    return choice, dest_name


def tracked_paths(src: Path) -> set[Path] | None:
    """Return tracked paths and their parents, or None for a plain folder."""
    if not (src / ".git").exists() and not (src / ".git").is_symlink():
        return None

    def git(*args: str) -> bytes:
        try:
            return subprocess.run(
                ["git", "-C", str(src), *args],
                check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            ).stdout
        except FileNotFoundError:
            sys.exit("error: git is required to copy repository templates")
        except subprocess.CalledProcessError as exc:
            sys.exit(f"error: cannot read template repository '{src}': {os.fsdecode(exc.stderr).strip()}")

    root = Path(os.fsdecode(git("rev-parse", "--show-toplevel")).rstrip("\n"))
    if root.resolve() != src.resolve():
        sys.exit(f"error: template '{src}' must be a Git working-tree root")

    paths = set()
    for entry in git("ls-files", "--stage", "-z").split(b"\0"):
        if not entry:
            continue
        metadata, filename = entry.split(b"\t", 1)
        mode, _, stage = metadata.split()
        path = Path(os.fsdecode(filename))
        if mode == b"160000":
            sys.exit(f"error: template '{src}' contains an unsupported submodule: {path}")
        if stage != b"0":
            sys.exit(f"error: template '{src}' has unresolved merge conflicts: {path}")
        paths.add(path)
        paths.update(path.parents)
    return paths


def copy_template(name: str, dest_name: str | None = None) -> None:
    src = TEMPLATES_DIR / name
    dest_name = dest_name or name
    if not valid_name(dest_name):
        sys.exit(f"error: invalid folder name: '{dest_name}'")
    dest = Path.cwd() / dest_name

    paths = tracked_paths(src)

    def ignore_files(directory: str, entries: list[str]) -> list[str]:
        relative = Path(directory).relative_to(src)
        return [
            entry for entry in entries
            if (relative == Path(".") and entry == ".git")
            or (paths is not None and relative / entry not in paths)
        ]

    if dest_taken(dest_name):
        sys.exit(f"error: '{dest}' already exists")
    shutil.copytree(src, dest, symlinks=True, ignore=ignore_files)
    print(f"Created ./{dest_name} from {src}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="init-template",
        description="Copy a template from the templates directory into the current directory.",
        epilog="Git templates copy tracked files with local edits, excluding untracked and ignored files. "
        "Plain folders copy everything except the root .git.",
    )
    parser.add_argument(
        "-n",
        "--name",
        metavar="NAME",
        help="name of the copied folder (if omitted, prompt; empty prompt uses the template's name)",
    )
    parser.add_argument(
        "-t",
        "--template",
        default="",
        metavar="QUERY",
        help="initial search query; if exactly one template matches, select it without the menu",
    )
    args = parser.parse_args()
    if args.name is not None:
        if not valid_name(args.name):
            parser.error(f"invalid folder name: '{args.name}'")
        if dest_taken(args.name):
            parser.error(f"'{Path.cwd() / args.name}' already exists")
    return args


def main() -> None:
    args = parse_args()
    if not TEMPLATES_DIR.is_dir():
        sys.exit(f"error: templates directory not found: {TEMPLATES_DIR}")
    names = list_templates()
    if not names:
        sys.exit(f"error: no templates found in {TEMPLATES_DIR}")

    query = args.template
    choice = None
    if query.strip():
        matches = filter_templates(query, names)
        if len(matches) == 1:
            choice = matches[0]

    if choice is not None and args.name is not None:
        copy_template(choice, args.name)
        return

    os.environ.setdefault("ESCDELAY", "25")  # make Esc respond immediately
    try:
        destination = curses.wrapper(select_destination, names, query, choice, args.name)
    except KeyboardInterrupt:
        destination = None
    if destination is None:
        print("Cancelled.")
        return
    copy_template(*destination)


if __name__ == "__main__":
    main()
