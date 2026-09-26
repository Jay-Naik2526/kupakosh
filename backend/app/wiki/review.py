"""Government-file 'noting' review: Approve / Edit / Return. Each action = numbered noting para + git commit."""
from __future__ import annotations

from datetime import datetime, timezone

import yaml
from sqlalchemy.orm import Session

from app.db.models import WikiNoting, WikiPage
from app.wiki import gitstore
from app.wiki.compiler import CitationError, check_citations

ACTIONS = {"approve": "approved", "return": "returned", "edit": "in_review"}


def _split(text: str) -> tuple[dict, str]:
    _, fm, body = text.split("---\n", 2)
    return yaml.safe_load(fm), body


def review(db: Session, slug: str, action: str, reviewer: str, role: str, note: str | None, content: str | None = None) -> dict:
    if action not in ACTIONS:
        raise ValueError("action must be approve | edit | return")
    page = db.query(WikiPage).filter(WikiPage.slug == slug).one()
    rel = slug + ".md"
    fm, body = _split(gitstore.read(rel))
    if action == "edit":
        if not content:
            raise ValueError("edit requires content")
        bad = check_citations(content)
        if bad:
            raise CitationError(f"edit rejected: {len(bad)} line(s) without a citation, e.g. {bad[0][:120]!r}")
        body = content if content.endswith("\n") else content + "\n"
        page.version += 1
    page.status = ACTIONS[action]
    if action == "approve":
        page.approved_by, page.approved_at = reviewer, datetime.now(timezone.utc)
    fm.update({"version": page.version, "status": page.status})
    if action == "approve":
        fm.update({"approved_by": reviewer, "approved_at": page.approved_at.date().isoformat()})
    text = "---\n" + yaml.safe_dump(fm, sort_keys=False, allow_unicode=True) + "---\n" + body
    sha = gitstore.write_and_commit({rel: text}, f"{action}: {slug} v{page.version} — {reviewer}" + (f": {note}" if note else ""), author=reviewer, always=True)
    page.git_commit = sha
    para = db.query(WikiNoting).filter(WikiNoting.page_id == page.id).count() + 1
    verb = {"approve": "Approved", "return": "Returned for correction", "edit": "Edited"}[action]
    db.add(WikiNoting(page_id=page.id, para_no=para, author=reviewer, role=role, note=f"{verb}. {note or ''}".strip(), action=action, git_commit=sha))
    db.commit()
    return {"ok": True, "status": page.status, "version": page.version, "commit": sha}
