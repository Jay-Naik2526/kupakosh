# Kupakosh — prototype build. See README.md.
PY      := backend/.venv/bin/python
DYLD    := DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib
API_PORT ?= 8010

.PHONY: setup data data-core bootstrap api web demo test e2e eval up share

setup:            ## python 3.11 venv + backend deps + frontend deps
	cd backend && uv venv --python 3.11 .venv && uv pip install --python .venv -r requirements.txt
	cd frontend && npm install

data:             ## download EVERY public dataset (all countries) into data/raw — idempotent, several minutes to ~1h on a slow line
	bash backend/scripts/download_world.sh

data-core:        ## fast path: Sodir (Norway) + Utah FORGE + India only — enough for `make bootstrap` to produce a working demo
	bash backend/scripts/download_world.sh core

bootstrap:        ## rebuild DB + embeddings + wiki + evals from data/raw (all countries; several minutes)
	cd backend && $(DYLD) .venv/bin/python -m scripts.bootstrap

api:              ## FastAPI on :$(API_PORT)  (do not wrap in nohup: macOS strips DYLD_* and PDF export then fails)
	cd backend && $(DYLD) .venv/bin/python -m uvicorn app.main:app --port $(API_PORT) --reload

web:              ## Next.js on :3000 (expects the API on :$(API_PORT))
	cd frontend && NEXT_PUBLIC_API=http://localhost:$(API_PORT) npm run dev

demo:             ## production build of the website on :3001 (pre-compiled pages: fast, smooth navigation; expects the API on :$(API_PORT))
	cd frontend && KK_DIST=.next-prod npm run build && KK_DIST=.next-prod npx next start -p 3001

test:             ## backend tests + frontend type-check + frontend unit tests
	cd backend && $(DYLD) .venv/bin/python -m pytest -q tests
	cd frontend && npx tsc --noEmit && npm test

e2e:              ## Playwright smoke test of all screens (needs `make api` + `make web` running; first run: npx playwright install chromium)
	cd frontend && npx playwright test

eval:             ## re-run evaluations only
	cd backend && .venv/bin/python -c "from app.db.session import SessionLocal; from app.eval.run import run_all; db=SessionLocal(); run_all(db); db.commit()"

up:               ## target stack (Postgres/PostGIS/pgvector) — NOT verified on the build machine (no Docker)
	docker compose up --build

share:            ## build the website into the backend and serve site + API + replay on ONE port (for teammates)
	cd frontend && KK_EXPORT=1 npx next build
	cd backend && $(DYLD) .venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port $(API_PORT)
	# then, in another terminal:  cloudflared tunnel --url http://localhost:$(API_PORT)
