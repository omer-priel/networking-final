# ftp classes and functions

from __future__ import annotations

from enum import IntEnum
import struct

# struct link: https://docs.python.org/3.7/library/struct.html

# Config
BYTES_ORDER = 'little'

# Types
class PocketType(IntEnum):
    Unknown = 0
    Auth = 1
    AuthResponse = 2
    Segment = 3
    ACK = 4
    CloseResponse = 5

class PocketSubType(IntEnum):
    Unknown = 0
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

    @staticmethod
    def length() -> int:
        return struct.calcsize(BasicLayer.FORMAT)

    @staticmethod
    def from_bytes(data: bytes, offset: int) -> BasicLayer:
        pocketType, pocketSubType, pocketID = struct.unpack_from(BasicLayer.FORMAT, data, offset)
        return BasicLayer(pocketID, PocketType(int.from_bytes(pocketType, BYTES_ORDER)), PocketSubType(int.from_bytes(pocketSubType, BYTES_ORDER)))

    def __init__(self, pocketID: int, pocketType = PocketType.Unknown, pocketSubType = PocketType.Unknown) -> None:
        self.pocketType = pocketType
        self.pocketSubType = pocketSubType
        self.pocketID = pocketID

    def to_bytes(self) -> bytes:
       return struct.pack(BasicLayer.FORMAT, int(self.pocketType).to_bytes(1, BYTES_ORDER), int(self.pocketSubType).to_bytes(1, BYTES_ORDER), self.pocketID)

    def __str__(self) -> str:
        return "| type: {}, sub-type: {}, id: {} |".format(self.pocketType, self.pocketSubType, self.pocketID)


class AuthLayer:
    FORMAT = 'LLL'

    @staticmethod
    def length() -> int:
        return struct.calcsize(AuthLayer.FORMAT)

    @staticmethod
    def from_bytes(data: bytes, offset: int) -> AuthLayer:
        pocketFullSize, maxSingleSegmentSize, maxWindowTimeout = struct.unpack_from(AuthLayer.FORMAT, data, offset)
        return AuthLayer(pocketFullSize, maxSingleSegmentSize, maxWindowTimeout)

    def __init__(self, pocketFullSize: int, maxSingleSegmentSize: int, maxWindowTimeout: int) -> None:
        self.pocketFullSize = pocketFullSize
        self.maxSingleSegmentSize = maxSingleSegmentSize
        self.maxWindowTimeout = maxWindowTimeout

    def to_bytes(self) -> bytes:
       return struct.pack(AuthLayer.FORMAT, self.pocketFullSize, self.maxSingleSegmentSize, self.maxWindowTimeout)

    def __str__(self) -> str:
        return " size: {} |".format(self.pocketFullSize)



# FTP (Application) Layer


# global
class Pocket:
    @staticmethod
    def from_bytes(data: bytes) -> Pocket:
        authLayer = None

        offset = 0
        basicLayer = BasicLayer.from_bytes(data, offset)
        offset += BasicLayer.length()

        if basicLayer.pocketType == PocketType.Auth:
            authLayer = AuthLayer.from_bytes(data, offset)

        return Pocket(basicLayer=basicLayer, authLayer=authLayer)


    def __init__(self, basicLayer: BasicLayer, authLayer: AuthLayer | None = None) -> None:
        self.basicLayer = basicLayer
        self.authLayer = authLayer

    def to_bytes(self) -> bytes:
        data = self.basicLayer.to_bytes()

        if self.basicLayer.pocketType == PocketType.Auth:
            data += self.authLayer.to_bytes()

        return data

    def __str__(self):
        ret = str(self.basicLayer)

        if self.basicLayer.pocketType == PocketType.Auth:
            ret += str(self.authLayer)

        return ret

