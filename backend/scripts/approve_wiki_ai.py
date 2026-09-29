"""AI review of the Well Wiki, at the project lead's explicit request (29 Sept 2026, no engineer available).

For every page that is not yet approved:
  - re-run the compiler's citation post-check on the page body (every sentence must carry [^sN]);
  - require at least one cited source.
Pages that pass are approved through the normal review workflow (noting para + git commit) with the
reviewer "AI review, authorised by Jay Naik" — never a human name — so they stay distinguishable
from engineer approvals. Pages that fail are left as they are and listed.

Usage (from backend/):  DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib .venv/bin/python -m scripts.approve_wiki_ai
"""
from __future__ import annotations

import re

from app.db.models import WikiPage
from app.db.session import SessionLocal
from app.wiki import gitstore
from app.wiki.compiler import check_citations
from app.wiki.review import _split, review

REVIEWER = "AI review, authorised by Jay Naik"
ROLE = "AI reviewer (not engineer-verified)"
NOTE = ("AI check: every sentence cited; numbers were already traced to their sources by the compiler. "
        "Not engineer-verified.")


def main() -> None:
    db = SessionLocal()
    pages = db.query(WikiPage).filter(WikiPage.status != "approved").order_by(WikiPage.slug).all()
    ok, skipped = 0, []
    for p in pages:
        try:
            fm, body = _split(gitstore.read(p.slug + ".md"))
        except Exception as e:  # missing file
            skipped.append((p.slug, f"unreadable: {e}"))
            continue
        bad = check_citations(body)
        n_src = len(fm.get("sources") or []) or len(set(re.findall(r"\[\^s\d+\]:", body)))
        if bad:
            skipped.append((p.slug, f"{len(bad)} uncited line(s)"))
            continue
        if n_src == 0:
            skipped.append((p.slug, "no sources"))
            continue
        review(db, p.slug, "approve", REVIEWER, ROLE, NOTE)
        ok += 1
        if ok % 100 == 0:
            print(f"approved {ok}…", flush=True)
    print(f"approved {ok} of {len(pages)} pending pages; left as they were: {len(skipped)}")
    for slug, why in skipped[:50]:
        print(f"  skipped {slug}: {why}")


if __name__ == "__main__":
    main()
