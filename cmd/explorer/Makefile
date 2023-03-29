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

dev:
	TEXTUAL=devtools poetry run python src/main.py

run:
	poetry run python src/main.py