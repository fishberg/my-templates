"""Searchable curses menu that writes a github/gitignore template into the cwd."""

import argparse
import curses
import os
import subprocess
import sys
from pathlib import Path

REPO_URL = "https://github.com/github/gitignore"
REPO_DIR = Path(__file__).resolve().parent / "gitignore"
SUFFIX = ".gitignore"

KEY_ESC = 27
KEY_CTRL_N = 14
KEY_CTRL_P = 16
KEYS_BACKSPACE = (curses.KEY_BACKSPACE, 127, 8)
KEYS_ENTER = (curses.KEY_ENTER, 10, 13)


def git(*args: str, capture: bool = False) -> str:
    result = subprocess.run(
        ["git", "-C", str(REPO_DIR), *args],
        check=True,
        text=True,
        stdout=subprocess.PIPE if capture else None,
    )
    return result.stdout.strip() if capture else ""


def clone_repo() -> None:
    print(f"Cloning {REPO_URL} into {REPO_DIR} ...")
    subprocess.run(["git", "clone", "--quiet", "--depth", "1", REPO_URL, str(REPO_DIR)], check=True)


def ensure_repo() -> None:
    """Clone the repo if missing; never touch the network otherwise."""
    if not REPO_DIR.is_dir():
        clone_repo()


def update_repo() -> None:
    if not REPO_DIR.is_dir():
        clone_repo()
        return
    print(f"Checking {REPO_URL} for updates ...")
    git("fetch", "--quiet", "--depth", "1")
    old = git("rev-parse", "HEAD", capture=True)
    new = git("rev-parse", "@{u}", capture=True)
    if old == new:
        print(f"Already up to date ({old[:7]}).")
        return
    # Shallow history may not fast-forward; the clone has no local changes, so reset.
    git("reset", "--quiet", "--hard", "@{u}")
    print(f"Updated {old[:7]} -> {new[:7]}.")


def list_gitignores() -> dict[str, Path]:
    """Map display names (path relative to the repo, minus the suffix) to files."""
    entries = {}
    for path in REPO_DIR.rglob(f"*{SUFFIX}"):
        rel = path.relative_to(REPO_DIR)
        if rel.parts[0] in (".git", ".github") or not path.is_file():
            continue
        entries[rel.as_posix()[: -len(SUFFIX)]] = path
    return entries


def sort_key(name: str) -> tuple[int, str]:
    # Root-level templates first, then Global/, then community/ and anything deeper.
    return (name.count("/"), name.lower())


def dest_taken(name: str) -> bool:
    dest = Path.cwd() / name
    return dest.exists() or dest.is_symlink()


def fuzzy_match(query: str, name: str) -> bool:
    """True if every character of query appears in name, in order."""
    it = iter(name.lower())
    return all(ch in it for ch in query.lower())


def filter_names(query: str, names: list[str]) -> list[str]:
    query = query.strip()
    if not query:
        return names
    matches = [n for n in names if fuzzy_match(query, n)]
    # Substring matches first, then fuzzy-only matches; each group in sort_key order.
    return sorted(matches, key=lambda n: (query.lower() not in n.lower(), *sort_key(n)))


def unique_pick(query: str, names: list[str]) -> str | None:
    """The single obvious choice for query, if there is one."""
    query = query.strip()
    if not query:
        return None
    matches = filter_names(query, names)
    if len(matches) == 1:
        return matches[0]
    exact = [n for n in names if n.rsplit("/", 1)[-1].lower() == query.lower()]
    return exact[0] if len(exact) == 1 else None


def addstr(win, y: int, x: int, text: str, attr: int = 0) -> None:
    height, width = win.getmaxyx()
    if 0 <= y < height and x < width:
        win.addnstr(y, x, text, width - x - 1, attr)


def menu(stdscr, names: list[str], query: str, dest_name: str) -> str | None:
    curses.curs_set(1)
    curses.use_default_colors()
    stdscr.keypad(True)

    selected = 0
    scroll = 0
    status = ""
    taken = dest_taken(dest_name)

    while True:
        matches = filter_names(query, names)
        selected = max(0, min(selected, len(matches) - 1))

        stdscr.erase()
        height, _ = stdscr.getmaxyx()
        list_top = 2
        list_height = max(1, height - list_top - 3)
        if selected < scroll:
            scroll = selected
        elif selected >= scroll + list_height:
            scroll = selected - list_height + 1

        addstr(stdscr, 1, 0, f"{len(matches)} of {len(names)} templates in {REPO_DIR}", curses.A_DIM)
        if not matches:
            addstr(stdscr, list_top, 2, "(no matches)", curses.A_DIM)
        for row, name in enumerate(matches[scroll : scroll + list_height]):
            idx = scroll + row
            attr = curses.A_REVERSE if idx == selected else curses.A_NORMAL
            addstr(stdscr, list_top + row, 0, ("> " if idx == selected else "  ") + name, attr)

        dest_label = f"Destination: {Path.cwd() / dest_name}" + ("  (exists)" if taken else "")
        addstr(stdscr, height - 3, 0, dest_label, curses.A_DIM if taken else curses.A_NORMAL)
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
            taken = dest_taken(dest_name)
            if taken:
                status = f"'{dest_name}' already exists in the current directory"
                continue
            return matches[selected]
        if key in KEYS_BACKSPACE:
            query = query[:-1]
            selected = 0
        elif key == curses.KEY_UP:
            selected = max(0, selected - 1)
        elif key == curses.KEY_DOWN:
            selected = min(len(matches) - 1, selected + 1)


def write_gitignore(name: str, src: Path, dest_name: str) -> None:
    dest = Path.cwd() / dest_name
    if dest_taken(dest_name):
        sys.exit(f"error: '{dest}' already exists")
    data = src.read_bytes()
    try:
        with open(dest, "xb") as f:  # "x" refuses to overwrite, even on a race
            f.write(data)
    except FileExistsError:
        sys.exit(f"error: '{dest}' already exists")
    print(f"Created ./{dest_name} from {name}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="init-gitignore",
        description=f"Create a .gitignore in the current directory from {REPO_URL}.",
    )
    parser.add_argument(
        "query",
        nargs="?",
        default="",
        help="initial search query; if exactly one template matches, create it without the menu",
    )
    parser.add_argument(
        "-n",
        "--name",
        default=SUFFIX,
        metavar="NAME",
        help=f"name of the created file (default: {SUFFIX})",
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="pull the latest templates into the local clone (exits unless QUERY is given)",
    )
    args = parser.parse_args()
    if args.name in ("", ".", "..") or "/" in args.name:
        parser.error(f"invalid file name: '{args.name}'")
    if dest_taken(args.name) and not (args.update and not args.query):
        parser.error(f"'{Path.cwd() / args.name}' already exists")
    return args


def main() -> None:
    args = parse_args()
    try:
        if args.update:
            update_repo()
            if not args.query:
                return
        else:
            ensure_repo()
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        sys.exit(f"error: git failed: {e}")

    entries = list_gitignores()
    if not entries:
        sys.exit(f"error: no {SUFFIX} files found in {REPO_DIR}")
    names = sorted(entries, key=sort_key)

    choice = unique_pick(args.query, names)
    if choice is None:
        os.environ.setdefault("ESCDELAY", "25")  # make Esc respond immediately
        try:
            choice = curses.wrapper(menu, names, args.query, args.name)
        except KeyboardInterrupt:
            choice = None
        if choice is None:
            print("Cancelled.")
            return
    write_gitignore(choice, entries[choice], args.name)


if __name__ == "__main__":
    main()
