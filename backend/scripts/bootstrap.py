"""Rebuild the whole database from data/raw (real public data only).

usage: python -m scripts.bootstrap [--skip-forge]
"""
from __future__ import annotations

import sys
import time

from app.db.session import SessionLocal, create_all


def _reset_wiki():
    """The wiki git repo is rebuilt with the database so page ids and commits stay consistent."""
    import shutil
    from app.config import WIKI_DIR
    if "--keep-wiki" not in sys.argv and WIKI_DIR.exists():
        shutil.rmtree(WIKI_DIR)


def main():
    t0 = time.time()
    create_all(drop=True)
    _reset_wiki()
    from app.ingest import sodir
    from app.extract import pipeline
    from app.engines import auditor, episodes, post
    with SessionLocal() as db:
        sodir.ingest(db)
        db.commit()
        if "--skip-forge" not in sys.argv:
            from app.ingest import forge
            forge.ingest(db)
            db.commit()
        from app.ingest import india, india_docs
        india.ingest(db)
        india_docs.ingest(db)
        db.commit()
        from app.ingest import ext
        for mod in ext.modules():
            try:
                mod.ingest(db)
                db.commit()
            except Exception as e:  # one broken source must not stop the rebuild
                db.rollback()
                print(f"ext {mod.__name__}: FAILED {e!r}")
        post.assign_countries(db)
        db.commit()
        try:
            from app.search import embeddings
            embeddings.build(db)
        except Exception as e:  # noqa: BLE001 — search falls back to keyword-only and the UI says so
            print(f"embeddings: FAILED {e!r} (copilot uses keyword search only)")
        pipeline.run(db)
        from app.extract import llm_extract
        llm_extract.run(db)  # pass 2; skipped (and stated) when no LLM key is configured
        from app.engines import review_replay
        review_replay.run(db)  # human decisions from the review queue survive a rebuild
        db.commit()
        episodes.run(db)
        db.commit()

        post.run(db)
        db.commit()
        auditor.run(db)
        db.commit()
        post.register_sources(db)
        db.commit()
        from app.wiki import compiler
        compiler.compile_all(db)
        db.commit()
        if "--skip-eval" not in sys.argv:
            from app.eval.run import run_all
            run_all(db)
            db.commit()
    print(f"bootstrap done in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
