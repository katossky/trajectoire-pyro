import os
from pathlib import Path
import re
from typing import List, Dict, Optional
from typing_extensions import Annotated

from github import Github, ContentFile, Label, Issue

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

def _update_file(file_obj: ContentFile.ContentFile, new_content: str, message: str) -> None:
    """Commit *new_content* back to *file_obj* with *message*."""
    _repo.update_file(
        path=file_obj.path,
        message=message,
        content=new_content,
        sha=file_obj.sha,
        branch=_default_branch,
    )

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
    if path == "" :
        path = None
    paths = [Path(path, p) if path else Path(p) for p in os.listdir(path)]
    dirs = [str(p) for p in paths if p.is_dir()]
    return [d for d in dirs if not d.startswith(".")]

def list_files(
    path: Annotated[str, "Directory path relative to root"] = None
) -> List[str]:
    """Return the file paths at *path* (non‑recursive)."""
    if path == "" :
        path = None
    paths = [Path(path, p) if path else Path(p) for p in os.listdir(path)]
    files = [str(p) for p in paths if not p.is_dir()]
    return [f for f in files if not f.startswith(".")]

def read_file(
    path: Annotated[str, "File path relative to root"] = None
) -> str:
    """Read file at *path*."""
    return Path(path).read_text(encoding="utf-8")

def create_directory(
    path: Annotated[str, "Directory path relative to root"] = None
) :
    """Create a new directory."""
    if Path(path).exists() :
        raise FileExistsError("File or directory {path} already exists")
    else :
        Path(path).mkdir()

def write_file(
    path: Annotated[str, "File path relative to root"] = None,
    content: Annotated[str, "Content of the file"] = None
) :
    """Create a new text file."""
    if Path(path).exists() :
        raise FileExistsError("File or directory {path} already exists")
    elif content is not None :
        with open(path, 'w') as f:
            f.write(content)

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

# ────────────────────────────────── README mutation helpers ─────────────────

# Heading pattern with ID in curly‑brace, e.g. "## Statistics {#stats}"
_HEADING_ID_RE = re.compile(r"^(?P<hashes>#{1,6})\s+[^#{}]*\{#(?P<id>[A-Za-z0-9_.-]+)\}\s*$")


def _find_heading_index(lines: List[str], section_id: str) -> Optional[int]:
    """Return index of heading line matching *section_id* or None."""
    for i, ln in enumerate(lines):
        m = _HEADING_ID_RE.match(ln)
        if m and m.group("id") == section_id:
            return i
    return None


def append_readme(section: str, point: str) -> None:
    """Append markdown bullet *point* to the heading whose id == *section*.

    The heading must follow the GitHub‑flavoured pattern `## Title {#id}`.
    Creates the section at the end of the document if it does not exist.
    """
    cf = _get_readme()
    lines = cf.decoded_content.decode().splitlines()

    idx = _find_heading_index(lines, section)
    bullet = f"- {point}"

    if idx is None:
        # section missing → create new H2 at end
        lines.extend(["", f"## {section.title()} {{#{section}}}", bullet, ""])
    else:
        # insert after existing content until next heading or EOF
        insert_at = idx + 1
        while insert_at < len(lines) and not lines[insert_at].startswith("#"):
            insert_at += 1
        lines.insert(insert_at, bullet)

    new_body = "\n".join(lines)
    _update_file(cf, new_body, f"docs(readme): append bullet to section #{section}")


def create_readme_section(title: str, id: str) -> None:
    """Create a new H2 section formatted as `## title {#id}` if it doesn't exist."""
    cf = _get_readme()
    lines = cf.decoded_content.decode().splitlines()

    if _find_heading_index(lines, id) is not None:
        return  # already present

    lines.extend(["", f"## {title} {{#{id}}}", ""])
    new_body = "\n".join(lines)
    _update_file(cf, new_body, f"docs(readme): add section {title} (# {id})")
