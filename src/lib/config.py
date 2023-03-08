# global config for the applications

import logging


class Config:
    USER_ID: int = 1000
    GROUP_ID: int = 1000

    FILE_PATH_MAX_LENGTH: int = 256

    SOCKET_TIMEOUT: float = 0.1
    SOCKET_MAXSIZE: int = 64000
    CWND_START_VALUE: int = 1500

    LOGGING_LEVEL: int = logging.INFO


config = Config()


def init_logging() -> None:
    logging.basicConfig(level=config.LOGGING_LEVEL, format="%(asctime)s %(levelname)s: %(message)s", datefmt="%H:%M:%S")
