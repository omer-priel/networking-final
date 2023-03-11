# testing upload command

import os
import filecmp
import time
import pytest

from src.tests.helpers import TESTS_DOWNLOADS_DIRECTORY, APP_STORAGE_DIRECTORY
from src.tests.test_app_upload import test_app_upload_empty, test_app_upload_simple, test_app_upload_block, test_app_upload_simple_dest, test_app_upload_binary_files, test_app_upload_big_binary_files

def test_app_download_empty():
    test_app_upload_empty()
    os.system("poetry run python src/client/main.py download empty.md {}/empty.md".format(TESTS_DOWNLOADS_DIRECTORY))

    assert filecmp.cmp(APP_STORAGE_DIRECTORY + "/public/empty.md", TESTS_DOWNLOADS_DIRECTORY + "/empty.md")


def test_app_download_simple():
    test_app_upload_simple()
    os.system("poetry run python src/client/main.py download md-renamed.md {}/md-renamed.md".format(TESTS_DOWNLOADS_DIRECTORY))

    assert filecmp.cmp(APP_STORAGE_DIRECTORY + "/public/md-renamed.md", TESTS_DOWNLOADS_DIRECTORY + "/md-renamed.md")


def test_app_download_simple_dest():
    test_app_upload_simple_dest()
    os.system("poetry run python src/client/main.py download dir/md-renamed.md {}/dir/md-renamed.md".format(TESTS_DOWNLOADS_DIRECTORY))

    assert filecmp.cmp(APP_STORAGE_DIRECTORY + "/public/dir/md-renamed.md", TESTS_DOWNLOADS_DIRECTORY + "/dir/md-renamed.md")


def test_app_download_block():
    test_app_upload_block()
    os.system("poetry run python src/client/main.py download block.txt {}/block.txt".format(TESTS_DOWNLOADS_DIRECTORY))

    assert filecmp.cmp(APP_STORAGE_DIRECTORY + "/public/block.txt", TESTS_DOWNLOADS_DIRECTORY + "/block.txt")


def test_app_download_binary_files():
    test_app_upload_binary_files()

    files = ["document.pdf", "image.png", "image.tif", "md.md"]
    for fileName in files:
        os.system("poetry run python src/client/main.py download {} {}/{}".format(fileName, TESTS_DOWNLOADS_DIRECTORY, fileName))
        time.sleep(1)
        assert filecmp.cmp(APP_STORAGE_DIRECTORY + "/public/{}".format(fileName), TESTS_DOWNLOADS_DIRECTORY + "/{}".format(fileName))


#@pytest.mark.skip()
def test_app_download_big_binary_files():
    test_app_upload_big_binary_files()

    files = ["audio.mp3", "video.avi", "video.mp4"]
    for fileName in files:
        os.system("poetry run python src/client/main.py download {} {}/{}".format(fileName, TESTS_DOWNLOADS_DIRECTORY, fileName))
        time.sleep(1)
        assert filecmp.cmp(APP_STORAGE_DIRECTORY + "/public/{}".format(fileName), TESTS_DOWNLOADS_DIRECTORY + "/{}".format(fileName))
