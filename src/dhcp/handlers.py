# handlers

import logging
import socket
import time

from src.dhcp.config import config
from src.dhcp.database import Database, IPAddressLease, save_database
from src.dhcp.packets import DHCPOptionKey, DHCPOptionValue, DHCPPacket, DHCPParameterRequest, MessageType


# networking
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


# handlers helpers
def create_additional_options(database: Database, packet: DHCPPacket) -> dict[DHCPOptionKey, DHCPOptionValue]:
    additional_options: dict[DHCPOptionKey, DHCPOptionValue] = {}

    additional_options[DHCPOptionKey.DHCPServer] = database.server_address

    additional_options[DHCPOptionKey.IPAddressLeaseTime] = database.lease_time
    additional_options[DHCPOptionKey.RenewalTime] = database.renewal_time
    additional_options[DHCPOptionKey.RebindingTime] = database.rebinding_time

    additional_options[DHCPOptionKey.SubnetMask] = database.subnet_mask
    additional_options[DHCPOptionKey.Router] = database.router

    paramterReqestList = packet.options[DHCPOptionKey.ParamterRequestList]
    if DHCPOptionKey.ParamterRequestList in packet.options and isinstance(paramterReqestList, list):
        if DHCPParameterRequest.DomainNameServer in paramterReqestList and database.dns:
            additional_options[DHCPOptionKey.DomainNameServer] = database.dns
        if DHCPParameterRequest.BroadcastAddress in paramterReqestList and database.broadcast_address:
            additional_options[DHCPOptionKey.BroadcastAddress] = database.broadcast_address

    return additional_options


# handlers
def handle_discover(database: Database, packet: DHCPPacket) -> None:
    logging.info("Recive Discover")

    # create the offered address
    yourIPAddress: str | None = None

    if DHCPOptionKey.RequestedIPAddress in packet.options:
        requestedIPAddress = packet.options[DHCPOptionKey.RequestedIPAddress]
        assert isinstance(requestedIPAddress, str)
        yourIPAddress = requestedIPAddress

    yourIPAddress = database.get_ip(yourIPAddress)

    if not yourIPAddress:
        return None

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
        print(database.ip_address_leases)
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
    assert isinstance(requestedIPAddress, str)  # mypy

    # save
    database.ip_address_leases[requestedIPAddress] = IPAddressLease(expired_time=int(time.time()) + database.lease_time)
    save_database(database)
    logging.info("The ip " + requestedIPAddress + " are saved")

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
    if DHCPOptionKey.DHCPServer in packet.options:
        if packet.options[DHCPOptionKey.DHCPServer] != database.server_address:
            logging.warn("Request: The DHCP Server IP address is not this server")
            return False

    if DHCPOptionKey.RequestedIPAddress not in packet.options:
        logging.error("Request: The requested IP address option are missing")
        return False

    # check if the requested ip address is available
    requestedIPAddress = packet.options[DHCPOptionKey.RequestedIPAddress]
    assert isinstance(requestedIPAddress, str)  # mypy

    if not database.is_available(requestedIPAddress):
        logging.error("Request: The requested IP address is not available")
        return False

    return True


def handle_renewal_request(database: Database, packet: DHCPPacket) -> None:
    clientIPAddress = packet.clientIPAddress

    # save
    database.ip_address_leases[clientIPAddress] = IPAddressLease(expired_time=int(time.time()) + database.lease_time)
    save_database(database)
    logging.info("The ip " + clientIPAddress + " are renewaled")

    # send the response
    packet.op = 2
    packet.clientIPAddress = clientIPAddress
    packet.yourIPAddress = clientIPAddress
    packet.serverIPAddress = database.server_address
    packet.gatewayIPAddress = "0.0.0.0"

    packet.options[DHCPOptionKey.MessageType] = MessageType.ACK

    additional_options = create_additional_options(database, packet)
    for key in additional_options:
        packet.options[key] = additional_options[key]

    broadcast(database, packet)
    logging.info("Send ACK")


def handle_release(database: Database, packet: DHCPPacket) -> None:
    logging.info("Recive Release")

    clientIPAddress = packet.clientIPAddress

    if clientIPAddress not in database.ip_address_leases:
        return None

    # Release the ip address
    database.ip_address_leases.pop(clientIPAddress)
    save_database(database)
    logging.info("The ip " + clientIPAddress + " are released")
