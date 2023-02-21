# ftp classes and functions

from __future__ import annotations

from enum import IntEnum
import struct
import time

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
    Close = 5

class PocketSubType(IntEnum):
    Unknown = 0
    UploadRequest = 1
    UploadResponse = 2
    UploadSegment = 3
    DownloadRequest = 4
    DownloadResponse = 5
    DownloadReadyForDownloading = 6
    DownloadSegment = 7
    DownloadComplited = 8
    ListRequest = 9
    ListResponse = 10

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
        return AuthLayer(pocketFullSize, maxSingleSegmentSize, float(maxWindowTimeout / 1000))

    def __init__(self, pocketFullSize: int, maxSingleSegmentSize: int, maxWindowTimeout: float) -> None:
        self.pocketFullSize = pocketFullSize
        self.maxSingleSegmentSize = maxSingleSegmentSize
        self.maxWindowTimeout = maxWindowTimeout

    def to_bytes(self) -> bytes:
       return struct.pack(AuthLayer.FORMAT, self.pocketFullSize, self.maxSingleSegmentSize, int(self.maxWindowTimeout * 1000))

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
        return AuthResponseLayer(segmentsAmount, singleSegmentSize, float(windowTimeout / 1000))

    def __init__(self, segmentsAmount: int, singleSegmentSize: int, windowTimeout: float) -> None:
        self.segmentsAmount = segmentsAmount
        self.singleSegmentSize = singleSegmentSize
        self.windowTimeout = windowTimeout

    def to_bytes(self) -> bytes:
       return struct.pack(AuthResponseLayer.FORMAT, self.segmentsAmount, self.singleSegmentSize, int(self.windowTimeout * 1000))

    def __str__(self) -> str:
        return " segments: {}, size: {}, window-timeout: {} |".format(self.segmentsAmount, self.singleSegmentSize, self.windowTimeout)


class SegmentLayer:
    FORMAT = 'LI'

    @staticmethod
    def length() -> int:
        return struct.calcsize(SegmentLayer.FORMAT)

    @staticmethod
    def from_bytes(data: bytes, offset: int) -> SegmentLayer:
        segmentID, segmentLength = struct.unpack_from(SegmentLayer.FORMAT, data, offset)
        segment = data[offset + SegmentLayer.length():offset + SegmentLayer.length() + segmentLength]
        return SegmentLayer(segmentID, segment)

    def __init__(self, segmentID: int, data: bytes) -> None:
        self.segmentID = segmentID
        self.data = data

    def to_bytes(self) -> bytes:
       return struct.pack(SegmentLayer.FORMAT, self.segmentID, len(self.data)) + self.data

    def __str__(self) -> str:
        return " segment: {}, length: {} |".format(self.segmentID, len(self.data))


class AKCLayer:
    FORMAT = 'L'

    @staticmethod
    def length() -> int:
        return struct.calcsize(AKCLayer.FORMAT)

    @staticmethod
    def from_bytes(data: bytes, offset: int) -> AKCLayer:
        segmentID = struct.unpack_from(AKCLayer.FORMAT, data, offset)[0]
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
        filePathLength = struct.unpack_from("I", data, offset)[0]
        offset += struct.calcsize("I")
        filePath = data[offset: offset + filePathLength]
        offset += filePathLength
        fileSize = struct.unpack_from("L", data, offset)[0]

        return UploadRequestLayer(bytes.decode(filePath), fileSize)

    def __init__(self, filePath: str, fileSize: int) -> None:
        self.path = filePath
        self.fileSize = fileSize

    def length(self) -> int:
        return struct.calcsize("I") + len(self.path) + struct.calcsize("L")

    def to_bytes(self) -> bytes:
       return struct.pack("I", len(self.path)) + self.path.encode() + struct.pack("L", self.fileSize)

    def __str__(self) -> str:
        return " file path: {}, size: {} |".format(self.path, self.fileSize)


class UploadResponseLayer:
    @staticmethod
    def from_bytes(data: bytes, offset: int) -> UploadResponseLayer:
        ok, errorMessageLength = struct.unpack_from("?b", data, offset)
        offset = struct.calcsize("?b")
        if errorMessageLength == 0:
            errorMessage = ""
        else:
            errorMessage = bytes.decode(data[offset:offset + errorMessageLength - 1])

        return UploadResponseLayer(ok, errorMessage)

    def __init__(self, ok: bool, errorMessage: str) -> None:
        self.ok = ok
        self.errorMessage = errorMessage

    def length(self) -> int:
        return struct.calcsize("?b") + len(self.errorMessage)

    def to_bytes(self) -> bytes:
       if len(self.errorMessage) == 0:
            return struct.pack("?b", self.ok, 0)

       return struct.pack("?b", self.ok, len(self.errorMessage)) + self.errorMessage.encode()

    def __str__(self) -> str:
        return " ok: {}, message: {} |".format(self.ok, self.errorMessage)


class DownloadRequestLayer:
    @staticmethod
    def from_bytes(data: bytes, offset: int) -> DownloadRequestLayer:
        filePathLength = struct.unpack_from("I", data, offset)[0]
        offset += struct.calcsize("I")
        filePath = data[offset: offset + filePathLength]
        offset += filePathLength

        return DownloadRequestLayer(bytes.decode(filePath))

    def __init__(self, filePath: str) -> None:
        self.path = filePath

    def length(self) -> int:
        return struct.calcsize("I") + len(self.path)

    def to_bytes(self) -> bytes:
       return struct.pack("I", len(self.path)) + self.path.encode()

    def __str__(self) -> str:
        return " file path: {} |".format(self.path)


class DownloadResponseLayer:
    @staticmethod
    def from_bytes(data: bytes, offset: int) -> DownloadResponseLayer:
        ok, errorMessageLength = struct.unpack_from("?b", data, offset)
        offset = struct.calcsize("?b")
        if errorMessageLength == 0:
            errorMessage = ""
        else:
            errorMessage = bytes.decode(data[offset:offset + errorMessageLength - 1])

        offset += errorMessageLength
        fileSize, updatedAt = struct.unpack_from("Ld", data, offset)

        return DownloadResponseLayer(ok, errorMessage, fileSize=fileSize, updatedAt=updatedAt)

    def __init__(self, ok: bool, errorMessage: str, fileSize: int, updatedAt: float) -> None:
        self.ok = ok
        self.errorMessage = errorMessage
        self.fileSize = fileSize
        self.updatedAt = updatedAt

    def length(self) -> int:
        return struct.calcsize("?b") + len(self.errorMessage) + struct.calcsize("Ld")

    def to_bytes(self) -> bytes:
       if len(self.errorMessage) == 0:
            return struct.pack("?b", self.ok, 0) + struct.pack("Ld", self.fileSize, self.updatedAt)

       return struct.pack("?b", self.ok, len(self.errorMessage)) + self.errorMessage.encode() + struct.pack("Ld", self.fileSize, self.updatedAt)

    def __str__(self) -> str:
        return " ok: {}, message: {}, file-size: {}, updated at: {} |".format(self.ok, self.errorMessage, self.fileSize, time.ctime(self.updatedAt))


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
        uploadResponseLayer = None
        downloadRequestLayer = None
        downloadResponseLayer = None

        offset = 0
        basicLayer = BasicLayer.from_bytes(data, offset)
        offset += BasicLayer.length()

        if basicLayer.pocketType == PocketType.Auth:
            authLayer = AuthLayer.from_bytes(data, offset)
            offset += AuthLayer.length()
            if basicLayer.pocketSubType == PocketSubType.UploadRequest:
                uploadRequestLayer = UploadRequestLayer.from_bytes(data, offset)
            elif basicLayer.pocketSubType == PocketSubType.DownloadRequest:
                downloadRequestLayer = DownloadRequestLayer.from_bytes(data, offset)

        elif basicLayer.pocketType == PocketType.AuthResponse:
            authResponseLayer = AuthResponseLayer.from_bytes(data, offset)
            offset += AuthResponseLayer.length()
            if basicLayer.pocketSubType == PocketSubType.UploadResponse:
                uploadResponseLayer = UploadResponseLayer.from_bytes(data, offset)
            elif basicLayer.pocketSubType == PocketSubType.DownloadResponse:
                downloadResponseLayer = DownloadResponseLayer.from_bytes(data, offset)

        elif basicLayer.pocketType == PocketType.Segment:
            segmentLayer = SegmentLayer.from_bytes(data, offset)
        elif basicLayer.pocketType == PocketType.ACK:
            akcLayer = AKCLayer.from_bytes(data, offset)

        return Pocket(basicLayer=basicLayer,
                      authLayer=authLayer, authResponseLayer=authResponseLayer,
                      segmentLayer=segmentLayer, akcLayer=akcLayer,
                      uploadRequestLayer=uploadRequestLayer, uploadResponseLayer=uploadResponseLayer,
                      downloadRequestLayer=downloadRequestLayer, downloadResponseLayer=downloadResponseLayer)


    def __init__(self, basicLayer: BasicLayer,
                 authLayer: AuthLayer | None = None, authResponseLayer: AuthResponseLayer | None = None,
                 segmentLayer: SegmentLayer | None = None, akcLayer: AKCLayer | None = None,
                 uploadRequestLayer: UploadRequestLayer | None = None, uploadResponseLayer: UploadResponseLayer | None = None,
                 downloadRequestLayer: DownloadRequestLayer | None = None, downloadResponseLayer: DownloadResponseLayer | None = None) -> None:
        self.basicLayer = basicLayer
        self.authLayer = authLayer
        self.authResponseLayer = authResponseLayer
        self.segmentLayer = segmentLayer
        self.akcLayer = akcLayer

        self.uploadRequestLayer = uploadRequestLayer
        self.uploadResponseLayer = uploadResponseLayer
        self.downloadRequestLayer = downloadRequestLayer
        self.downloadResponseLayer = downloadResponseLayer

    def get_id(self):
        return self.basicLayer.pocketID

    def to_bytes(self) -> bytes:
        data = self.basicLayer.to_bytes()

        if self.authLayer:
            data += self.authLayer.to_bytes()
            if self.uploadRequestLayer:
                data += self.uploadRequestLayer.to_bytes()
            elif self.downloadRequestLayer:
                data += self.downloadRequestLayer.to_bytes()
        elif self.authResponseLayer:
            data += self.authResponseLayer.to_bytes()
            if self.uploadResponseLayer:
                data += self.uploadResponseLayer.to_bytes()
            elif self.downloadResponseLayer:
                data += self.downloadResponseLayer.to_bytes()
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
            elif self.downloadRequestLayer:
                ret += str(self.downloadRequestLayer)
        elif self.authResponseLayer:
            ret += str(self.authResponseLayer)
            if self.uploadResponseLayer:
                ret += str(self.uploadResponseLayer)
            elif self.downloadResponseLayer:
                ret += str(self.downloadResponseLayer)
        elif self.segmentLayer:
            ret += str(self.segmentLayer)
        elif self.akcLayer:
            ret += str(self.akcLayer)

        return ret
