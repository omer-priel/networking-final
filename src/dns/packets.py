# dns packet

from __future__ import annotations

import struct

# https://www.ietf.org/rfc/rfc1035.txt

# TODO Need to serperate to Query Record and Annser Record

class DNSRecord:
    @staticmethod
    def from_bytes(isQuery: bool, data: bytes, offset: int, queriesOffset: int) -> tuple[DNSRecord, int]:
        domainName = ""
        domainNameOffset = 0

        if not isQuery:
            originOffset = offset + 2
            offset = queriesOffset + int(data[offset + 1])
            domainNameOffset = int(data[offset + 1])

        labelLen = int(data[offset])
        offset += 1
        while labelLen > 0:
            if len(domainName) > 0:
                domainName += "."
            domainName += data[offset: offset + labelLen].decode()
            offset += labelLen
            labelLen = int(data[offset])
            offset += 1

        if not isQuery:
            offset = originOffset

        recordType, recordClass = struct.unpack_from(">HH", data, offset)
        offset += 4

        ttl = 0
        rData = b''

        if not isQuery:
            ttl, rDataLength = struct.unpack_from(">HH", data, offset)
            offset += 4
            rData = data[offset: offset + rDataLength]
            offset += rDataLength

        return (DNSRecord(isQuery, domainName, domainNameOffset, recordType, recordClass, ttl, rData), offset)

    def __init__(self, isQuery: bool, domainName: str, domainNameOffset: int, recordType: int, recordClass: int, ttl: int, rData: bytes) -> None:
        self.isQuery = isQuery

        self.domainName = domainName
        self.domainNameOffset = domainNameOffset
        self.type = recordType
        self.clase = recordClass

        self.ttl = ttl
        self.rData = rData

    def __bytes__(self) -> bytes:
        data = b''

        if self.isQuery:
            for label in self.domainName.split('.'):
                data += struct.pack(">B", len(label))
                data += label.encode()
            data += struct.pack(">B", 0)
        else:
            data += b"\xc0"
            data += bytes([self.domainNameOffset])

        data += struct.pack(">HH", self.type, self.clase)

        if not self.isQuery:
            data += struct.pack(">HH", self.ttl, len(self.rData))
            data += self.rData

        return data

    def __str__(self) -> str:
        return (
            " isQuery: {}, name: {}, type: {}, class: {}, ttl: {}, data length: {} |"
        ).format(
            self.isQuery,
            self.domainName,
            self.type,
            self.clase,
            self.ttl,
            len(self.rData)
        )


class DNSFlags:
    @staticmethod
    def from_bytes(data: int) -> DNSFlags:
        b1 = int(data[0])
        b2 = int(data[1])

        rcode = b2 % 16

        checkdisable = b2 & 2**4 > 0
        authenticated = b2 & 2**5 > 0
        z = b2 & 2**6 > 0
        recavail = b2 & 2**7 > 0

        recdesired = b1 & 2**0 > 0
        truncated = b1 & 2**1 > 0
        authoritative = b1 & 2**2 > 0
        b1 = int(b1 / 8)

        opcode = b1 % 16
        b1 = int(b1 / 16)

        isResponse = b1 & 2**0 > 0

        return DNSFlags(isResponse, opcode, authoritative, truncated, recdesired, recavail, z, authenticated, checkdisable, rcode)

    def __init__(self, isResponse: bool, opcode: int, authoritative: bool, truncated: bool, recdesired: bool, recavail: bool, z: bool, authenticated: bool, checkdisable: bool, rcode: int):
        self.isResponse = isResponse
        self.opcode = opcode
        self.authoritative = authoritative
        self.truncated = truncated
        self.recdesired = recdesired
        self.recavail = recavail
        self.z = z
        self.authenticated = authenticated
        self.checkdisable = checkdisable
        self.rcode = rcode

    def __bytes__(self) -> bytes:
        b2 = self.rcode + self.checkdisable * 2 ** 4
        b2 += self.authenticated * 2 ** 5 + self.z * 2 ** 6 + self.recavail * 2 ** 7

        b1 = self.recdesired * 2 ** 0 + self.truncated * 2 ** 1 + self.authoritative * 2 ** 2
        b1 += self.opcode * 2 ** 3 + self.isResponse * 2 ** 7

        return bytes([b1, b2])

    def __str__(self) -> str:
        if not self.isResponse:
            return (
                    "query (opcode: {}, truncated: {}, recdesired: {}, z: {}, check disable: {})"
                ).format(self.opcode, self.truncated, self.recdesired, self.z, self.checkdisable)

        return (
                "response (opcode: {}, authoritative: {}, truncated: {}, recdesired: {}, recavail: {}, z: {}, authenticated: {}, check disable: {}, rcode: {})"
            ).format(self.opcode, self.authoritative, self.truncated, self.recdesired, self.recavail, self.z, self.authenticated, self.checkdisable, self.rcode)


class DNSPacket:
    @staticmethod
    def from_bytes(data: bytes) -> DNSPacket:
        offset = 0

        transactionID = data[offset:offset + 2]
        offset += 2

        flags = data[offset:offset + 2]
        offset += 2

        queriesCount, answersCount, authorityCount, additionalCount = struct.unpack_from(">HHHH", data, offset)
        offset += 4 * 2

        packet = DNSPacket(transactionID, DNSFlags.from_bytes(flags), queriesCount, answersCount, authorityCount, additionalCount)

        queriesOffset = offset
        while queriesCount > 0:
            record, offset = DNSRecord.from_bytes(True, data, offset, queriesOffset)
            packet.queriesRecords += [record]
            queriesCount -= 1

        while answersCount > 0:
            record, offset = DNSRecord.from_bytes(False, data, offset, queriesOffset)
            packet.answersRecords += [record]
            answersCount -= 1

        while authorityCount > 0:
            record, offset = DNSRecord.from_bytes(False, data, offset, queriesOffset)
            packet.authorityCount += [record]
            authorityCount -= 1

        while additionalCount > 0:
            record, offset = DNSRecord.from_bytes(False, data, offset, queriesOffset)
            packet.additionalRecords += [record]
            additionalCount -= 1

        return packet

    def __init__(self, transactionID: bytes, flags: DNSFlags, queriesCount: int, answersCount: int, authorityCount: int, additionalCount: int) -> None:
        self.transactionID = transactionID
        self.flags = flags

        self.queriesCount = queriesCount
        self.answersCount = answersCount
        self.authorityCount = authorityCount
        self.additionalCount = additionalCount

        self.queriesRecords: list[DNSRecord] = []
        self.answersRecords: list[DNSRecord] = []
        self.authorityRecords: list[DNSRecord] = []
        self.additionalRecords: list[DNSRecord] = []

    def __bytes__(self) -> bytes:
        data = self.transactionID
        data += bytes(self.flags)

        data += struct.pack(">HHHH", self.queriesCount, self.answersCount, self.authorityCount, self.additionalCount)

        for record in self.queriesRecords + self.answersRecords + self.authorityRecords + self.additionalRecords:
            data += bytes(record)

        return data

    def __repr__(self) -> str:
        ret = (
            "| id: {}, flags: {}, queries count: {}, answers count: {}, authority count: {}, additional count: {} |"
        ).format(
            self.transactionID,
            str(self.flags),
            self.queriesCount,
            self.answersCount,
            self.authorityCount,
            self.additionalCount
        )

        for record in self.queriesRecords + self.answersRecords + self.authorityRecords + self.additionalRecords:
            ret += str(record)

        return ret


def ip_to_str(data: bytes) -> str:
    return "{}.{}.{}.{}".format(data[0], data[1], data[2], data[3])


def str_to_ip(address: str) -> bytes:
    return bytes([int(num) for num in "255.255.0.255".split(".")])
