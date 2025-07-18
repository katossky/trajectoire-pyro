import os
import sys
from pathlib import Path
from typing import List, Dict, Optional, Callable
from typing_extensions import Annotated

from github import Github, Issue
from git import Repo

import subprocess

# ------- Project root location helper --------------

_root = None

p = Path(__file__).resolve()
for parent in (p, *p.parents):
    if (parent / "pyproject.toml").exists() or (parent / ".git").exists():
        _root = parent

if _root is None :
    raise RuntimeError("Cannot locate the project root")

def get_absolute_path(path):
    if path == "" or path is None :
        path = Path(_root)
    else :
        path = Path(_root, path)
    return path

# ---------------------------------------------------------------------------
# Initialise GitHub handle ----------------------------------------------------
# ---------------------------------------------------------------------------

_GH_TOKEN = os.environ.get("GH_TOKEN")
if not _GH_TOKEN:
    raise EnvironmentError("GH_TOKEN environment variable is required")

_REPO_FULLNAME = os.environ.get("GH_REPO", "owner/project")  # fallback for local tests

_g = Github(_GH_TOKEN)
_repo = _g.get_repo(_REPO_FULLNAME)
_default_branch = _repo.default_branch

# ─────────────────────────── Helper utilities ───────────────────────────

def _issue_dict(iss: Issue.Issue) -> Dict:
    return {
        "number": iss.number,
        "title": iss.title,
        "body": iss.body or "",
        "state": iss.state,
        "labels": [l.name for l in iss.labels],
    }

# ─────────────────────────────────────────── FS helpers ──────────────────────

def list_directories(
    path: Annotated[str, "Directory path relative to root"] = None
) -> List[str]:
    """Return directories inside *path* (non-recursive)."""
    path = get_absolute_path(path)
    paths = [Path(path, p) for p in os.listdir(path)]
    dirs = [str(p.relative_to(path)) for p in paths if p.is_dir()]
    return [d for d in dirs if not d.startswith(".")]

def list_files(
    path: Annotated[str, "Directory path relative to root"] = None
) -> List[str]:
    """Return the file paths at *path* (non‑recursive)."""
    if path == "" :
        path = None
    paths = [Path(_root, path, p) if path else Path(p) for p in os.listdir(path)]
    files = [str(p) for p in paths if not p.is_dir()]
    return [f for f in files if not f.startswith(".")]

def read_file(
    path: Annotated[str, "File path relative to root"] = None
) -> str:
    """Read file at *path*."""
    return Path(_root, path).read_text(encoding="utf-8")

def create_directory(
    path: Annotated[str, "Directory path relative to root"] = None
) :
    """Create a new directory."""
    if Path(_root, path).exists() :
        raise FileExistsError(f"File or directory {path} already exists")
    else :
        Path(_root, path).mkdir()
    return Path(_root, path)

def write_file(
    path: Annotated[str, "File path relative to root"] = None,
    content: Annotated[str, "Content of the file"] = None
) :
    """Create a new text file."""
    if Path(_root, path).exists() :
        raise FileExistsError(f"File or directory {path} already exists")
    elif content is not None :
        with Path(_root, path).open('w') as f:
            f.write(content)
    return Path(_root, path)

def delete_file(
    path: Annotated[str, "Path to the file to be deleted relative to root"]
) -> None:
    """Delete file at given *path*."""
    path_obj = Path(_root, path)
    if not path_obj.exists() or not path_obj.is_file():
        raise FileNotFoundError(f"{path} does not exist or is not a file")
    path_obj.unlink()

def insert_line(
    path: Annotated[str, "Path to file"],
    line_number: Annotated[int, "Line number after which to insert the new line"],
    new_line: Annotated[str, "New line to insert"]
) -> None:
    """Insert *new_line* after *line_number* in file *path*."""
    lines = Path(_root, path).read_text(encoding="utf-8").splitlines()
    lines.insert(line_number, new_line)
    Path(_root, path).write_text("\n".join(lines) + "\n", encoding="utf-8")

def delete_line(
    path: Annotated[str, "Path to file"],
    line_number: Annotated[int, "Line number to delete"]
) -> None:
    """Delete line *line_number* (0-indexed) from file *path*."""
    lines = Path(_root, path).read_text(encoding="utf-8").splitlines()
    if not (0 <= line_number < len(lines)):
        raise IndexError("Line number out of range")
    del lines[line_number]
    Path(_root, path).write_text("\n".join(lines) + "\n", encoding="utf-8")

# ───────────────────────────────────────── Issue helpers ───────────────

def list_issues(
    state: Annotated[str, "State to filter the issues (defaults to 'all')"] = None,
    label: Annotated[str, "Label to filter the issues (defaults to no filter)"] = None
) -> List[Dict]:
    """Return issues, optionally filtered by *state* ("open"/"closed") and/or *label* name."""
    state = state or "all"
    candle = _repo.get_issues(state=state)
    out = []
    for iss in candle:
        if label and label not in [l.name for l in iss.labels]:
            continue
        out.append(_issue_dict(iss))
    return out

def create_issue(
    title: Annotated[str, "The issue title"],
    body: Annotated[str, "The issue body"]
) -> int:
    """Create a new issue on GitHub"""
    return _repo.create_issue(title=title, body=body).number

def comment_issue(
    number: Annotated[int, "issue identification number"],
    comment: Annotated[str, "comment to add to the issue"]
) -> None :
    """Add comment to an existing issue on GitHub"""
    iss = _repo.get_issue(number)
    iss.create_comment(comment)

def close_issue(
    number: Annotated[int, "issue identification number"]
) -> None:
    """Close an existing issue on GitHub"""
    iss = _repo.get_issue(number)
    iss.edit(state="closed")

def get_issue_body(
    issue_number: Annotated[int, "issue identification number"]
) -> str:
    """Return the body text of *issue_number*. Raises if not found."""
    return _repo.get_issue(issue_number).body or ""

# ───────────────────────────────────────── Labels helpers ───────────────

def list_existing_labels(
    state : Annotated[str, "state of the issues to consider"] = "open"
) -> Dict[str, List[int]]:
    """Return mapping {label_name: [issue_numbers,…]} for issues of state **state**."""
    result: Dict[str, List[int]] = {}
    for lbl in _repo.get_labels():
        associated = [iss.number for iss in _repo.get_issues(state=state) if lbl in iss.labels]
        result[lbl.name] = associated
    return result

def get_labels(
    issue_number: Annotated[int, "issue identification number"]
) -> List[str]:
    """List all labels of given issue"""
    iss = _repo.get_issue(issue_number)
    return [l.name for l in iss.labels]

def add_label(
    issue_number: Annotated[int, "issue identification number"],
    label: Annotated[str, "label to assign to the issue"]
) -> List[str]:
    """Add *label* to the given issue (create label if absent). Returns issue's labels."""
    # ensure label exists
    try:
        _repo.get_label(label)
    except Exception:
        _repo.create_label(name=label, color="ededed")

    iss = _repo.get_issue(issue_number)
    iss.add_to_labels(label)
    return [l.name for l in iss.labels]

def remove_label(
    issue_number: Annotated[int, "issue identification number"],
    label: Annotated[str, "label to remove from the issue"]
) -> List[str]:
    """Remove *label* from issue; returns remaining labels."""
    iss = _repo.get_issue(issue_number)
    # safe: GitHub API ignores if label isn't attached
    iss.remove_from_labels(label)
    return [l.name for l in iss.labels]

# ----------- merge requests ----------------------------------

def open_pull_request(
    branch: Annotated[str, "Name of the feature branch"],
    title: Annotated[str, "Title of the pull request"],
    body: Annotated[str, "Description of the pull request"],
    issue_number: Annotated[Optional[int], "Optional issue number to link PR"] = None,
) -> None:
    """Open a pull request on GitHub for *branch*, optionally linking issue *issue_number*."""
    pr_body = f"Closes #{issue_number}\n\n{body}" if issue_number else body
    _repo.create_pull(title=title, body=pr_body, head=branch, base=_default_branch)

# ----------- git helpers ----------------------------

def create_and_switch_branch(branch: Annotated[str, "The new branch to create"]) -> None :
    """Create a new """
    repo = Repo()
    repo.git.checkout(_default_branch)
    repo.git.pull("origin", _default_branch)
    repo.git.checkout("-b", branch)

def diff(
    path: Annotated[Optional[str], "Path to file or directory (optional, default is full repo)"] = None
) -> str:
    """Return git diff of the whole repo or the given path."""
    args = ["git", "diff"]
    if path:
        args.append(path)
    return subprocess.check_output(args).decode()

def commit_factory(user: Annotated[str, "Git user name for the commit"]) -> Callable[[str], None] :
    def commit(message: Annotated[str, "Commit message"]) -> None:
        """Commit all changes and push them with *user* as the author."""
        subprocess.check_call(["git", "config", "user.name", user])
        subprocess.check_call(["git", "config", "user.email", f"{user}@users.noreply.github.com"])
        subprocess.check_call(["git", "add", "."])
        subprocess.check_call(["git", "commit", "-m", message])
        # subprocess.check_call(["git", "push"])
    return commit

# ----------- running helpers ----------------------------

def run_module(
    module: Annotated[str, "module path"],
    args: Annotated[list[str], "additional arguments"] = [],
) :
    """Run module *module*, possibly with arguments"""
    subprocess.run([sys.executable, "-m", module] + args, check=True)

def run_tests(
    path: Annotated[str, "test dir or test file path"] = "tests",
    args: Annotated[list[str], "additional arguments"] = [],
) :
    """Run the test suite for **path** dir or file"""
    path = get_absolute_path(path)
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", path] + args,
        check=True,
        stdout=subprocess.PIPE,            # capture
        stderr=subprocess.STDOUT,          # merge the two streams
        text=True,                         # decode to str
    )
    return {
        "exit_code": completed.returncode,
        "output": completed.stdout,
    }