# Kupakosh — prototype build. See README.md.
PY      := backend/.venv/bin/python
DYLD    := DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib
API_PORT ?= 8010

.PHONY: setup data bootstrap api web test eval up

setup:            ## python 3.11 venv + backend deps + frontend deps
	cd backend && uv venv --python 3.11 .venv && uv pip install --python .venv -r requirements.txt
	cd frontend && npm install

data:             ## download the real public datasets (Sodir, Utah FORGE) into data/raw
	bash backend/scripts/download_data.sh

bootstrap:        ## rebuild DB + wiki + evals from data/raw (about 30 s)
	cd backend && $(DYLD) .venv/bin/python -m scripts.bootstrap

api:              ## FastAPI on :$(API_PORT)
	cd backend && $(DYLD) .venv/bin/python -m uvicorn app.main:app --port $(API_PORT) --reload

web:              ## Next.js on :3000 (expects the API on :$(API_PORT))
	cd frontend && NEXT_PUBLIC_API=http://localhost:$(API_PORT) npm run dev

test:             ## backend tests + frontend type-check
	cd backend && $(DYLD) .venv/bin/python -m pytest -q tests
	cd frontend && npx tsc --noEmit

eval:             ## re-run evaluations only
	cd backend && .venv/bin/python -c "from app.db.session import SessionLocal; from app.eval.run import run_all; db=SessionLocal(); run_all(db); db.commit()"

up:               ## target stack (Postgres/PostGIS/pgvector) — NOT verified on the build machine (no Docker)
	docker compose up --build
