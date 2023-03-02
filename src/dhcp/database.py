# database

import os
import os.path
import json
import time

import jsbeautifier
from pydantic import BaseModel

from src.dhcp.config import config


class UsedIPInfo(BaseModel):
    expired_time: int


class Database(BaseModel):
    server_address: str = "192.168.100.1"
    network_interface: str = "virbr1"

    renewal_time: int = 30   # [s]
    rebinding_time: int = 50 # [s]

    router: str = "192.168.100.0"
    subnet_mask: str = "255.255.255.0"

    dns: str | None = "8.8.8.8"
    broadcast_address: str| None = None

    pool_range: tuple[int, int] = (10, 50)

    used_ips: dict[str, UsedIPInfo] = {}

    def get_prefix(self) -> str:
        return self.server_address[: self.server_address.rindex(".")] + "."

    def is_available(self, ip: str, prefix: str | None = None) -> bool:
        if not prefix:
            prefix = self.get_prefix()
        if not ip.startswith(prefix) or ip in [self.router, self.server_address]:
            return False
        return ip not in self.used_ips

    def get_ip(self, wantIp: str) -> str | None:
        prefix = self.get_prefix()
        if self.is_available(wantIp, prefix):
            return wantIp

        for i in range(self.pool_range[0], self.pool_range[1] + 1):
            yourIP = prefix + str(i)
            if self.is_available(yourIP, prefix):
                return yourIP

        return None

    def refresh_used_ips(self) -> None:
        now = int(time.time())
        ips = list(self.used_ips.keys())
        for ip in ips:
            if now > self.used_ips[ip].expired_time:
                self.used_ips.pop(ip)

        save_database(self)


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
