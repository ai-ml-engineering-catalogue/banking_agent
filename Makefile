PYTHON = .venv/bin/python
.PHONY: setup seed dev run-mcp run-backend run-frontend test build
setup:
	python3 -m venv .venv
	.venv/bin/pip install -r requirements.txt
	npm ci --prefix frontend
seed:
	$(PYTHON) -m backend.seed.seed
dev:
	$(PYTHON) scripts/dev.py
run-mcp:
	$(PYTHON) -m mcp_server.server
run-backend:
	$(PYTHON) -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
run-frontend:
	npm run dev --prefix frontend
test:
	.venv/bin/pytest -q
	npm test --prefix frontend
build:
	npm run build --prefix frontend
