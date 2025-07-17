from pathlib import Path

if __name__ == "__main__":
    
    _root = None

    p = Path(__file__).resolve()
    for parent in (p, *p.parents):
        if (parent / "pyproject.toml").exists() or (parent / ".git").exists():
            _root = parent

    print(_root)