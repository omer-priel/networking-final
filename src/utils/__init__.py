# utils

import os
import logging

from dotenv import load_dotenv

class _config:
    APP_HOST: str | None = None
    APP_PORT: int | None = None
    CLIENT_HOST: str | None = None
    CLIENT_PORT: int | None = None

    SOCKET_TIMEOUT: int = 3
    LOGGING_LEVEL: int = logging.DEBUG


config = _config()


def init_config() -> None:
    load_dotenv()

    config.APP_HOST = os.getenv("APP_HOST")
    config.APP_PORT = int(os.getenv("APP_PORT"))
    config.CLIENT_HOST = os.getenv("CLIENT_HOST")
    config.CLIENT_PORT = int(os.getenv("CLIENT_PORT"))


def init_logging() -> None:
    logging.basicConfig(level=config.LOGGING_LEVEL, format='%(asctime)s %(levelname)s: %(message)s', datefmt='%H:%M:%S')
