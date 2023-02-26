# global config for the applications

import logging


class Config:
    FILE_PATH_MAX_LENGTH = 256

    SOCKET_TIMEOUT: int = 3
    SOCKET_MAXSIZE: int = 4096
    LOGGING_LEVEL: int = logging.DEBUG


config = Config()


def init_logging() -> None:
    logging.basicConfig(level=config.LOGGING_LEVEL, format="%(asctime)s %(levelname)s: %(message)s", datefmt="%H:%M:%S")
