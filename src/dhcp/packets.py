# packets

import struct


class DiscoveryPacket:
    def __init__(self, data: bytes, offset: int = 0) -> None:
        self.op, self.htype, self.hlen, self.hops = struct.unpack_from("LLLL", data, offset)
        offset += 4*8

        self.xid = data[offset:offset + 4*8]
        offset += 4*8

        self.secs = data[offset:offset + 2*8]
        offset += 2*8
        self.flags = data[offset:offset + 2*8]
        offset += 2*8

        self.clientIPAddress = data[offset:offset + 4*8]
        offset += 4*8

        self.yourIPAddress = data[offset:offset + 4*8]
        offset += 4*8

        self.xid = data[offset:offset + 4*8]
        offset += 4*8

        self.xid = data[offset:offset + 4*8]
        offset += 4*8
        