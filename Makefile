SHELL:=/usr/bin/env bash -O globstar

# ci / cd
install:
	poetry install

clean:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean-all: clean
	rm -rf .venv

black:
	 poetry run black ./src/

isort:
	poetry run isort ./src/

fix: isort black

fix-lint: fix lint

start-app:
	PYTHONPATH=. poetry run python src/app/main.py
