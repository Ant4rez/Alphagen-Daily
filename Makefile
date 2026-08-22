.PHONY: install test lint format build deploy invoke-local clean

install:
	pip install -r requirements-dev.txt

test:
	pytest tests/ -v --cov=src

lint:
	ruff check src/ tests/
	mypy src/

format:
	black src/ tests/
	ruff check --fix src/ tests/

build:
	cd infrastructure && sam build --use-container

deploy:
	cd infrastructure && sam deploy --guided

deploy-fast:
	cd infrastructure && sam deploy

invoke-local:
	cd infrastructure && sam local invoke AlphaGenFunction --event events/scheduled.json

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf .aws-sam/ .coverage htmlcov/