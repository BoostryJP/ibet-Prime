.PHONY: format doc test test_migrations run

install:
	uv sync --frozen --no-install-project --all-extras
	uv run pre-commit install

update:
	uv lock --upgrade

format:
	uv run ruff format && uv run ruff check --fix --select I

lint:
	uv run ruff check --fix

doc:
	DVP_AGENT_FEATURE_ENABLED=1 BC_EXPLORER_ENABLED=1 FREEZE_LOG_FEATURE_ENABLED=1 uv run python docs/generate_openapi_doc.py

test:
	uv run pytest tests/ ${ARG}

test_migrations:
	uv run pytest -vv --test-alembic -m "alembic"

run:
	uv run gunicorn --worker-class server.AppUvicornWorker app.main:app