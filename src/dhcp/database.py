# database

import json
import os
import os.path

import jsbeautifier

from pydantic import BaseModel

from src.dhcp.config import config


class Database(BaseModel):
    dns: str = "8.8.8.8"
    router: str = "0.0.0.0"
    subnet_mask: str = "255.255.255.0"
    dhcp_server: str = "0.0.0.0"

    ips: list[str] = []


# global
def get_database() -> Database:
    databasePath = os.path.abspath(config.DATABASE_PATH)

    if os.path.isfile(databasePath):
        with open(databasePath, "r") as f:
            database = Database(**json.load(f))
    else:
        database = Database()
        save_database(database)

    return database


def save_database(database: Database) -> None:
    databasePath = os.path.abspath(config.DATABASE_PATH)

    if os.path.isfile(databasePath):
        os.remove(databasePath)

    os.makedirs(os.path.dirname(databasePath), exist_ok=True)

    with open(databasePath, "a") as f:
        opts = jsbeautifier.default_options()
        opts.indent_size = 2
        f.write(jsbeautifier.beautify(database.json(), opts))
