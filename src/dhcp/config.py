# config of the DHCP server

import os

from src.lib.config import Config
from src.lib.config import init_logging as base_init_logging


class AppConfig(Config):
    SERVER_PORT: int = 67
    CLIENT_PORT: int = 68

    DATABASE_PATH = "storage/dhcp.json"


config = AppConfig()


def init_config() -> None:
    pass


def init_logging() -> None:
    base_init_logging()
