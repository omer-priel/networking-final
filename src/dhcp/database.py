# database

import json
import os
import os.path

import jsbeautifier
from pydantic import BaseModel

from src.dhcp.config import config


class Database(BaseModel):
    server_address: str = "192.168.122.1"
    network_interface: str = "virbr0"

    dns: str = "8.8.8.8"
    router: str = "169.254.0.0"
    subnet_mask: str = "255.255.255.0"

    pool_range: tuple[int, int] = (10, 50)

    ips: list[str] = []

    def get_prefix(self) -> str:
        return self.server_address[: self.server_address.rindex(".")] + "."

    def get_ip(self, wantIp: str) -> str | None:
        prefix = self.get_prefix()
        if wantIp.startswith(prefix) and wantIp not in (self.ips + [self.router, self.server_address]):
            return wantIp

        for i in range(self.pool_range[0], self.pool_range[1] + 1):
            yourIP = prefix + str(i)
            if yourIP not in (self.ips + [self.router, self.server_address]):
                return yourIP

        return None


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
