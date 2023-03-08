# database

import json
import os
import os.path
import time

import jsbeautifier  # type: ignore
from pydantic import BaseModel

from src.dns.config import config


class Record(BaseModel):
    ip_address: str


class CacheRecord(Record):
    expired_time: int  # [s]


class RecordData:
    domain_name: str
    ip_address: str
    ttl: int

    def __init__(self, domain_name: str, ip_address: str, ttl: int) -> None:
        self.domain_name = domain_name
        self.ip_address = ip_address
        self.ttl = ttl


class Database(BaseModel):
    parent_dns: str = "8.8.8.8"

    static_ttl: int = 360  # [s]
    static_records: dict[str,Record] = {}  # domain name : Record

    cache_records: dict[str,CacheRecord] = {} # domain name : CacheRecord

    def get_active_record(self, domainName: str) -> RecordData | None:
        if domainName in self.static_records:
            return RecordData(domainName, self.static_records[domainName].ip_address, self.static_ttl)

        if domainName in self.cache_records:
            record = self.cache_records[domainName]
            now = int(time.time())

            if record.expired_time < now:
                self.cache_records.pop(domainName)
                save_database(self)
                return None

            return RecordData(domainName, record.ip_address, record.expired_time - now)

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
    os.chown(os.path.dirname(databasePath), config.USER_ID, config.GROUP_ID)

    with open(databasePath, "a") as f:
        opts = jsbeautifier.default_options()
        opts.indent_size = 2
        f.write(jsbeautifier.beautify(database.json(), opts))
        os.chown(databasePath, config.USER_ID, config.GROUP_ID)
