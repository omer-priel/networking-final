# config of the DHCP server

import os

from dotenv import load_dotenv

from src.lib.config import Config
from src.lib.config import init_logging as base_init_logging


class AppConfig(Config):
    SERVER_PORT: int = 67
    CLIENT_PORT: int = 68

    DATABASE_PATH = "storage/dhcp.json"


config = AppConfig()


def init_config() -> None:
    if os.path.isfile("src/dhcp/.env"):
        load_dotenv("src/dhcp/.env")

    SERVER_PORT = os.getenv("SERVER_PORT")
    if SERVER_PORT:
        config.SERVER_PORT = int(SERVER_PORT)

    CLIENT_PORT = os.getenv("CLIENT_PORT")
    if CLIENT_PORT:
        config.CLIENT_PORT = int(CLIENT_PORT)

    DATABASE_PATH = os.getenv("DATABASE_PATH")
    if DATABASE_PATH:
        config.DATABASE_PATH = DATABASE_PATH


def init_logging() -> None:
    base_init_logging()
