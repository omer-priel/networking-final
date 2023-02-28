# database

import os
import os.path

from pydantic import BaseModel

from src.dhcp.config import config


class StorageData(BaseModel):
    dns: str
    router: str
    subnetMask: str

    ips: dict[str] = {}


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
            f.write(storageData.json())


def get_path(path: str, storagePath: str) -> str:
    return storagePath + path


def in_storage(path: str, storagePath: str) -> bool:
    return os.path.commonpath(
        [os.path.abspath(get_path(path, storagePath)), os.path.abspath(storagePath)]
    ) == os.path.abspath(storagePath)
