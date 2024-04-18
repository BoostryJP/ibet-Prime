.PHONY: isort black test run

install:
	poetry install --no-root --all-extras
	poetry run pre-commit install

update:
	poetry update

format: isort black

isort:
	isort .

black:
	black .

test:
	pytest tests/

test_migrations:
	poetry run pytest -vv --test-alembic -m "alembic"

run:
	poetry run gunicorn --worker-class server.AppUvicornWorker app.main:app