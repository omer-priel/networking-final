# utils

import os

from dotenv import load_dotenv


class _config:
    APP_HOST: str | None = None
    APP_PORT: int | None = None


config = _config()


def init_config():
    load_dotenv()

    config.APP_HOST = os.getenv("APP_HOST")
    config.APP_PORT = int(os.getenv("APP_PORT"))
