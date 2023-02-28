# database

import json
import os
import os.path

import jsbeautifier

from pydantic import BaseModel

from src.dhcp.config import config


class Database(BaseModel):
    dns: str = "0.0.0.0"
    router: str = "0.0.0.0"
    subnetMask: str = "255.255.255.0"

    ips: list[str] = []


# global
database: Database


def init_database() -> None:
    global database

    databasePath = os.path.abspath(config.DATABASE_PATH)

    if os.path.isfile(databasePath):
        with open(databasePath, "r") as f:
            database = Database(**json.load(f))
    else:
        database = Database()
        save_database()


def save_database() -> None:
    databasePath = os.path.abspath(config.DATABASE_PATH)

    if os.path.isfile(databasePath):
        os.remove(databasePath)

    os.makedirs(os.path.dirname(databasePath), exist_ok=True)

    with open(databasePath, "a") as f:
        opts = jsbeautifier.default_options()
        opts.indent_size = 2
        f.write(jsbeautifier.beautify(database.json(), opts))
