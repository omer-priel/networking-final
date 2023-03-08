# controller

import logging
import socket

from src.dns.config import config
from src.dns.database import Database
from src.dns.packets import DNSPacket
from src.dns.handlers import request_handler


def create_socket() -> tuple[socket.socket, socket.socket]:
    dnsSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    dnsSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    dnsSocket.setblocking(True)
    dnsSocket.settimeout(config.SOCKET_TIMEOUT)
    dnsSocket.bind(("0.0.0.0", config.SERVER_PORT))

    logging.info("The dhcp socket initialized on port {}".format(config.SERVER_PORT))

    parentSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    parentSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    parentSocket.setblocking(True)
    parentSocket.settimeout(config.SOCKET_TIMEOUT)
    parentSocket.bind(("0.0.0.0", config.PARENT_PORT))

    return (dnsSocket, parentSocket)


def recvfrom(dhcpSocket: socket.socket) -> tuple[DNSPacket, tuple[str, int]] | None:
    try:
        data, clientAddress = dhcpSocket.recvfrom(config.SOCKET_MAXSIZE)
        packet = DNSPacket.from_bytes(data)
        return (packet, clientAddress)
    except socket.error:
        return None


def main_loop(database: Database) -> None:
    dnsSocket, parentSocket = create_socket()

    while True:
        res = recvfrom(dnsSocket)

        if not res:
            continue

        packet, clientAddress = res

        if packet.flags.isResponse:
            continue

        request_handler(dnsSocket, parentSocket, database, packet, clientAddress)
