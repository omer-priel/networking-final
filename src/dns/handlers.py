# DNS handlers

import socket

from src.dns.database import Database
from src.dns.packets import DNSPacket

def request_handler(dnsSocket: socket.socket, database: Database, query: DNSPacket, clientAddress: tuple[str, int]) -> None:
    print(query)
