SHELL:=/usr/bin/env bash -O globstar

# units
temp:
	mkdir temp

# ci / cd
clean:
	find . -name '*.pyc' -exec sudo rm -f {} +
	find . -name '*.pyo' -exec sudo rm -f {} +
	find . -name '*~' -exec sudo rm -f {} +
	find . -name '__pycache__' -exec sudo rm -fr {} +
	sudo rm -rf temp storage tests-files/downloads

clean-all: clean
	rm -rf .venv poetry.lock

black:
	 poetry run black ./src/

isort:
	poetry run isort ./src/

fix: isort black

flake8:
	poetry run flake8

mypy:
	poetry run mypy src

lint:
	make flake8
	poetry run black --check --diff ./
	make mypy

fix-lint: fix lint

# scripts
scripts-create-big-file:
	PYTHONPATH=. poetry run python src/scripts/create_big_file.py

# testing
scripts-tc-disable:
	sudo tc qdisc del dev lo root netem

scripts-tc-10:
	sudo tc qdisc add dev lo root netem loss 10%

scripts-tc-15:
	sudo tc qdisc add dev lo root netem loss 15%

scripts-tc-20:
	sudo tc qdisc add dev lo root netem loss 20%

# start applications
start-app:
	PYTHONPATH=. poetry run python src/app/main.py

start-app-profile:
	PYTHONPATH=. poetry run python src/app/main.py --with-profiler

start-dhcp:
	sudo  ./.venv/bin/python3 src/dhcp/main.py

start-dns:
	sudo  ./.venv/bin/python3 src/dns/main.py

# testing
test-client-help:
	PYTHONPATH=. poetry run python src/client/main.py --help

test-client-upload:
	PYTHONPATH=. poetry run python src/client/main.py upload uploads/A.md

test-client-upload-100:
	PYTHONPATH=. poetry run python src/client/main.py upload uploads/100.txt

test-client-upload-1000:
	PYTHONPATH=. poetry run python src/client/main.py upload uploads/1K.txt

test-client-upload-1000-multi:
	for i in {1..10..1}; do \
		PYTHONPATH=. poetry run python src/client/main.py upload uploads/1K.txt ;\
	done;

test-client-upload-10000:
	PYTHONPATH=. poetry run python src/client/main.py upload uploads/10K.txt

test-client-upload-10000-2:
	PYTHONPATH=. poetry run python src/client/main.py upload uploads/other/10K.txt --dest 10K-2.txt

test-client-upload-child:
	PYTHONPATH=. poetry run python src/client/main.py upload uploads/other/B.txt --dest child-dir/B.txt

test-client-upload-child-100:
	PYTHONPATH=. poetry run python src/client/main.py upload uploads/other/100.txt --dest child-dir/100.txt

test-client-upload-child-1000:
	PYTHONPATH=. poetry run python src/client/main.py upload uploads/other/1K.txt --dest child-dir/1K.txt

test-client-upload-child-10000:
	PYTHONPATH=. poetry run python src/client/main.py upload uploads/other/10K.txt --dest child-dir/10K.txt

test-client-upload-multi:
	PYTHONPATH=. poetry run python src/client/main.py upload uploads/net.jpg
	PYTHONPATH=. poetry run python src/client/main.py upload uploads/dir
	PYTHONPATH=. poetry run python src/client/main.py upload uploads/other/100.txt --dest a/100.txt
	PYTHONPATH=. poetry run python src/client/main.py upload uploads/other/100.txt --dest b/100.txt
	PYTHONPATH=. poetry run python src/client/main.py upload uploads/other/100.txt --dest a/c/100.txt
	PYTHONPATH=. poetry run python src/client/main.py upload uploads/other/100.txt --dest b/c/100.txt

test-client-upload-range:
	for i in {1..10..2}; do \
		PYTHONPATH=. poetry run python src/client/main.py upload uploads/other/100.txt --dest range/$$i-$$i/$$i.txt ;\
		for j in {1..10..1}; do \
			PYTHONPATH=. poetry run python src/client/main.py upload uploads/other/100.txt --dest range/$$i-$$j.txt ;\
		done; \
	done;

test-client-upload-all:
	make test-client-upload
	make test-client-upload-child
	make test-client-upload-100
	make test-client-upload-child-100
	make test-client-upload-1000
	make test-client-upload-child-1000
	make test-client-upload-multi

test-client-upload-not-found:
	PYTHONPATH=. poetry run python src/client/main.py upload uploads/other/100.txt --dest ../100.txt
	PYTHONPATH=. poetry run python src/client/main.py upload uploads/abdasda

test-client-upload-user:
	PYTHONPATH=. poetry run python src/client/main.py --user clark --password kent upload uploads/A.md

test-client-upload-user-without-password:
	PYTHONPATH=. poetry run python src/client/main.py --user bar upload uploads/A.md

test-client-upload-user-multi:
	PYTHONPATH=. poetry run python src/client/main.py --user clark --password kent upload uploads/other/100.txt --dest a/100.txt
	PYTHONPATH=. poetry run python src/client/main.py --user clark --password kent upload uploads/other/100.txt --dest b/100.txt
	PYTHONPATH=. poetry run python src/client/main.py --user clark --password kent upload uploads/other/100.txt --dest a/c/100.txt
	PYTHONPATH=. poetry run python src/client/main.py --user clark --password kent upload uploads/other/100.txt --dest b/c/100.txt

test-client-upload-final:
	PYTHONPATH=. poetry run python src/client/main.py upload uploads/A.md
	PYTHONPATH=. poetry run python src/client/main.py upload uploads/block.txt
	PYTHONPATH=. poetry run python src/client/main.py upload uploads/block.txt --dest "ceptain america/block.txt"
	PYTHONPATH=. poetry run python src/client/main.py upload uploads/dir
	PYTHONPATH=. poetry run python src/client/main.py --user superman --password "clark kent" upload uploads/block.txt
	PYTHONPATH=. poetry run python src/client/main.py --user superman --password "clark kent" upload uploads/dir

test-client-download: temp
	PYTHONPATH=. poetry run python src/client/main.py download A.md ./temp/A.md

test-client-download-100: temp
	PYTHONPATH=. poetry run python src/client/main.py download 100.txt ./temp/100.txt

test-client-download-1000: temp
	PYTHONPATH=. poetry run python src/client/main.py download 1K.txt ./temp/1K.txt

test-client-download-10000: temp
	PYTHONPATH=. poetry run python src/client/main.py download 10K.txt ./temp/10K.txt

test-client-download-child: temp
	PYTHONPATH=. poetry run python src/client/main.py download child-dir/A.txt ./temp/child/A.txt

test-client-download-child-100: temp
	PYTHONPATH=. poetry run python src/client/main.py download child-dir/100.txt ./temp/child/100.txt

test-client-download-child-1000: temp
	PYTHONPATH=. poetry run python src/client/main.py download child-dir/1K.txt ./temp/child/1K.txt

test-client-download-child-10000: temp
	PYTHONPATH=. poetry run python src/client/main.py download child-dir/10K.txt ./temp/child/10K.txt

test-client-download-multi: temp
	PYTHONPATH=. poetry run python src/client/main.py download net.jpg ./temp/net.jpg
	PYTHONPATH=. poetry run python src/client/main.py download dir ./temp/dir
	PYTHONPATH=. poetry run python src/client/main.py download a/100.txt ./temp/a/100.txt
	PYTHONPATH=. poetry run python src/client/main.py download b/100.txt ./temp/b/100.txt
	PYTHONPATH=. poetry run python src/client/main.py download a/c/100.txt ./temp/a/c/100.txt
	PYTHONPATH=. poetry run python src/client/main.py download b/c/100.txt ./temp/b/c/100.txt

test-client-download-all: temp
	make test-client-download
	make test-client-download-child
	make test-client-download-100
	make test-client-download-child-100
	make test-client-download-1000
	make test-client-download-child-1000
	make test-client-download-multi

test-client-download-not-found: temp
	PYTHONPATH=. poetry run python src/client/main.py download ../.env ./temp/.enve
	PYTHONPATH=. poetry run python src/client/main.py download abdasda ./temp/abdasda

test-client-download-user: temp
	PYTHONPATH=. poetry run python src/client/main.py --user clark --password kent download A.md ./temp/A.md

test-client-download-user-without-password: temp
	PYTHONPATH=. poetry run python src/client/main.py --user bar download A.md ./temp/A.md

test-client-download-user-multi: temp
	PYTHONPATH=. poetry run python src/client/main.py --user clark --password kent download a/100.txt ./temp/a/100.txt
	PYTHONPATH=. poetry run python src/client/main.py --user clark --password kent download b/100.txt ./temp/b/100.txt
	PYTHONPATH=. poetry run python src/client/main.py --user clark --password kent download a/c/100.txt ./temp/a/c/100.txt
	PYTHONPATH=. poetry run python src/client/main.py --user clark --password kent download b/c/100.txt ./temp/b/c/100.txt

test-client-download-final: temp
	PYTHONPATH=. poetry run python src/client/main.py download A.md ./temp/A.md
	PYTHONPATH=. poetry run python src/client/main.py download block.txt ./temp/block.txt
	PYTHONPATH=. poetry run python src/client/main.py download "ceptain america/block.txt" "./temp/ceptain america block.txt"
	PYTHONPATH=. poetry run python src/client/main.py download dir ./temp/dir
	PYTHONPATH=. poetry run python src/client/main.py --user superman --password "clark kent" download block.txt ./temp/user-block.txt
	PYTHONPATH=. poetry run python src/client/main.py --user superman --password "clark kent" download dir ./temp/user-dir

test-client-list:
	PYTHONPATH=. poetry run python src/client/main.py list

test-client-list-recursive:
	PYTHONPATH=. poetry run python src/client/main.py list --recursive

test-client-list-child:
	PYTHONPATH=. poetry run python src/client/main.py list child-dir

test-client-list-a:
	PYTHONPATH=. poetry run python src/client/main.py list a

test-client-list-b:
	PYTHONPATH=. poetry run python src/client/main.py list b

test-client-list-a-c:
	PYTHONPATH=. poetry run python src/client/main.py list a/c

test-client-list-range:
	PYTHONPATH=. poetry run python src/client/main.py list range

test-client-list-not-found:
	PYTHONPATH=. poetry run python src/client/main.py list ..
	PYTHONPATH=. poetry run python src/client/main.py list abdasda

test-client-list-user:
	PYTHONPATH=. poetry run python src/client/main.py --user clark --password kent list

test-client-list-user-without-password:
	PYTHONPATH=. poetry run python src/client/main.py --user bar list .

test-client-list-user-multi:
	PYTHONPATH=. poetry run python src/client/main.py --user clark --password kent list
	PYTHONPATH=. poetry run python src/client/main.py --user clark --password kent list a
	PYTHONPATH=. poetry run python src/client/main.py --user clark --password kent list b

test-client-list-user-recursive:
	PYTHONPATH=. poetry run python src/client/main.py --user clark --password kent list --recursive
	PYTHONPATH=. poetry run python src/client/main.py --user bar list --recursive

test-client-list-final:
	PYTHONPATH=. poetry run python src/client/main.py list
	PYTHONPATH=. poetry run python src/client/main.py list --recursive
	PYTHONPATH=. poetry run python src/client/main.py list dir
	PYTHONPATH=. poetry run python src/client/main.py --user superman --password "clark kent" list
	PYTHONPATH=. poetry run python src/client/main.py --user superman --password "clark kent" list --recursive

test-client-delete:
	PYTHONPATH=. poetry run python src/client/main.py delete A.md

test-client-delete-100:
	PYTHONPATH=. poetry run python src/client/main.py delete 100.txt

test-client-delete-child:
	PYTHONPATH=. poetry run python src/client/main.py delete child-dir

test-client-delete-multi:
	PYTHONPATH=. poetry run python src/client/main.py delete net.jpg
	PYTHONPATH=. poetry run python src/client/main.py delete dir
	PYTHONPATH=. poetry run python src/client/main.py delete a/100.txt
	PYTHONPATH=. poetry run python src/client/main.py delete b/100.txt
	PYTHONPATH=. poetry run python src/client/main.py delete a/c/100.txt
	PYTHONPATH=. poetry run python src/client/main.py delete b/c/100.txt

test-client-delete-range:
	for i in {1..10..2}; do \
		PYTHONPATH=. poetry run python src/client/main.py delete range/$$i-$$i/$$i.txt ;\
		for j in {1..10..1}; do \
			PYTHONPATH=. poetry run python src/client/main.py delete range/$$i-$$j.txt ;\
		done; \
	done;

test-client-delete-all:
	make test-client-delete
	make test-client-delete-child
	make test-client-delete-100
	make test-client-delete-multi

test-client-delete-not-found:
	PYTHONPATH=. poetry run python src/client/main.py delete ../100.txt
	PYTHONPATH=. poetry run python src/client/main.py delete abdasda

test-client-delete-user:
	PYTHONPATH=. poetry run python src/client/main.py --user clark --password kent delete A.md

test-client-delete-user-without-password:
	PYTHONPATH=. poetry run python src/client/main.py --user bar delete A.md

test-client-delete-user-multi:
	PYTHONPATH=. poetry run python src/client/main.py --user clark --password kent delete a/100.txt
	PYTHONPATH=. poetry run python src/client/main.py --user clark --password kent delete b/100.txt
	PYTHONPATH=. poetry run python src/client/main.py --user clark --password kent delete a/c/100.txt
	PYTHONPATH=. poetry run python src/client/main.py --user clark --password kent delete b/c/100.txt

test-client-delete-root:
	PYTHONPATH=. poetry run python src/client/main.py delete .
	PYTHONPATH=. poetry run python src/client/main.py --user bar delete .
	PYTHONPATH=. poetry run python src/client/main.py --user clark --password kent delete .

test-client-delete-final:
	PYTHONPATH=. poetry run python src/client/main.py delete block.txt
	PYTHONPATH=. poetry run python src/client/main.py delete dir
	PYTHONPATH=. poetry run python src/client/main.py delete .
	PYTHONPATH=. poetry run python src/client/main.py --user superman --password "clark kent" delete .

test-client-not-found: test-client-upload-not-found test-client-download-not-found test-client-list-not-found test-client-delete-not-found

test-dhcp-release:
	sudo dhclient -r

test-dhcp-get-ip:
	sudo dhclient

test-dhcp-renew:
	sudo dhclient -r
	sudo dhclient

dhcp-show-my-ip:
	ip a

dhcp-show-apps-on-ports:
	sudo lsof -i -P -n | grep :67
	sudo lsof -i -P -n | grep :68

dhcp-kill-dhclient:
	sudo killall dhclient

dhcp-stop-dnsmasq:
	sudo killall dnsmasq

dhcp-edit-config-file:
	sudo nano /etc/dhcp/dhclient.conf

dhcp-edit-leases-file:
	sudo nano /var/lib/dhcp/dhclient.leases

test-dns-ask-google:
	nslookup google.com localhost

test-dns-ask-youtube:
	nslookup www.youtube.com localhost

test-dns-ask-wikipedia:
	nslookup en.wikipedia.org localhost

test-dns-ask-facebook:
	nslookup www.facebook.com localhost

test-dns-ask-app:
	nslookup app.final.project.local localhost

test-dns-all:
	nslookup app.final.project.local localhost
	nslookup google.com localhost
	nslookup google.com localhost
	sleep 300
	nslookup google.com localhost
	nslookup www.youtube.com localhost

test-dns-all-origin:
	nslookup google.com localhost
	nslookup google.com localhost
	nslookup google.com localhost
	nslookup www.youtube.com localhost
	nslookup www.youtube.com localhost
	nslookup en.wikipedia.org localhost
	nslookup www.facebook.com localhost
	nslookup app.final.project.local localhost
	nslookup app.final.project.local localhost
