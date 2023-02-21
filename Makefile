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

# scripts
scripts-create-big-file:
	PYTHONPATH=. poetry run python src/scripts/create_big_file.py

# start applications
start-app:
	PYTHONPATH=. poetry run python src/app/main.py

start-dhcp:
	PYTHONPATH=. poetry run python src/dhcp/main.py

start-dns:
	PYTHONPATH=. poetry run python src/dns/main.py

# testing
test-client-upload-file:
	PYTHONPATH=. poetry run python src/client/main.py upload uploads/A.md

test-client-upload-file-100:
	PYTHONPATH=. poetry run python src/client/main.py upload uploads/100.txt

test-client-upload-file-1000:
	PYTHONPATH=. poetry run python src/client/main.py upload uploads/1K.txt

test-client-upload-file-10000:
	PYTHONPATH=. poetry run python src/client/main.py upload uploads/10K.txt

test-client-upload-file-child:
	PYTHONPATH=. poetry run python src/client/main.py upload uploads/other/B.txt --dest child-dir/B.txt

test-client-upload-file-child-100:
	PYTHONPATH=. poetry run python src/client/main.py upload uploads/other/100.txt --dest child-dir/100.txt

test-client-upload-file-child-1000:
	PYTHONPATH=. poetry run python src/client/main.py upload uploads/other/1K.txt --dest child-dir/1K.txt

test-client-upload-file-child-10000:
	PYTHONPATH=. poetry run python src/client/main.py upload uploads/other/10K.txt --dest child-dir/10K.txt

test-client-upload-all:
	make test-client-upload-file
	make test-client-upload-file-child
	make test-client-upload-file-100
	make test-client-upload-file-child-100
	make test-client-upload-file-1000
	make test-client-upload-file-child-1000
	make test-client-upload-file-10000
	make test-client-upload-file-child-10000

test-client-list-1:
	PYTHONPATH=. poetry run python src/client/main.py list

test-client-list:
	PYTHONPATH=. poetry run python src/client/main.py list child-dir

test-client-download-file: temp
	PYTHONPATH=. poetry run python src/client/main.py download A.md ./temp/A.md

test-client-download-file-child: temp
	PYTHONPATH=. poetry run python src/client/main.py download child-dir/A.txt ./temp/B.txt