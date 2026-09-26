"""wiki/ is its own git repository; every compile and every review action is a commit."""
from __future__ import annotations

from pathlib import Path

import git

from app.config import WIKI_DIR


def repo() -> git.Repo:
    WIKI_DIR.mkdir(parents=True, exist_ok=True)
    if not (WIKI_DIR / ".git").exists():
        r = git.Repo.init(WIKI_DIR)
        with r.config_writer() as cw:
            cw.set_value("user", "name", "Kupakosh compiler")
            cw.set_value("user", "email", "compiler@kupakosh.local")
        return r
    return git.Repo(WIKI_DIR)


def write_and_commit(files: dict[str, str], message: str, author: str = "Kupakosh compiler", always: bool = False) -> str | None:
    """always=True records a commit even when the text is unchanged (every review action is a file event)."""
    r = repo()
    for rel, content in files.items():
        p = WIKI_DIR / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
    r.index.add(list(files.keys()))
    if always or not r.head.is_valid() or r.index.diff("HEAD"):
        actor = git.Actor(author, "reviewer@kupakosh.local")
        c = r.index.commit(message, author=actor, committer=actor)
        return c.hexsha
    return r.head.commit.hexsha


def history(rel: str) -> list[dict]:
    r = repo()
    if not r.head.is_valid():
        return []
    slug = rel[:-3] if rel.endswith(".md") else rel
    touched = {c.hexsha for c in r.iter_commits(paths=rel)}
    # review actions that did not change the text are still file events: they name the page in the message
    return [{"commit": c.hexsha, "short": c.hexsha[:8], "author": c.author.name, "message": c.message.strip(),
             "at": c.committed_datetime.isoformat()} for c in r.iter_commits()
            if c.hexsha in touched or f" {slug} v" in c.message]


def read(rel: str, commit: str | None = None) -> str | None:
    r = repo()
    if commit:
        try:
            return (r.commit(commit).tree / rel).data_stream.read().decode()
        except KeyError:
            return None
    p = WIKI_DIR / rel
    return p.read_text() if p.exists() else None


def diff(rel: str, a: str, b: str) -> str:
    return repo().git.diff(a, b, "--", rel, word_diff="porcelain")
