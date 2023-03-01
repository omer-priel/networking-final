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
    ParamterRequestList = 55
    SubnetMask = 1
    Router = 3
    DomainNameServer = 6
    DHCPServer = 54

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
    NAK = 6
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


DHCPOptionValue = bytes | str | int | MessageType | list[DHCPParameterRequest] | list[str]


class DHCPPacket:
    def from_bytes(data: bytes) -> DHCPPacket:
        offset = 0

        op, htype, hlen, hops = data[offset : offset + 4]
        offset += 4

        xid, secs, flags = struct.unpack_from("IHH", data, offset)
        offset += 8

        clientIPAddress = socket.inet_ntoa(data[offset : offset + 4])
        offset += 4
        yourIPAddress = socket.inet_ntoa(data[offset : offset + 4])
        offset += 4
        serverIPAddress = socket.inet_ntoa(data[offset : offset + 4])
        offset += 4
        gatewayIPAddress = socket.inet_ntoa(data[offset : offset + 4])
        offset += 4

        clientEthernetAddress = data[offset : offset + 16]
        offset += 16

        # 192 octets of 0s, or overflow space for additional options; BOOTP legacy.
        offset += 192

        magicCookie = struct.unpack_from("I", data, offset)[0]
        offset += 4

        options: dict[DHCPOptionKey, DHCPOptionValue] = {}

        while offset + 1 < len(data) and int(data[offset]) != int(DHCPOptionKey.End):
            optionKey = int(data[offset])
            optionLength = int(data[offset + 1])
            offset += 2

            if DHCPOptionKey.has_value(optionKey):
                optionValue = b""
                if optionLength > 0:
                    optionValue = data[offset : offset + optionLength]

                options[optionKey] = bytes2dhcpOptionValue(optionKey, optionValue)

            offset += optionLength

        return DHCPPacket(
            op=op,
            htype=htype,
            hlen=hlen,
            hops=hops,
            xid=xid,
            secs=secs,
            flags=flags,
            clientIPAddress=clientIPAddress,
            yourIPAddress=yourIPAddress,
            serverIPAddress=serverIPAddress,
            gatewayIPAddress=gatewayIPAddress,
            clientEthernetAddress=clientEthernetAddress,
            magicCookie=magicCookie,
            options=options,
        )

    def __init__(
        self,
        op: int,
        htype: int,
        hlen: int,
        hops: int,
        xid: int,
        secs: int,
        flags: int,
        clientIPAddress: str,
        yourIPAddress: str,
        serverIPAddress: str,
        gatewayIPAddress: str,
        clientEthernetAddress: bytes,
        magicCookie: int,
        options: dict[DHCPOptionKey, DHCPOptionValue],
    ) -> None:
        self.op = op
        self.htype = htype
        self.hlen = hlen
        self.hops = hops

        self.xid = xid
        self.secs = secs
        self.flags = flags

        self.clientIPAddress = clientIPAddress
        self.yourIPAddress = yourIPAddress
        self.serverIPAddress = serverIPAddress
        self.gatewayIPAddress = gatewayIPAddress

        self.clientEthernetAddress = clientEthernetAddress
        self.magicCookie = magicCookie

        self.options = options

    def __bytes__(self) -> bytes:
        data = bytes([self.op, self.htype, self.hlen, self.hops])
        data += struct.pack("IHH", self.xid, self.secs, self.flags)

        data += socket.inet_aton(self.clientIPAddress)
        data += socket.inet_aton(self.yourIPAddress)
        data += socket.inet_aton(self.serverIPAddress)
        data += socket.inet_aton(self.gatewayIPAddress)

        data += self.clientEthernetAddress

        # 192 octets of 0s, or overflow space for additional options; BOOTP legacy.
        data += b"\0" * 192

        data += struct.pack("I", self.magicCookie)

        for key in self.options:
            if not key == DHCPOptionKey.End and not key == DHCPOptionKey.Padding:
                optionAsData = dhcpOptionValue2bytes(key, self.options[key])
                data += struct.pack("BB", int(key), len(optionAsData))
                data += optionAsData

        data += struct.pack("BB", int(DHCPOptionKey.End), 0)

        return data

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
            self.gatewayIPAddress,
            self.clientEthernetAddress,
            self.magicCookie,
            self.options,
        )


def bytes2dhcpOptionValue(key: DHCPOptionKey, data: bytes) -> DHCPOptionValue:
    if key == DHCPOptionKey.MessageType:
        return MessageType.from_value(struct.unpack("B", data)[0])

    if key in [
        DHCPOptionKey.RequestedIPAddress,
        DHCPOptionKey.SubnetMask,
        DHCPOptionKey.Router,
        DHCPOptionKey.DHCPServer,
        DHCPOptionKey.DomainNameServer,
    ]:
        return socket.inet_ntoa(data)

    if key == DHCPOptionKey.ParamterRequestList:
        arr = [DHCPParameterRequest.from_value(item) for item in list(data)]
        return list(set(sorted(arr)))

    return data


def dhcpOptionValue2bytes(key: DHCPOptionKey, value: DHCPOptionValue) -> bytes:
    if key == DHCPOptionKey.MessageType:
        return struct.pack("B", int(value))

    if key in [
        DHCPOptionKey.RequestedIPAddress,
        DHCPOptionKey.SubnetMask,
        DHCPOptionKey.Router,
        DHCPOptionKey.DHCPServer,
        DHCPOptionKey.DomainNameServer,
    ]:
        return socket.inet_aton(value)

    if key == DHCPOptionKey.ParamterRequestList:
        arr = [int(item) for item in value if int(item) != 0]
        return bytes(arr)

    return value
