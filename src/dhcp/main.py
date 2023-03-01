# entry point to DHCP

import logging
import socket

from src.dhcp.config import config, init_config, init_logging
from src.dhcp.database import Database, get_database, save_database
from src.dhcp.packets import *

# globals
dhcpSocket: socket.socket


# network
def create_socket(database: Database) -> None:
    global dhcpSocket

    dhcpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    dhcpSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    dhcpSocket.setsockopt(socket.SOL_SOCKET, 25, database.network_interface.encode())
    dhcpSocket.setblocking(1)
    dhcpSocket.settimeout(config.SOCKET_TIMEOUT)
    dhcpSocket.bind(("0.0.0.0", config.SERVER_PORT))

    logging.info("The dhcp socket initialized from port {}".format(config.SERVER_PORT))


def recvfrom() -> DHCPPacket | None:
    global dhcpSocket
    try:
        data = dhcpSocket.recvfrom(config.SOCKET_MAXSIZE)[0]
        packet = DHCPPacket.from_bytes(data)
        return packet
    except socket.error:
        return None


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


# handlers
def handle_discover(database: Database, packet: DHCPPacket) -> None:
    logging.info("Recive Discover")

    # create the offered address
    yourIPAddress = ""

    if DHCPOptionKey.RequestedIPAddress in packet.options:
        yourIPAddress = packet.options[DHCPOptionKey.RequestedIPAddress]

    yourIPAddress = database.get_ip(yourIPAddress)

    # create the response
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
    if DHCPOptionKey.ParamterRequestList in packet.options:
        if DHCPParameterRequest.DomainNameServer in packet.options[DHCPOptionKey.ParamterRequestList]:
            packet.options[DHCPOptionKey.DomainNameServer] = database.dns

    logging.info("Send Offer with ip " + yourIPAddress)
    broadcast(database, packet)


def handle_request(database: Database, packet: DHCPPacket) -> None:
    logging.info("Recive Request")

    if not handle_request_validation(database, packet):
        # send NAK message
        packet.op = 2
        packet.clientIPAddress = "0.0.0.0"
        packet.yourIPAddress = "0.0.0.0"
        packet.serverIPAddress = database.server_address
        packet.gatewayIPAddress = "0.0.0.0"

        packet.options = {}
        packet.options[DHCPOptionKey.MessageType] = MessageType.NAK
        packet.options[DHCPOptionKey.DHCPServer] = database.server_address

        logging.info("Send NAK")
        broadcast(database, packet)
        return None

    requestedIPAddress = packet.options[DHCPOptionKey.RequestedIPAddress]

    # save
    database.ips += [requestedIPAddress]
    save_database(database)
    logging.info("The ip " + requestedIPAddress + " is saved")

    # send the response
    packet.op = 2
    packet.clientIPAddress = "0.0.0.0"
    packet.yourIPAddress = requestedIPAddress
    packet.serverIPAddress = database.server_address
    packet.gatewayIPAddress = "0.0.0.0"

    packet.options[DHCPOptionKey.MessageType] = MessageType.ACK
    packet.options[DHCPOptionKey.SubnetMask] = database.subnet_mask
    packet.options[DHCPOptionKey.Router] = database.router
    packet.options[DHCPOptionKey.DHCPServer] = database.server_address
    if DHCPOptionKey.ParamterRequestList in packet.options:
        if DHCPParameterRequest.DomainNameServer in packet.options[DHCPOptionKey.ParamterRequestList]:
            packet.options[DHCPOptionKey.DomainNameServer] = database.dns

    broadcast(database, packet)
    logging.info("Send ACK")


def handle_request_validation(database: Database, packet: DHCPPacket) -> bool:
    # validation
    if DHCPOptionKey.DHCPServer not in packet.options:
        logging.error("Request: The DHCP Server IP Address option are missing")
        return False

    if packet.options[DHCPOptionKey.DHCPServer] != database.server_address:
        logging.error("Request: The DHCP Server IP address is not right")
        return False

    if DHCPOptionKey.RequestedIPAddress not in packet.options:
        logging.error("Request: The requested IP address option are missing")
        return False

    # check if the requested ip address is available
    requestedIPAddress = packet.options[DHCPOptionKey.RequestedIPAddress]

    if not database.is_available(requestedIPAddress):
        logging.error("Request: The requested IP address is not available")
        return False

    return True


def handle_release(database: Database, packet: DHCPPacket) -> None:
    pass


# controller
def main_loop(database: Database) -> None:
    while True:
        packet = recvfrom()

        if not packet:
            continue

        if DHCPOptionKey.MessageType not in packet.options:
            continue

        reqType: MessageType = packet.options[DHCPOptionKey.MessageType]
        if reqType == MessageType.Unknown:
            continue

        if reqType == MessageType.Discover:
            handle_discover(database, packet)
        elif reqType == MessageType.Request:
            handle_request(database, packet)
        elif reqType == MessageType.Release:
            handle_release(database, packet)


def main() -> None:
    init_config()
    init_logging()

    database = get_database()

    create_socket(database)

    main_loop(database)


if __name__ == "__main__":
    main()
