.PHONY: isort black test run

format: isort black

isort:
	isort .

black:
	black .

test:
	pytest tests/

run:
	poetry run gunicorn --worker-class server.AppUvicornWorker app.main:app