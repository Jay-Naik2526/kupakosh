"""Add the real Volve daily drilling reports to an existing database without a full rebuild
(a full rebuild would also re-create the wiki and drop its approvals).

Steps: ingest (app.ingest.ext.no_volve_ddr) -> countries -> extraction on the new documents only ->
episodes for the Volve wells -> data-source register. Embeddings are added separately (slow on CPU):
    python -m scripts.add_volve_ddr            # ingest + extract + episodes
    python -m scripts.add_volve_ddr --embed    # also embed the new sentences for the copilot
Safe to re-run: the ingester skips reports already loaded (by content hash).
"""
from __future__ import annotations

import sys

from sqlalchemy import select

from app.db.models import Document
from app.db.session import SessionLocal


def main() -> None:
    from app.engines import episodes, post
    from app.extract import pipeline
    from app.ingest.ext import no_volve_ddr

    with SessionLocal() as db:
        before = set(db.scalars(select(Document.id).where(Document.kind == "DDR_XML")))
        s = no_volve_ddr.ingest(db)
        db.commit()
        new_docs = set(db.scalars(select(Document.id).where(Document.kind == "DDR_XML"))) - before
        well_ids = set(db.scalars(select(Document.well_id).where(Document.id.in_(new_docs)))) if new_docs else set()
        print(f"new daily reports: {len(new_docs)} across {len(well_ids)} wells ({s})")
        post.assign_countries(db)
        db.commit()
        if new_docs:
            print("extraction:", pipeline.run(db, doc_ids=new_docs))
            db.commit()
            all_volve = set(db.scalars(select(Document.well_id).where(Document.kind == "DDR_XML")))
            print("episodes:", episodes.run(db, well_ids=all_volve))
            db.commit()
        post.register_sources(db)
        db.commit()
        if "--embed" in sys.argv:
            from app.search import embeddings
            print("embeddings:", embeddings.build(db))


if __name__ == "__main__":
    main()
