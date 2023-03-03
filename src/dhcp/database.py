# database

import json
import os
import os.path
import time

import jsbeautifier  # type: ignore
from pydantic import BaseModel

from src.dhcp.config import config


class IPAddressLease(BaseModel):
    expired_time: int


class Database(BaseModel):
    server_address: str = "192.168.100.1"
    network_interface: str = "virbr1"

    lease_time: int = 60  # [s]
    renewal_time: int = 30  # [s]
    rebinding_time: int = 50  # [s]

    router: str = "192.168.100.0"
    subnet_mask: str = "255.255.255.0"

    dns: str | None = "8.8.8.8"
    broadcast_address: str | None = None

    pool_range: tuple[int, int] = (10, 50)

    ip_address_leases: dict[str, IPAddressLease] = {}

    def get_prefix(self) -> str:
        return self.server_address[: self.server_address.rindex(".")] + "."

    def is_available(self, ip: str, prefix: str | None = None) -> bool:
        if not prefix:
            prefix = self.get_prefix()
        if not ip.startswith(prefix) or ip in [self.router, self.server_address]:
            return False
        return ip not in self.ip_address_leases

    def get_ip(self, wantIp: str | None) -> str | None:
        prefix = self.get_prefix()
        if wantIp:
            if self.is_available(wantIp, prefix):
                return wantIp

        for i in range(self.pool_range[0], self.pool_range[1] + 1):
            yourIP = prefix + str(i)
            if self.is_available(yourIP, prefix):
                return yourIP

        if self.clean_ip_address_leases():
            for i in range(self.pool_range[0], self.pool_range[1] + 1):
                yourIP = prefix + str(i)
                if self.is_available(yourIP, prefix):
                    return yourIP

        return None

    def clean_ip_address_leases(self) -> bool:
        now = int(time.time())
        ips = list(self.ip_address_leases.keys())
        for ip in ips:
            if now > self.ip_address_leases[ip].expired_time:
                self.ip_address_leases.pop(ip)
                save_database(self)
                return True

        return False


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
    os.chown(os.path.dirname(databasePath), config.USER_ID, config.GROUP_ID)

    with open(databasePath, "a") as f:
        opts = jsbeautifier.default_options()
        opts.indent_size = 2
        f.write(jsbeautifier.beautify(database.json(), opts))
        os.chown(databasePath, config.USER_ID, config.GROUP_ID)
