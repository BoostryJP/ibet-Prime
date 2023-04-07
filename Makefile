.PHONY: isort black test run

install:
	poetry install --no-root -E ibet-explorer
	poetry run pre-commit install

format: isort black

isort:
	isort .

black:
	black .

test:
	pytest tests/

run:
	poetry run gunicorn --worker-class server.AppUvicornWorker app.main:app