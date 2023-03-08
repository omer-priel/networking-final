# config of the DHCP server

import os

from dotenv import load_dotenv

from src.lib.config import Config
from src.lib.config import init_logging as base_init_logging


class AppConfig(Config):
    SERVER_PORT: int = 53
    PARENT_PORT: int = 8500

    DATABASE_PATH = "storage/dns.json"


config = AppConfig()


def init_config() -> None:
    if os.path.isfile("src/dns/.env"):
        load_dotenv("src/dns/.env")

    SERVER_PORT = os.getenv("SERVER_PORT")
    if SERVER_PORT:
        config.SERVER_PORT = int(SERVER_PORT)

    PARENT_PORT = os.getenv("PARENT_PORT")
    if PARENT_PORT:
        config.PARENT_PORT = int(PARENT_PORT)

    DATABASE_PATH = os.getenv("DATABASE_PATH")
    if DATABASE_PATH:
        config.DATABASE_PATH = DATABASE_PATH


def init_logging() -> None:
    base_init_logging()
