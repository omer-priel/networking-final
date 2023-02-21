SHELL:=/usr/bin/env bash -O globstar

# units
temp:
	mkdir temp

# ci / cd
install:
	poetry install

clean:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +
	rm -rf temp storage

clean-all: clean
	rm -rf .venv poetry.lock

black:
	 poetry run black ./src/

isort:
	poetry run isort ./src/

fix: isort black

fix-lint: fix lint

# start
start-app:
	PYTHONPATH=. poetry run python src/app/main.py

start-dhcp:
	PYTHONPATH=. poetry run python src/dhcp/main.py

start-dns:
	PYTHONPATH=. poetry run python src/dns/main.py

# testing
test-client-upload-file:
	PYTHONPATH=. poetry run python src/client/main.py upload uploads/A.md

test-client-upload-file-child:
	PYTHONPATH=. poetry run python src/client/main.py upload uploads/other/B.txt --dest child-dir/B.txt

test-client-list-1:
	PYTHONPATH=. poetry run python src/client/main.py list

test-client-list:
	PYTHONPATH=. poetry run python src/client/main.py list child-dir

test-client-download-file: temp
	PYTHONPATH=. poetry run python src/client/main.py download A.md ./temp/A.md

test-client-download-file-child: temp
	PYTHONPATH=. poetry run python src/client/main.py download child-dir/A.txt ./temp/B.txt