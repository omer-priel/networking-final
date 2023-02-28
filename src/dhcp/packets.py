# dhcp packets

from __future__ import annotations

import socket
import struct
from enum import IntEnum

# struct link: https://docs.python.org/3.7/library/struct.html


class DHCPOptionKey(IntEnum):
    Padding = 0
    End = 255
    MessageType = 53
    RequestedIPAddress = 50
    HostName = 12
    ParamterRequestList = 55

    @staticmethod
    def has_value(value: int) -> bool:
        return value in DHCPOptionKey._value2member_map_


class MessageType(IntEnum):
    Unknown = 0
    Discover = 1
    Offer = 2
    Request = 3
    Decline = 4
    ACK = 5
    Release = 7

    @staticmethod
    def has_value(value: int) -> bool:
        return value in MessageType._value2member_map_

    @staticmethod
    def from_value(value: int) -> MessageType:
        if not MessageType.has_value(value):
            return MessageType.Unknown

        return MessageType(value)


class DHCPParameterRequest(IntEnum):
    Unknown = 0
    SubnetMask = 1
    Router = 3
    DomainNameServer = 6

    @staticmethod
    def has_value(value: int) -> bool:
        return value in DHCPParameterRequest._value2member_map_

    @staticmethod
    def from_value(value: int) -> DHCPParameterRequest:
        if not DHCPParameterRequest.has_value(value):
            return DHCPParameterRequest.Unknown

        return DHCPParameterRequest(value)

DHCPOptionValue = bytes | MessageType | str | int | list[DHCPParameterRequest]

class DHCPPacket:
    def __init__(self, data: bytes) -> None:
        offset = 0

        self.op, self.htype, self.hlen, self.hops = data[offset : offset + 4]
        offset += 4

        self.xid = struct.unpack_from("I", data, offset)[0]
        offset += 4

        self.secs, self.flags = struct.unpack_from("HH", data, offset)
        offset += 4

        self.clientIPAddress = socket.inet_ntoa(data[offset : offset + 4])
        offset += 4

        self.yourIPAddress = socket.inet_ntoa(data[offset : offset + 4])
        offset += 4

        self.serverIPAddress = socket.inet_ntoa(data[offset : offset + 4])
        offset += 4

        self.relayIPAddress = socket.inet_ntoa(data[offset : offset + 4])
        offset += 4

        self.clientEthernetAddress = data[offset : offset + 16]
        offset += 16

        # 192 octets of 0s, or overflow space for additional options; BOOTP legacy.
        offset += 192

        self.magicCookie = struct.unpack_from("I", data, offset)[0]
        offset += 4

        self.options: dict[DHCPOptionKey, DHCPOptionValue] = {}

        while offset + 1 < len(data) and int(data[offset]) != int(DHCPOptionKey.End):
            optionKey = int(data[offset])
            optionLength = int(data[offset + 1])
            offset += 2

            if DHCPOptionKey.has_value(optionKey):
                optionValue = b""
                if optionLength > 0:
                    optionValue = data[offset : offset + optionLength]

                self.options[optionKey] = bytes2dhcpOptionValue(optionKey, optionValue)

            offset += optionLength

    def __repr__(self) -> str:
        return "| op: {}, htype: {}, hlen: {}, hops: {}, xid: {}, secs: {}, flags: {},  client: {}, your: {}, server: {}, relay: {}, clientEthernetAddress: {}, magic-cookie: {}, options: {} |".format(
            self.op,
            self.htype,
            self.hlen,
            self.hops,
            self.xid,
            self.secs,
            self.flags,
            self.clientIPAddress,
            self.yourIPAddress,
            self.serverIPAddress,
            self.relayIPAddress,
            self.clientEthernetAddress,
            self.magicCookie,
            self.options,
        )


def bytes2dhcpOptionValue(key: DHCPOptionKey, value: bytes) -> DHCPOptionValue:
    if key == DHCPOptionKey.MessageType:
        return MessageType.from_value(struct.unpack("B", value)[0])

    if key == DHCPOptionKey.RequestedIPAddress:
        return socket.inet_ntoa(value)

    if key == DHCPOptionKey.End:
        return value.decode()

    if key == DHCPOptionKey.ParamterRequestList:
        arr = [DHCPParameterRequest.from_value(item) for item in list(value)]
        return list(set(sorted(arr)))

    return value
