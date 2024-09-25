.PHONY: format doc test test_migrations run

install:
	poetry install --no-root --all-extras
	poetry run pre-commit install

update:
	poetry update

format:
	poetry run ruff format && poetry run ruff check --fix --select I

lint:
	poetry run ruff check --fix

doc:
	poetry run python docs/generate_openapi_doc.py

test:
	pytest tests/

test_migrations:
	poetry run pytest -vv --test-alembic -m "alembic"

run:
	poetry run gunicorn --worker-class server.AppUvicornWorker app.main:app