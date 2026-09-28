from __future__ import annotations

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.config import DATABASE_URL, DATA_DIR

DATA_DIR.mkdir(parents=True, exist_ok=True)
# SQLite in WAL mode serves many concurrent readers; a page fires several API calls at once, so the
# default pool (5 + 10) was too small. Fail fast (5 s) rather than hang a request for 30 s.
_pool = {"pool_size": 20, "max_overflow": 20, "pool_timeout": 5} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, future=True, **_pool)

if DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _pragma(conn, _):
        cur = conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA synchronous=NORMAL")
        cur.execute("PRAGMA busy_timeout=5000")
        cur.execute("PRAGMA cache_size=-65536")   # 64 MB page cache per connection
        cur.execute("PRAGMA temp_store=MEMORY")
        cur.close()

SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_all(drop: bool = False):
    from app.db.models import Base
    if drop:
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
