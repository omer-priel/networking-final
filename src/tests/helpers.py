# helpers for testing

import os
import os.path
import shutil

TESTS_UPLOADS_DIRECTORY= "tests-files/uploads"
TESTS_DOWNLOADS_DIRECTORY = "tests-files/downloads"

APP_STORAGE_DIRECTORY = "storage"

def needs_downloads_directory(needsEmpty: bool = True) -> None:
    if os.path.isdir(TESTS_DOWNLOADS_DIRECTORY):
        if needsEmpty:
            shutil.rmtree(TESTS_DOWNLOADS_DIRECTORY)

    if not os.path.isdir(TESTS_DOWNLOADS_DIRECTORY):
        os.makedirs(TESTS_DOWNLOADS_DIRECTORY, exist_ok=True)
