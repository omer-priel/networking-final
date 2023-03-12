# testing upload command

import filecmp
import os
import time

from src.tests.helpers import APP_STORAGE_DIRECTORY, TESTS_UPLOADS_DIRECTORY


def test_app_upload_empty() -> None:
    os.system("poetry run python src/client/main.py upload {}/empty.md".format(TESTS_UPLOADS_DIRECTORY))

    assert filecmp.cmp(TESTS_UPLOADS_DIRECTORY + "/empty.md", APP_STORAGE_DIRECTORY + "/public/empty.md")


def test_app_upload_simple() -> None:
    os.system(
        "poetry run python src/client/main.py upload {}/md.md --dest md-renamed.md".format(TESTS_UPLOADS_DIRECTORY)
    )

    assert filecmp.cmp(TESTS_UPLOADS_DIRECTORY + "/md.md", APP_STORAGE_DIRECTORY + "/public/md-renamed.md")


def test_app_upload_simple_dest() -> None:
    os.system(
        "poetry run python src/client/main.py upload {}/md.md --dest dir/md-renamed.md".format(TESTS_UPLOADS_DIRECTORY)
    )

    assert filecmp.cmp(TESTS_UPLOADS_DIRECTORY + "/md.md", APP_STORAGE_DIRECTORY + "/public/dir/md-renamed.md")


def test_app_upload_block() -> None:
    os.system("poetry run python src/client/main.py upload {}/block.txt".format(TESTS_UPLOADS_DIRECTORY))

    assert filecmp.cmp(TESTS_UPLOADS_DIRECTORY + "/block.txt", APP_STORAGE_DIRECTORY + "/public/block.txt")


def test_app_upload_binary_files() -> None:
    files = ["document.pdf", "image.png", "image.tif", "md.md"]
    for fileName in files:
        os.system(
            "poetry run python src/client/main.py upload {}/{} --dest {}".format(
                TESTS_UPLOADS_DIRECTORY, fileName, fileName
            )
        )
        time.sleep(1)
        assert filecmp.cmp(
            TESTS_UPLOADS_DIRECTORY + "/{}".format(fileName), APP_STORAGE_DIRECTORY + "/public/{}".format(fileName)
        )


def test_app_upload_big_binary_files() -> None:
    files = ["audio.mp3", "video.avi"]
    for fileName in files:
        os.system(
            "poetry run python src/client/main.py upload {}/{} --dest {}".format(
                TESTS_UPLOADS_DIRECTORY, fileName, fileName
            )
        )
        time.sleep(1)
        assert filecmp.cmp(
            TESTS_UPLOADS_DIRECTORY + "/{}".format(fileName), APP_STORAGE_DIRECTORY + "/public/{}".format(fileName)
        )
