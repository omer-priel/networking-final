# testing upload command

import filecmp
import os
import time

from src.tests.helpers import APP_STORAGE_DIRECTORY, TESTS_DOWNLOADS_DIRECTORY
from src.tests.test_app_upload import (
    test_app_upload_big_binary_files,
    test_app_upload_binary_files,
    test_app_upload_block,
    test_app_upload_empty,
    test_app_upload_simple,
    test_app_upload_simple_dest,
)


def test_app_download_empty() -> None:
    test_app_upload_empty()
    os.system("poetry run python src/client/main.py download empty.md {}/empty.md".format(TESTS_DOWNLOADS_DIRECTORY))

    assert filecmp.cmp(APP_STORAGE_DIRECTORY + "/public/empty.md", TESTS_DOWNLOADS_DIRECTORY + "/empty.md")


def test_app_download_simple() -> None:
    test_app_upload_simple()
    os.system(
        "poetry run python src/client/main.py download md-renamed.md {}/md-renamed.md".format(TESTS_DOWNLOADS_DIRECTORY)
    )

    assert filecmp.cmp(APP_STORAGE_DIRECTORY + "/public/md-renamed.md", TESTS_DOWNLOADS_DIRECTORY + "/md-renamed.md")


def test_app_download_simple_dest() -> None:
    test_app_upload_simple_dest()
    os.system(
        "poetry run python src/client/main.py download dir/md-renamed.md {}/dir/md-renamed.md".format(
            TESTS_DOWNLOADS_DIRECTORY
        )
    )

    assert filecmp.cmp(
        APP_STORAGE_DIRECTORY + "/public/dir/md-renamed.md", TESTS_DOWNLOADS_DIRECTORY + "/dir/md-renamed.md"
    )


def test_app_download_block() -> None:
    test_app_upload_block()
    os.system("poetry run python src/client/main.py download block.txt {}/block.txt".format(TESTS_DOWNLOADS_DIRECTORY))

    assert filecmp.cmp(APP_STORAGE_DIRECTORY + "/public/block.txt", TESTS_DOWNLOADS_DIRECTORY + "/block.txt")


def test_app_download_binary_files() -> None:
    test_app_upload_binary_files()

    files = ["document.pdf", "image.png", "image.tif", "md.md"]
    for fileName in files:
        os.system(
            "poetry run python src/client/main.py download {} {}/{}".format(
                fileName, TESTS_DOWNLOADS_DIRECTORY, fileName
            )
        )
        time.sleep(1)
        assert filecmp.cmp(
            APP_STORAGE_DIRECTORY + "/public/{}".format(fileName), TESTS_DOWNLOADS_DIRECTORY + "/{}".format(fileName)
        )


def test_app_download_big_binary_files() -> None:
    test_app_upload_big_binary_files()

    files = ["audio.mp3", "video.avi"]
    for fileName in files:
        os.system(
            "poetry run python src/client/main.py download {} {}/{}".format(
                fileName, TESTS_DOWNLOADS_DIRECTORY, fileName
            )
        )
        time.sleep(1)
        assert filecmp.cmp(
            APP_STORAGE_DIRECTORY + "/public/{}".format(fileName), TESTS_DOWNLOADS_DIRECTORY + "/{}".format(fileName)
        )
