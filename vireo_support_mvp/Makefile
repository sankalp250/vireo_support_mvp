install:
	python -m venv .venv && .venv/bin/pip install -r requirements.txt
run:
	uvicorn app.main:app --reload
worker:
	python -m app.worker
ingest:
	python scripts/ingest.py
review-sample:
	python scripts/create_review_sample.py
test:
	pytest -q
