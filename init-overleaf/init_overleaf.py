"""Push the cwd's contents as the next commit of an Overleaf project's Git repo."""

import re
import shutil
import subprocess
import sys
from pathlib import Path

DEFAULT_BRANCH = "master"  # Overleaf's branch name
COMMIT_MESSAGE = "init commit"
PROJECT_URL_RE = re.compile(r"^https?://(?:www\.)?overleaf\.com/project/([^/?#]+)/?(?:[?#].*)?$")


def git_url(url: str) -> str:
    """Map an Overleaf project (document) URL to its Git URL; pass anything else through."""
    match = PROJECT_URL_RE.match(url)
    return f"https://git@git.overleaf.com/{match.group(1)}" if match else url


def run(*args: str) -> None:
    subprocess.run(["git", *args], check=True)


def remote_branch(url: str) -> str | None:
    """Return the remote's default branch, None if the remote is empty; exit if unreachable."""
    result = subprocess.run(
        ["git", "ls-remote", "--symref", url, "HEAD"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        sys.exit(f"error: could not access Overleaf repo at {url}\n{result.stderr.rstrip()}")
    for line in result.stdout.splitlines():
        if line.startswith("ref: refs/heads/") and line.endswith("\tHEAD"):
            return line.removeprefix("ref: refs/heads/").removesuffix("\tHEAD")
    return None


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("usage: init-overleaf <overleaf-git-url | overleaf-project-url>\n"
                 "  e.g. init-overleaf https://git@git.overleaf.com/<OVERLEAF_HASH>\n"
                 "       init-overleaf https://www.overleaf.com/project/<OVERLEAF_HASH>")
    url = git_url(sys.argv[1])
    if url != sys.argv[1]:
        print(f"Using Git URL {url}")
    cwd = Path.cwd()
    git_dir = cwd / ".git"
    if git_dir.exists() or git_dir.is_symlink():
        sys.exit(f"error: {cwd} is already a git repository")

    branch = remote_branch(url)
    empty = branch is None
    branch = branch or DEFAULT_BRANCH

    try:
        run("init", "-q")
        run("symbolic-ref", "HEAD", f"refs/heads/{branch}")
        run("remote", "add", "origin", url)
        if not empty:
            run("fetch", "-q", "origin", branch)
            # Mixed reset: HEAD/index follow Overleaf, working tree stays as-is.
            run("reset", "-q", "FETCH_HEAD")
        run("add", "-A")
        run("commit", "-q", "-m", COMMIT_MESSAGE)
        run("push", "-u", "origin", branch)
    except (subprocess.CalledProcessError, KeyboardInterrupt) as e:
        shutil.rmtree(git_dir, ignore_errors=True)
        what = f"'{' '.join(e.cmd)}' failed" if isinstance(e, subprocess.CalledProcessError) else "interrupted"
        sys.exit(f"error: {what}; removed {git_dir}")

    print(f"Pushed {cwd} to {url} ({branch})")


if __name__ == "__main__":
    main()
