# controller

import logging
import socket

from src.dns.config import config
from src.dns.database import Database
from src.dns.packets import DNSPacket
from src.dns.handlers import request_handler

# network
def create_socket() -> socket.socket:
    dnsSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    dnsSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    dnsSocket.setblocking(True)
    dnsSocket.settimeout(config.SOCKET_TIMEOUT)
    dnsSocket.bind(("0.0.0.0", config.SERVER_PORT))

    logging.info("The dhcp socket initialized on port {}".format(config.SERVER_PORT))
    return dnsSocket


def recvfrom(dhcpSocket: socket.socket) -> tuple[DNSPacket, tuple[str, int]] | None:
    try:
        data, clientAddress = dhcpSocket.recvfrom(config.SOCKET_MAXSIZE)
        packet = DNSPacket.from_bytes(data)
        return (packet, clientAddress)
    except socket.error:
        return None


def main_loop(database: Database) -> None:
    dnsSocket = create_socket()

    while True:
        res = recvfrom(dnsSocket)

        if not res:
            continue

        packet, clientAddress = res

        if packet.flags.isResponse:
            continue

        request_handler(dnsSocket, database, packet, clientAddress)
