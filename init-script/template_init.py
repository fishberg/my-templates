"""Searchable curses menu that copies a template from ../templates into the cwd."""

import curses
import os
import shutil
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


def menu(stdscr, names: list[str], query: str) -> str | None:
    curses.curs_set(1)
    curses.use_default_colors()
    stdscr.keypad(True)

    selected = 0
    scroll = 0
    status = ""

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
            taken = dest_taken(name)
            label = f"{name}  (exists)" if taken else name
            attr = curses.A_DIM if taken else curses.A_NORMAL
            if idx == selected:
                attr |= curses.A_REVERSE
            addstr(stdscr, list_top + row, 0, ("> " if idx == selected else "  ") + label, attr)

        if matches:
            addstr(stdscr, height - 3, 0, f"Destination: {Path.cwd() / matches[selected]}")
        addstr(stdscr, height - 2, 0, status, curses.A_BOLD)
        addstr(stdscr, height - 1, 0, "Type to search · ↑/↓ move · Enter select · Esc cancel", curses.A_DIM)
        addstr(stdscr, 0, 0, f"Search: {query}")
        stdscr.move(0, min(len("Search: ") + len(query), stdscr.getmaxyx()[1] - 1))
        stdscr.refresh()

        key = stdscr.get_wch()
        status = ""
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
            name = matches[selected]
            if dest_taken(name):
                status = f"'{name}' already exists in the current directory"
                continue
            return name
        if key in KEYS_BACKSPACE:
            query = query[:-1]
            selected = 0
        elif key == curses.KEY_UP:
            selected = max(0, selected - 1)
        elif key == curses.KEY_DOWN:
            selected = min(len(matches) - 1, selected + 1)


def copy_template(name: str) -> None:
    src = TEMPLATES_DIR / name
    dest = Path.cwd() / name
    if dest_taken(name):
        sys.exit(f"error: '{dest}' already exists")

    def ignore_root_git(directory: str, entries: list[str]) -> list[str]:
        return [".git"] if Path(directory) == src and ".git" in entries else []

    shutil.copytree(src, dest, symlinks=True, ignore=ignore_root_git)
    print(f"Created ./{name} from {src}")


def main() -> None:
    if not TEMPLATES_DIR.is_dir():
        sys.exit(f"error: templates directory not found: {TEMPLATES_DIR}")
    names = list_templates()
    if not names:
        sys.exit(f"error: no templates found in {TEMPLATES_DIR}")

    query = " ".join(sys.argv[1:])
    os.environ.setdefault("ESCDELAY", "25")  # make Esc respond immediately
    try:
        choice = curses.wrapper(menu, names, query)
    except KeyboardInterrupt:
        choice = None
    if choice is None:
        print("Cancelled.")
        return
    copy_template(choice)


if __name__ == "__main__":
    main()
