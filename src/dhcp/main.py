# entry point to DHCP

import logging
import socket

from src.dhcp.config import config, init_config, init_logging
from src.dhcp.database import init_database, save_database
from src.dhcp.packets import *

# globals
receiverSocket: socket.socket
senderSocket: socket.socket


def create_socket() -> None:
    global receiverSocket, senderSocket

    receiverSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    receiverSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    receiverSocket.setblocking(1)
    receiverSocket.settimeout(config.SOCKET_TIMEOUT)
    receiverSocket.bind(("0.0.0.0", config.SERVER_PORT))

    senderSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    senderSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    senderSocket.setblocking(1)
    senderSocket.settimeout(config.SOCKET_TIMEOUT)
    senderSocket.bind(("0.0.0.0", config.CLIENT_PORT))

    logging.info(
        "The dhcp socket initialized on {} from port {} to {}".format(
            config.SERVER_HOST, config.SERVER_PORT, config.CLIENT_PORT
        )
    )


def main_loop() -> None:
    while True:
        try:
            data, clientAddress = receiverSocket.recvfrom(config.SOCKET_MAXSIZE)
        except socket.error:
            data = None
            pass

        if not data:
            continue

        pocket = DHCPPacket.from_bytes(data)
        print(pocket)
        print(bytes(pocket))

        if DHCPOptionKey.MessageType not in pocket.options:
            continue

        reqType: MessageType = pocket.options[DHCPOptionKey.MessageType]
        if reqType == MessageType.Unknown:
            continue

        if reqType == MessageType.Discover:
            pass


def main() -> None:
    init_config()
    init_logging()
    init_database()

    create_socket()

    main_loop()


if __name__ == "__main__":
    main()
