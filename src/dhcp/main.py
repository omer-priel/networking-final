# entry point to DHCP

import logging
import socket

from src.dhcp.config import config, init_config, init_logging
from src.dhcp.database import Database, get_database, save_database
from src.dhcp.packets import *

# globals
receiverSocket: socket.socket
senderSocket: socket.socket


def create_socket(database: Database) -> None:
    global dhcpSocket

    dhcpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    dhcpSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    dhcpSocket.setsockopt(socket.SOL_SOCKET, 25, database.network_interface.encode())
    dhcpSocket.setblocking(1)
    dhcpSocket.settimeout(config.SOCKET_TIMEOUT)
    dhcpSocket.bind(("0.0.0.0", config.SERVER_PORT))

    logging.info("The dhcp socket initialized from port {}".format(config.SERVER_PORT))


def recvfrom() -> tuple[bytes | None, tuple[str, int] | None]:
    global dhcpSocket
    try:
        return dhcpSocket.recvfrom(config.SOCKET_MAXSIZE)
    except socket.error:
        return None, None


def broadcast(database: Database, packet: DHCPPacket) -> None:
    broadcastSocket = socket.socket(type=socket.SOCK_DGRAM)
    broadcastSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    broadcastSocket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    broadcastSocket.setsockopt(socket.SOL_SOCKET, 25, database.network_interface.encode())
    broadcastSocket.bind((database.server_address, config.SERVER_PORT))
    try:
        data = bytes(packet)
        broadcastSocket.sendto(data, ("255.255.255.255", config.CLIENT_PORT))
        broadcastSocket.sendto(data, (database.server_address, config.CLIENT_PORT))
    finally:
        broadcastSocket.close()


def main_loop(database: Database) -> None:
    while True:
        data, clientAddress = recvfrom()

        if not data:
            continue

        packet = DHCPPacket.from_bytes(data)

        if DHCPOptionKey.MessageType not in packet.options:
            continue

        reqType: MessageType = packet.options[DHCPOptionKey.MessageType]
        if reqType == MessageType.Unknown:
            continue

        if reqType == MessageType.Discover:
            logging.info("Recive Discover")
            returnDNS = False
            if DHCPOptionKey.ParamterRequestList in packet.options:
                returnDNS = DHCPParameterRequest.DomainNameServer in packet.options[DHCPOptionKey.ParamterRequestList]

            yourIPAddress = ""

            # yourIPAddress
            if DHCPOptionKey.RequestedIPAddress in packet.options:
                yourIPAddress = packet.options[DHCPOptionKey.RequestedIPAddress]

            yourIPAddress = database.get_ip(yourIPAddress)

            # response
            packet.op = 2
            packet.clientIPAddress = "0.0.0.0"
            packet.yourIPAddress = yourIPAddress
            packet.serverIPAddress = database.server_address
            packet.gatewayIPAddress = "0.0.0.0"

            packet.options = {}
            packet.options[DHCPOptionKey.MessageType] = MessageType.Offer
            packet.options[DHCPOptionKey.SubnetMask] = database.subnet_mask
            packet.options[DHCPOptionKey.Router] = database.router
            packet.options[DHCPOptionKey.DHCPServer] = database.server_address
            if returnDNS:
                packet.options[DHCPOptionKey.DomainNameServer] = database.dns

            print(clientAddress)
            print(packet)

            broadcast(database, packet)
            logging.info("Send Offer with ip " + yourIPAddress)


def main() -> None:
    init_config()
    init_logging()

    database = get_database()

    create_socket(database)

    main_loop(database)


if __name__ == "__main__":
    main()
