# entry point to DHCP

import logging
import socket
import time

from src.dhcp.config import config, init_config, init_logging
from src.dhcp.database import Database, UsedIPInfo, get_database, save_database
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


# handlers midalwer
def create_additional_options(database: Database, packet: DHCPPacket) -> dict[DHCPOptionKey, DHCPOptionValue]:
    additional_options = {}
    additional_options[DHCPOptionKey.DHCPServer] = database.server_address

    additional_options[DHCPOptionKey.RenewalTime] = database.renewal_time
    additional_options[DHCPOptionKey.RebindingTime] = database.rebinding_time

    additional_options[DHCPOptionKey.SubnetMask] = database.subnet_mask
    additional_options[DHCPOptionKey.Router] = database.router

    if DHCPOptionKey.ParamterRequestList in packet.options:
        if DHCPParameterRequest.DomainNameServer in packet.options[DHCPOptionKey.ParamterRequestList] and database.dns:
            additional_options[DHCPOptionKey.DomainNameServer] = database.dns
        if DHCPParameterRequest.BroadcastAddress in packet.options[DHCPOptionKey.ParamterRequestList] and database.broadcast_address:
            additional_options[DHCPOptionKey.BroadcastAddress] = database.broadcast_address

    return additional_options

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

    additional_options = create_additional_options(database, packet)
    for key in additional_options:
         packet.options[key] = additional_options[key]

    logging.info("Send Offer with ip " + yourIPAddress)
    broadcast(database, packet)


def handle_request(database: Database, packet: DHCPPacket) -> None:
    logging.info("Recive Request")

    if not handle_request_validation(database, packet):
        print(database.used_ips)
        print(packet)

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
    database.used_ips[requestedIPAddress] = UsedIPInfo(expired_time=int(time.time()) + database.rebinding_time)
    save_database(database)
    logging.info("The ip " + requestedIPAddress + " is saved")

    # send the response
    packet.op = 2
    packet.clientIPAddress = "0.0.0.0"
    packet.yourIPAddress = requestedIPAddress
    packet.serverIPAddress = database.server_address
    packet.gatewayIPAddress = "0.0.0.0"

    packet.options[DHCPOptionKey.MessageType] = MessageType.ACK

    additional_options = create_additional_options(database, packet)
    for key in additional_options:
         packet.options[key] = additional_options[key]

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
    logging.info("Recive Release")


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

        database.refresh_used_ips()

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
