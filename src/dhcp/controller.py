# controller

import logging
import socket

from src.dhcp.config import config
from src.dhcp.database import Database
from src.dhcp.handlers import handle_discover, handle_release, handle_renewal_request, handle_request
from src.dhcp.packets import DHCPOptionKey, DHCPPacket, MessageType


# network
def create_socket(database: Database) -> socket.socket:
    dhcpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    dhcpSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    dhcpSocket.setsockopt(socket.SOL_SOCKET, 25, database.network_interface.encode())
    dhcpSocket.setblocking(True)
    dhcpSocket.settimeout(config.SOCKET_TIMEOUT)
    dhcpSocket.bind(("0.0.0.0", config.SERVER_PORT))

    logging.info("The dhcp socket initialized from port {}".format(config.SERVER_PORT))
    return dhcpSocket


def recvfrom(dhcpSocket: socket.socket) -> DHCPPacket | None:
    try:
        data = dhcpSocket.recvfrom(config.SOCKET_MAXSIZE)[0]
        packet = DHCPPacket.from_bytes(data)
        return packet
    except socket.error:
        return None


def main_loop(database: Database) -> None:
    dhcpSocket = create_socket(database)

    while True:
        packet = recvfrom(dhcpSocket)

        if not packet:
            continue

        if DHCPOptionKey.MessageType not in packet.options:
            continue

        reqType = packet.options[DHCPOptionKey.MessageType]
        assert isinstance(reqType, MessageType)
        if reqType == MessageType.Unknown:
            continue

        if reqType == MessageType.Discover:
            handle_discover(database, packet)
        elif reqType == MessageType.Request:
            if packet.clientIPAddress not in database.ip_address_leases:
                handle_request(database, packet)
            else:
                handle_renewal_request(database, packet)
        elif reqType == MessageType.Release:
            handle_release(database, packet)
