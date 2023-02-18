open-server:
	poetry run python server.py --port 8000 -u ./storage

upload-file:
	python client.py -p ./README.md 127.0.0.1 8000

download-file:
	python client.py -g ./README.md 127.0.0.1 8000
