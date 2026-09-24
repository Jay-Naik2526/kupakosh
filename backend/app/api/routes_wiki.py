from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import WikiNoting, WikiPage
from app.db.session import get_db
from app.wiki import gitstore
from app.wiki.compiler import CitationError, compile_all
from app.wiki.review import review

router = APIRouter(prefix="/api/wiki")


def _p(p: WikiPage) -> dict:
    return {"slug": p.slug, "kind": p.kind, "title": p.title, "ref_no": p.ref_no, "version": p.version, "status": p.status,
            "approved_by": p.approved_by, "approved_at": p.approved_at.isoformat() if p.approved_at else None,
            "trust": p.trust, "n_sources": p.n_sources, "git_commit": p.git_commit}


@router.get("")
def pages(kind: str | None = None, status: str | None = None, q: str | None = None, db: Session = Depends(get_db)):
    s = select(WikiPage)
    if kind:
        s = s.where(WikiPage.kind == kind)
    if status:
        s = s.where(WikiPage.status == status)
    if q:
        s = s.where(WikiPage.title.ilike(f"%{q}%"))
    return [_p(p) for p in db.scalars(s.order_by(WikiPage.kind, WikiPage.title))]


@router.post("/compile")
def compile_(scope: str = "all", db: Session = Depends(get_db)):
    try:
        res = compile_all(db, scope)
    except CitationError as e:
        raise HTTPException(422, str(e))
    db.commit()
    return res


@router.get("/{slug:path}/history")
def history(slug: str):
    return gitstore.history(slug + ".md")


@router.get("/{slug:path}/diff")
def diff(slug: str, a: str, b: str):
    return {"diff": gitstore.diff(slug + ".md", a, b)}


@router.get("/{slug:path}/noting")
def noting(slug: str, db: Session = Depends(get_db)):
    p = db.scalars(select(WikiPage).where(WikiPage.slug == slug)).first()
    if not p:
        raise HTTPException(404)
    return [{"para_no": n.para_no, "author": n.author, "role": n.role, "note": n.note, "action": n.action,
             "created_at": n.created_at.isoformat() if n.created_at else None, "git_commit": n.git_commit}
            for n in db.scalars(select(WikiNoting).where(WikiNoting.page_id == p.id).order_by(WikiNoting.para_no))]


class Review(BaseModel):
    action: str
    reviewer: str
    role: str = "Reviewer"
    note: str | None = None
    content: str | None = None


@router.post("/{slug:path}/review")
def do_review(slug: str, body: Review, db: Session = Depends(get_db)):
    try:
        return review(db, slug, body.action, body.reviewer, body.role, body.note, body.content)
    except (ValueError, CitationError) as e:
        raise HTTPException(422, str(e))


@router.get("/{slug:path}")
def page(slug: str, commit: str | None = None, db: Session = Depends(get_db)):
    p = db.scalars(select(WikiPage).where(WikiPage.slug == slug)).first()
    if not p:
        raise HTTPException(404)
    text = gitstore.read(slug + ".md", commit)
    if text is None:
        raise HTTPException(404, "page file missing")
    _, fm, body = text.split("---\n", 2)
    return {**_p(p), "frontmatter": fm, "body": body}
