# dns packet

from __future__ import annotations

import struct

from src.dns.converters import ip_bytes_to_str, pack_int, unpack_host_name, unpack_int_from

# https://www.ietf.org/rfc/rfc1035.txt


class DNSPacketBase:
    def __init__(self) -> None:
        self.domainNames: dict[str, int] = {}


class DNSQueryRecord:
    @staticmethod
    def from_bytes(data: bytes, offset: int, packet: DNSPacketBase) -> tuple[DNSQueryRecord, int]:
        domainNameOffset = offset

        domainName, offset = unpack_host_name(data, offset)

        packet.domainNames[domainName] = domainNameOffset

        recordType, offset = unpack_int_from(data, offset, 2)
        recordClass, offset = unpack_int_from(data, offset, 2)

        return (DNSQueryRecord(domainName, recordType, recordClass), offset)

    def __init__(self, domainName: str, recordType: int, recordClass: int) -> None:
        self.domainName = domainName
        self.type = recordType
        self.clase = recordClass

    def __bytes__(self) -> bytes:
        data = b""

        for label in self.domainName.split("."):
            data += pack_int(len(label), 1)
            data += label.encode()
        data += b"\0"

        data += pack_int(self.type, 2)
        data += pack_int(self.clase, 2)

        return data

    def __str__(self) -> str:
        return (" query, name: {}, type: {}, class: {} |").format(
            self.domainName,
            self.type,
            self.clase,
        )


class DNSAnswerRecord:
    @staticmethod
    def from_bytes(data: bytes, offset: int, packet: DNSPacketBase) -> tuple[DNSAnswerRecord, int]:
        offset += 1

        domainNameOffset = int(data[offset])
        reversedDomainNames = dict(zip(packet.domainNames.values(), packet.domainNames.keys()))
        domainName = reversedDomainNames[domainNameOffset]
        offset += 1

        recordType, offset = unpack_int_from(data, offset, 2)
        recordClass, offset = unpack_int_from(data, offset, 2)

        ttl, offset = unpack_int_from(data, offset, 4)

        rDataLength, offset = unpack_int_from(data, offset, 2)

        nameOffset = offset

        rData = data[offset : offset + rDataLength]
        offset += rDataLength

        if recordType == 5:  # CNAME
            cName = unpack_host_name(rData[:-2], 0)[0]
            packet.domainNames[cName] = nameOffset

        return (DNSAnswerRecord(packet, domainName, recordType, recordClass, ttl, rData), offset)

    def __init__(
        self, packet: DNSPacketBase, domainName: str, recordType: int, recordClass: int, ttl: int, rData: bytes
    ) -> None:
        self.packet = packet

        self.domainName = domainName
        self.type = recordType
        self.clase = recordClass

        self.ttl = ttl
        self.rData = rData

    def to_bytes(self, offset: int) -> bytes:
        data = b""

        data += b"\xc0"
        data += bytes([self.packet.domainNames[self.domainName]])

        data += pack_int(self.type, 2)
        data += pack_int(self.clase, 2)

        data += pack_int(self.ttl, 4)
        data += pack_int(len(self.rData), 2)

        data += self.rData

        if self.type == 5:  # CNAME
            name = unpack_host_name(self.rData, 0)[0]
            self.packet.domainNames[name] = offset + 10

        return data

    def __str__(self) -> str:
        dataAsStr = str(len(self.rData))

        if self.type == 1:  # A
            dataAsStr = ip_bytes_to_str(self.rData)
        elif self.type == 5:  # CNAME
            dataAsStr = unpack_host_name(self.rData, 0)[0]

        return (" answer, name: {}, type: {}, class: {}, ttl: {}, data: {} |").format(
            self.domainName, self.type, self.clase, self.ttl, dataAsStr
        )


class DNSFlags:
    @staticmethod
    def from_bytes(data: bytes) -> DNSFlags:
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

        return DNSFlags(
            isResponse, opcode, authoritative, truncated, recdesired, recavail, z, authenticated, checkdisable, rcode
        )

    def __init__(
        self,
        isResponse: bool,
        opcode: int,
        authoritative: bool,
        truncated: bool,
        recdesired: bool,
        recavail: bool,
        z: bool,
        authenticated: bool,
        checkdisable: bool,
        rcode: int,
    ):
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
        b2 = self.rcode + self.checkdisable * 2**4
        b2 += self.authenticated * 2**5 + self.z * 2**6 + self.recavail * 2**7

        b1 = self.recdesired * 2**0 + self.truncated * 2**1 + self.authoritative * 2**2
        b1 += self.opcode * 2**3 + self.isResponse * 2**7

        return bytes([b1, b2])

    def __str__(self) -> str:
        if not self.isResponse:
            return ("query (opcode: {}, truncated: {}, recdesired: {}, z: {}, check disable: {})").format(
                self.opcode, self.truncated, self.recdesired, self.z, self.checkdisable
            )

        return (
            "response (opcode: {}, authoritative: {}, truncated: {}, recdesired: {}, recavail: {}"
            + ", z: {}, authenticated: {}, check disable: {}, rcode: {})"
        ).format(
            self.opcode,
            self.authoritative,
            self.truncated,
            self.recdesired,
            self.recavail,
            self.z,
            self.authenticated,
            self.checkdisable,
            self.rcode,
        )


class DNSPacket(DNSPacketBase):
    @staticmethod
    def from_bytes(data: bytes) -> DNSPacket:
        offset = 0

        transactionID = data[offset : offset + 2]
        offset += 2

        flags = data[offset : offset + 2]
        offset += 2

        queriesCount, answersCount, authorityCount, additionalCount = struct.unpack_from(">HHHH", data, offset)
        offset += 4 * 2

        packet = DNSPacket(
            transactionID, DNSFlags.from_bytes(flags), queriesCount, answersCount, authorityCount, additionalCount
        )

        record: DNSQueryRecord | DNSAnswerRecord

        while queriesCount > 0:
            record, offset = DNSQueryRecord.from_bytes(data, offset, packet)
            packet.queriesRecords += [record]
            queriesCount -= 1

        while answersCount > 0:
            record, offset = DNSAnswerRecord.from_bytes(data, offset, packet)
            packet.answersRecords += [record]
            answersCount -= 1

        while authorityCount > 0:
            record, offset = DNSAnswerRecord.from_bytes(data, offset, packet)
            packet.authorityRecords += [record]
            authorityCount -= 1

        while additionalCount > 0:
            record, offset = DNSAnswerRecord.from_bytes(data, offset, packet)
            packet.additionalRecords += [record]
            additionalCount -= 1

        return packet

    def __init__(
        self,
        transactionID: bytes,
        flags: DNSFlags,
        queriesCount: int,
        answersCount: int,
        authorityCount: int,
        additionalCount: int,
    ) -> None:
        DNSPacketBase.__init__(self)

        self.transactionID = transactionID
        self.flags = flags

        self.queriesCount = queriesCount
        self.answersCount = answersCount
        self.authorityCount = authorityCount
        self.additionalCount = additionalCount

        self.queriesRecords: list[DNSQueryRecord] = []
        self.answersRecords: list[DNSAnswerRecord] = []
        self.authorityRecords: list[DNSAnswerRecord] = []
        self.additionalRecords: list[DNSAnswerRecord] = []

    def __bytes__(self) -> bytes:
        data = self.transactionID
        data += bytes(self.flags)

        data += struct.pack(">HHHH", self.queriesCount, self.answersCount, self.authorityCount, self.additionalCount)

        record: DNSQueryRecord | DNSAnswerRecord

        for record in self.queriesRecords:
            self.domainNames[record.domainName] = len(data)
            data += bytes(record)

        for record in self.answersRecords + self.authorityRecords + self.additionalRecords:
            data += record.to_bytes(len(data))

        return data

    def __repr__(self) -> str:
        ret = (
            "| id: {}, flags: {}, queries count: {}, answers count: {}, authority count: {}, additional count: {} |"
        ).format(
            unpack_int_from(self.transactionID, 0, 2)[0],
            str(self.flags),
            self.queriesCount,
            self.answersCount,
            self.authorityCount,
            self.additionalCount,
        )

        for record in self.queriesRecords + self.answersRecords + self.authorityRecords + self.additionalRecords:
            ret += str(record)

        return ret
