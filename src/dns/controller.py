# controller

import logging
import socket

from src.dns.config import config
from src.dns.database import Database
from src.dns.handlers import request_handler
from src.dns.packets import DNSPacket


def create_socket() -> tuple[socket.socket, socket.socket]:
    clientsSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    clientsSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    clientsSocket.setblocking(True)
    clientsSocket.settimeout(config.SOCKET_TIMEOUT)
    clientsSocket.bind(("0.0.0.0", config.SERVER_PORT))

    logging.info("The dns socket initialized on port {}".format(config.SERVER_PORT))

    parentSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    parentSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    parentSocket.setblocking(True)
    parentSocket.settimeout(config.SOCKET_TIMEOUT)
    parentSocket.bind(("0.0.0.0", config.PARENT_PORT))

    return (clientsSocket, parentSocket)


def recvfrom(clientsSocket: socket.socket) -> tuple[DNSPacket, tuple[str, int]] | None:
    try:
        data, clientAddress = clientsSocket.recvfrom(config.SOCKET_MAXSIZE)
        packet = DNSPacket.from_bytes(data)
        return (packet, clientAddress)
    except socket.error:
        return None


def main_loop(database: Database) -> None:
    clientsSocket, parentSocket = create_socket()

    while True:
        res = recvfrom(clientsSocket)

        if not res:
            continue

        packet, clientAddress = res

        if packet.flags.isResponse:
            continue

        request_handler(clientsSocket, parentSocket, database, packet, clientAddress)
