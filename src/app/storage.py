# storage and database

import os
import os.path

import jsbeautifier  # type: ignore
from pydantic import BaseModel

from src.app.config import config


class UserData(BaseModel):
    id: str
    password: str


class StorageData(BaseModel):
    users: dict[str, UserData] = {}


def init_strorage() -> None:
    if not os.path.isdir(config.APP_STORAGE_PATH):
        os.mkdir(config.APP_STORAGE_PATH)

    if not os.path.isdir(config.APP_STORAGE_PATH + config.STORAGE_PUBLIC):
        os.mkdir(config.APP_STORAGE_PATH + config.STORAGE_PUBLIC)

    if not os.path.isdir(config.APP_STORAGE_PATH + config.STORAGE_PRIVATE):
        os.mkdir(config.APP_STORAGE_PATH + config.STORAGE_PRIVATE)

    if not os.path.isfile(config.APP_STORAGE_PATH + config.STORAGE_DATA):
        storageData = StorageData()
        with open(config.APP_STORAGE_PATH + config.STORAGE_DATA, "a") as f:
            opts = jsbeautifier.default_options()
            opts.indent_size = 2
            f.write(jsbeautifier.beautify(storageData.json(), opts))


def get_path(path: str, storagePath: str) -> str:
    return os.path.abspath(os.path.join(storagePath, path))


def in_storage(path: str, storagePath: str) -> bool:
    return os.path.commonpath(
        [os.path.abspath(get_path(path, storagePath)), os.path.abspath(storagePath)]
    ) == os.path.abspath(storagePath)
