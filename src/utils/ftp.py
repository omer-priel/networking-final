# ftp classes and functions

from __future__ import annotations

from enum import IntEnum
import struct

# struct link: https://docs.python.org/3.7/library/struct.html

# Config
BYTES_ORDER = 'little'

# Types
class PocketType(IntEnum):
    Auth = 1
    AuthResponse = 2
    Segment = 3
    ACK = 4
    CloseResponse = 5

class PocketSubType(IntEnum):
    UploadFileRequest = 1
    UploadFileResponse = 2
    UploadFileSegment = 3
    ListRequest = 4
    ListResponse = 5
    DownloadFileRequest = 6
    DownloadFileResponse = 7
    DownloadFileSegment = 8

# Network Layer

class BasicLayer:
    FORMAT = 'ccL'

    def bytes_lenght():
        return struct.calcsize(BasicLayer.FORMAT)

    def from_bytes(data: bytes) -> BasicLayer:
        pocketType, pocketSubType, pocketID = struct.unpack(BasicLayer.FORMAT, data)
        return BasicLayer(PocketType(int.from_bytes(pocketType, BYTES_ORDER)), PocketSubType(int.from_bytes(pocketSubType, BYTES_ORDER)), pocketID)

    def __init__(self, pocketType: PocketType, pocketSubType: PocketSubType, pocketID: int) -> None:
        self.pocketType = pocketType
        self.pocketSubType = pocketSubType
        self.pocketID = pocketID

    def to_bytes(self) -> bytes:
        return struct.pack(BasicLayer.FORMAT, int(self.pocketType).to_bytes(1, BYTES_ORDER), int(self.pocketSubType).to_bytes(1, BYTES_ORDER), self.pocketID)

    def __str__(self) -> str:
        return "({}, {}, {})".format(self.pocketType, self.pocketSubType, self.pocketID)

# FTP (Application) Layer
