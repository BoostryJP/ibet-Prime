.PHONY: isort black test run

format: isort black

isort:
	isort src/.

black:
	poetry run black src

test:
	pytest .

console:
	textual console

run:
	poetry run python src/main.py