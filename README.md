# my-templates
This is a simple landing/index repo that links to my other template repos.

## Install
```bash
git clone git@github.com:fishberg/my-templates.git ~/templates
cd ~/templates/templates
./do-clone-ssh.sh
```

## Templates

| Template | Repository |
| - | - |
| Core | https://github.com/fishberg/template-latex-core |
| Paper | https://github.com/fishberg/template-latex-paper |
| Homework | https://github.com/fishberg/template-latex-hw |
| Rebuttal | https://github.com/fishberg/template-latex-rebuttal |
| `uv` Python Tool Installed to `~/.local/bin`| https://github.com/fishberg/template-bin-uv-python-tool |

## Start a project

Install the picker with `./init-template/install.sh`, then run it from the directory
where you want the new project:

```bash
init-template -t paper -n my-paper
```

Use `-n NAME` or `--name NAME` to set the destination folder name. If omitted,
a curses prompt asks for the name after template selection; submitting an empty
name uses the template's folder name. Esc or Ctrl-C cancels. Existing destinations
cause an error and are never overwritten. A unique `-t` match skips template
selection; supplying `-n` as well skips all prompts.

Git templates copy only tracked files, using their current local contents (including
uncommitted edits). Untracked files, locally deleted files, ignored build output,
and Git metadata are omitted. Tracked settings, executable permissions, and symlinks
are preserved. Git must be installed; templates containing submodules or unresolved
merge conflicts are rejected. Plain folders retain full-folder copying, excluding
the root `.git`.

For LaTeX templates, this prevents old `build/` caches with paths to the original
template from reaching the new project. Those caches can make LaTeX Workshop load
both projects' sources and report false duplicate labels. An existing affected
project may need `make clean` followed by **Developer: Reload Window** once to clear
the editor's cached dependencies.

