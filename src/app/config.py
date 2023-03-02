# config of the apps

import os

from dotenv import load_dotenv

from src.lib.config import Config
from src.lib.config import init_logging as base_init_logging


class AppConfig(Config):
    APP_HOST: str = "localhost"
    APP_PORT: int = 8000
    APP_STORAGE_PATH: str = "storage"

    STORAGE_PUBLIC = "/public"
    STORAGE_PRIVATE = "/private"
    STORAGE_DATA = "/data.json"

    SINGLE_SEGMENT_SIZE_MIN = 10  # [byte]
    SINGLE_SEGMENT_SIZE_MAX = 1500  # [byte]


config = AppConfig()


def init_config() -> None:
    if os.path.isfile("src/app/.env"):
        load_dotenv("src/app/.env")

    APP_HOST = os.getenv("APP_HOST")
    if APP_HOST:
        config.APP_HOST = APP_HOST

    APP_PORT = os.getenv("APP_PORT")
    if APP_PORT:
        config.APP_PORT = int(APP_PORT)

    APP_STORAGE_PATH = os.getenv("APP_STORAGE_PATH")
    if APP_STORAGE_PATH:
        config.APP_STORAGE_PATH = APP_STORAGE_PATH


def init_logging() -> None:
    base_init_logging()
