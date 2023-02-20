# ftp classes and functions

from __future__ import annotations

from enum import IntEnum
import struct

# struct link: https://docs.python.org/3.7/library/struct.html

# Config
BYTES_ORDER = 'little'
FILE_PATH_MAX_SIZE = 256

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
    UploadRequest = 1
    UploadResponse = 2
    UploadSegment = 3
    ListRequest = 4
    ListResponse = 5
    DownloadRequest = 6
    DownloadResponse = 7
    DownloadSegment = 8

# RUDP Level
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


class AuthResponseLayer:
    FORMAT = 'LLL'

    @staticmethod
    def length() -> int:
        return struct.calcsize(AuthResponseLayer.FORMAT)

    @staticmethod
    def from_bytes(data: bytes, offset: int) -> AuthResponseLayer:
        segmentsAmount, singleSegmentSize, windowTimeout = struct.unpack_from(AuthResponseLayer.FORMAT, data, offset)
        return AuthResponseLayer(segmentsAmount, singleSegmentSize, windowTimeout)

    def __init__(self, segmentsAmount: int, singleSegmentSize: int, windowTimeout: int) -> None:
        self.segmentsAmount = segmentsAmount
        self.singleSegmentSize = singleSegmentSize
        self.windowTimeout = windowTimeout

    def to_bytes(self) -> bytes:
       return struct.pack(AuthResponseLayer.FORMAT, self.segmentsAmount, self.singleSegmentSize, self.windowTimeout)

    def __str__(self) -> str:
        return " segments: {}, size: {}, window-timeout: {} |".format(self.segmentsAmount, self.singleSegmentSize, self.windowTimeout)


class SegmentLayer:
    FORMAT = 'L'

    @staticmethod
    def length() -> int:
        return struct.calcsize(SegmentLayer.FORMAT)

    @staticmethod
    def from_bytes(data: bytes, offset: int) -> SegmentLayer:
        segmentID = struct.unpack_from(SegmentLayer.FORMAT, data, offset)
        return SegmentLayer(segmentID)

    def __init__(self, segmentID: int) -> None:
        self.segmentID = segmentID

    def to_bytes(self) -> bytes:
       return struct.pack(SegmentLayer.FORMAT, self.segmentID)

    def __str__(self) -> str:
        return " segment: {} |".format(self.segmentID)


class AKCLayer:
    FORMAT = 'L'

    @staticmethod
    def length() -> int:
        return struct.calcsize(AKCLayer.FORMAT)

    @staticmethod
    def from_bytes(data: bytes, offset: int) -> AKCLayer:
        segmentID = struct.unpack_from(AKCLayer.FORMAT, data, offset)
        return AKCLayer(segmentID)

    def __init__(self, segmentID: int) -> None:
        self.segmentID = segmentID

    def to_bytes(self) -> bytes:
       return struct.pack(AKCLayer.FORMAT, self.segmentID)

    def __str__(self) -> str:
        return " akc-to-segment: {} |".format(self.segmentID)


# FTP Level
class UploadRequestLayer:
    @staticmethod
    def from_bytes(data: bytes, offset: int) -> UploadRequestLayer:
        filePathLength = struct.unpack_from("I", data, offset)
        offset += struct.calcsize("I")

        filePath, fileSize = struct.unpack_from(str(filePathLength) + "cL", data, offset)

        return UploadRequestLayer(bytes.decode(filePath), fileSize)

    def __init__(self, filePath: str, fileSize: int) -> None:
        self.path = filePath
        self.fileSize = fileSize

    def get_format(self) -> str:
        return "I{}cL".format(len(self.path))

    def length(self) -> int:
        return struct.calcsize(self.get_format())

    def to_bytes(self) -> bytes:
       return struct.pack(self.get_format(), len(self.path), self.path.encode(), self.fileSize)

    def __str__(self) -> str:
        return " file path: {}, size: {} |".format(self.path, self.fileSize)


# A socket pocket
# with parsing and saving all the layers of the app
class Pocket:
    @staticmethod
    def from_bytes(data: bytes) -> Pocket:
        authLayer = None
        authResponseLayer = None
        segmentLayer = None
        akcLayer = None

        uploadRequestLayer = None

        offset = 0
        basicLayer = BasicLayer.from_bytes(data, offset)
        offset += BasicLayer.length()

        if basicLayer.pocketType == PocketType.Auth:
            authLayer = AuthLayer.from_bytes(data, offset)
            offset += AuthLayer.length()
            if basicLayer.pocketSubType == PocketSubType.UploadRequest:
                uploadRequestLayer = UploadRequestLayer.from_bytes(data, offset)
        elif basicLayer.pocketType == PocketType.AuthResponse:
            authResponseLayer = AuthResponseLayer.from_bytes(data, offset)
        elif basicLayer.pocketType == PocketType.Segment:
            segmentLayer = SegmentLayer.from_bytes(data, offset)
        elif basicLayer.pocketType == PocketType.ACK:
            akcLayer = AKCLayer.from_bytes(data, offset)

        return Pocket(basicLayer=basicLayer, authLayer=authLayer,
                      authResponseLayer=authResponseLayer, segmentLayer=segmentLayer,
                      akcLayer=akcLayer, uploadRequestLayer=uploadRequestLayer)


    def __init__(self, basicLayer: BasicLayer, authLayer: AuthLayer | None = None,
                 authResponseLayer: AuthResponseLayer | None = None,
                 segmentLayer: SegmentLayer | None = None,
                 akcLayer: AKCLayer | None = None,
                 uploadRequestLayer: UploadRequestLayer | None = None) -> None:
        self.basicLayer = basicLayer
        self.authLayer = authLayer
        self.authResponseLayer = authResponseLayer
        self.segmentLayer = segmentLayer
        self.akcLayer = akcLayer
        self.uploadRequestLayer = uploadRequestLayer

    def to_bytes(self) -> bytes:
        data = self.basicLayer.to_bytes()

        if self.authLayer:
            data += self.authLayer.to_bytes()
            if self.uploadRequestLayer:
                data += self.uploadRequestLayer.to_bytes()

        elif self.authResponseLayer:
            data += self.authResponseLayer.to_bytes()
        elif self.segmentLayer:
            data += self.segmentLayer.to_bytes()
        elif self.akcLayer:
            data += self.akcLayer.to_bytes()

        return data

    def __str__(self):
        ret = str(self.basicLayer)

        if self.authLayer:
            ret += str(self.authLayer)
            if self.uploadRequestLayer:
                ret += str(self.uploadRequestLayer)
        elif self.authResponseLayer:
            ret += str(self.authResponseLayer)
        elif self.segmentLayer:
            ret += str(self.segmentLayer)
        elif self.akcLayer:
            ret += str(self.akcLayer)


        return ret

