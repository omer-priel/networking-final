# ftp classes and functions

from __future__ import annotations

import struct
from abc import ABC, abstractclassmethod
from enum import IntEnum

# struct link: https://docs.python.org/3.7/library/struct.html


# Types
class PocketType(IntEnum):
    Unknown = 0
    Request = 1
    Response = 2
    ReadyForDownloading = 3
    Segment = 4
    ACK = 5
    DownloadComplited = 6
    Close = 7


class PocketSubType(IntEnum):
    Unknown = 0
    Upload = 1
    Download = 2
    List = 3


# Layer Interface
class LayerInterface(ABC):
    @abstractclassmethod
    def length(self) -> int:
        pass

    @abstractclassmethod
    def to_bytes(self) -> bytes:
        pass


# RUDP Level
class BasicLayer(LayerInterface):
    @staticmethod
    def from_bytes(data: bytes, offset: int) -> BasicLayer:
        pocketType, pocketSubType, requestID = struct.unpack_from("bbL", data, offset)
        return BasicLayer(
            requestID,
            PocketType(pocketType),
            PocketSubType(pocketSubType),
        )

    def __init__(self, requestID: int, pocketType=PocketType.Unknown, pocketSubType=PocketType.Unknown) -> None:
        self.pocketType = pocketType
        self.pocketSubType = pocketSubType
        self.requestID = requestID

    def length(self) -> int:
        return struct.calcsize("bbL")

    def to_bytes(self) -> bytes:
        return struct.pack(
            "bbL",
            self.pocketType,
            self.pocketSubType,
            self.requestID,
        )

    def __str__(self) -> str:
        return "| type: {}, sub-type: {}, id: {} |".format(self.pocketType, self.pocketSubType, self.requestID)


class RequestLayer(LayerInterface):
    @staticmethod
    def from_bytes(data: bytes, offset: int) -> RequestLayer:
        pocketFullSize, maxSingleSegmentSize, maxWindowTimeout, anonymous, userNameLength = struct.unpack_from(
            "LLL?I", data, offset
        )
        offset += struct.calcsize("LLL?I")
        userName = ""
        password = ""
        if not anonymous:
            if userNameLength > 0:
                userName = data[offset : offset + userNameLength].decode()
                offset += userNameLength

            passwordLength = struct.unpack_from("I", data, offset)[0]
            offset += struct.calcsize("I")
            if passwordLength > 0:
                password = data[offset : offset + passwordLength].decode()
                offset += passwordLength

        return RequestLayer(
            pocketFullSize, maxSingleSegmentSize, float(maxWindowTimeout / 1000), anonymous, userName, password
        )

    def __init__(
        self,
        pocketFullSize: int,
        maxSingleSegmentSize: int,
        maxWindowTimeout: float,
        anonymous: bool,
        userName: str,
        password: str,
    ) -> None:
        self.pocketFullSize = pocketFullSize
        self.maxSingleSegmentSize = maxSingleSegmentSize
        self.maxWindowTimeout = maxWindowTimeout
        self.anonymous = anonymous
        self.userName = userName
        self.password = password

    def length(self) -> int:
        return struct.calcsize("LLL?I") + len(self.userName) + struct.calcsize("I") + len(self.password)

    def to_bytes(self) -> bytes:
        ret = struct.pack(
            "LLL?I",
            self.pocketFullSize,
            self.maxSingleSegmentSize,
            int(self.maxWindowTimeout * 1000),
            self.anonymous,
            len(self.userName),
        )
        ret += self.userName.encode()
        ret += struct.pack("I", len(self.password))
        ret += self.password.encode()
        return ret

    def __str__(self) -> str:
        if self.anonymous:
            return " size: {}, anonymous |".format(self.pocketFullSize)
        return " size: {}, user-name: {} |".format(self.pocketFullSize, self.userName)


class ResponseLayer(LayerInterface):
    @staticmethod
    def from_bytes(data: bytes, offset: int) -> ResponseLayer:
        ok, errorMessageLength = struct.unpack_from("?b", data, offset)
        offset += struct.calcsize("?b")
        if errorMessageLength == 0:
            errorMessage = ""
        else:
            errorMessage = data[offset : offset + errorMessageLength].decode()
            offset += errorMessageLength
        dataSize, segmentsAmount, singleSegmentSize, windowTimeout = struct.unpack_from("LLLL", data, offset)
        return ResponseLayer(ok, errorMessage, dataSize, segmentsAmount, singleSegmentSize, float(windowTimeout / 1000))

    def __init__(
        self, ok: bool, errorMessage: str | None, dataSize: int, segmentsAmount: int, singleSegmentSize: int, windowTimeout: float
    ) -> None:
        self.ok = ok
        if not errorMessage:
            self.errorMessage = ""
        else:
            self.errorMessage = errorMessage
        self.dataSize = dataSize
        self.segmentsAmount = segmentsAmount
        self.singleSegmentSize = singleSegmentSize
        self.windowTimeout = windowTimeout

    def length(self) -> int:
        return struct.calcsize("?b") + len(self.errorMessage) + struct.calcsize("LLLL")

    def to_bytes(self) -> bytes:
        ret = struct.pack("?b", self.ok, len(self.errorMessage))
        ret += self.errorMessage.encode()
        ret += struct.pack("LLLL", self.dataSize, self.segmentsAmount, self.singleSegmentSize, int(self.windowTimeout * 1000))
        return ret

    def __str__(self) -> str:
        return " ok: {}, message: {}, size: {}, segments: {}, size: {}, window-timeout: {} |".format(
            self.ok, self.errorMessage, self.dataSize, self.segmentsAmount, self.singleSegmentSize, self.windowTimeout
        )


class SegmentLayer(LayerInterface):
    @staticmethod
    def from_bytes(data: bytes, offset: int) -> SegmentLayer:
        segmentID, segmentLength = struct.unpack_from("LI", data, offset)
        offset += struct.calcsize("LI")
        segment = data[offset : offset + segmentLength]
        return SegmentLayer(segmentID, segment)

    def __init__(self, segmentID: int, data: bytes) -> None:
        self.segmentID = segmentID
        self.data = data

    def length(self) -> int:
        return struct.calcsize("LI") + len(self.data)

    def to_bytes(self) -> bytes:
        return struct.pack("LI", self.segmentID, len(self.data)) + self.data

    def __str__(self) -> str:
        return " segment: {}, length: {} |".format(self.segmentID, len(self.data))


class AKCLayer(LayerInterface):
    @staticmethod
    def from_bytes(data: bytes, offset: int) -> AKCLayer:
        segmentID = struct.unpack_from("L", data, offset)[0]
        return AKCLayer(segmentID)

    def __init__(self, segmentID: int) -> None:
        self.segmentID = segmentID

    def length(self) -> int:
        return struct.calcsize("L")

    def to_bytes(self) -> bytes:
        return struct.pack("L", self.segmentID)

    def __str__(self) -> str:
        return " akc-to-segment: {} |".format(self.segmentID)


# FTP Level
class UploadRequestLayer(LayerInterface):
    @staticmethod
    def from_bytes(data: bytes, offset: int) -> UploadRequestLayer:
        filePathLength = struct.unpack_from("I", data, offset)[0]
        offset += struct.calcsize("I")
        filePath = data[offset : offset + filePathLength]

        return UploadRequestLayer(bytes.decode(filePath))

    def __init__(self, filePath: str) -> None:
        self.path = filePath

    def length(self) -> int:
        return struct.calcsize("I") + len(self.path)

    def to_bytes(self) -> bytes:
        return struct.pack("I", len(self.path)) + self.path.encode()

    def __str__(self) -> str:
        return " file path: {} |".format(self.path)


class DownloadRequestLayer(LayerInterface):
    @staticmethod
    def from_bytes(data: bytes, offset: int) -> DownloadRequestLayer:
        filePathLength = struct.unpack_from("I", data, offset)[0]
        offset += struct.calcsize("I")
        filePath = data[offset : offset + filePathLength]
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


class ListRequestLayer(LayerInterface):
    @staticmethod
    def from_bytes(data: bytes, offset: int) -> ListRequestLayer:
        directoryPathLength = struct.unpack_from("I", data, offset)[0]
        offset += struct.calcsize("I")
        directoryPath = data[offset : offset + directoryPathLength]
        offset += directoryPathLength

        return ListRequestLayer(bytes.decode(directoryPath))

    def __init__(self, directoryPath: str) -> None:
        self.path = directoryPath

    def length(self) -> int:
        return struct.calcsize("I") + len(self.path)

    def to_bytes(self) -> bytes:
        return struct.pack("I", len(self.path)) + self.path.encode()

    def __str__(self) -> str:
        return " directory path: {} |".format(self.path)


class ListResponseLayer(LayerInterface):
    @staticmethod
    def from_bytes(data: bytes, offset: int) -> ListResponseLayer:
        directoriesCount, filesCount = struct.unpack_from("LL", data, offset)

        return ListResponseLayer(directoriesCount, filesCount)

    def __init__(self, directoriesCount: int, filesCount: int) -> None:
        self.directoriesCount = directoriesCount
        self.filesCount = filesCount

    def length(self) -> int:
        return struct.calcsize("LL")

    def to_bytes(self) -> bytes:
        return struct.pack("LL", self.directoriesCount, self.filesCount)

    def __str__(self) -> str:
        return " directories: {}, files: {} |".format(self.directoriesCount, self.filesCount)


def pack_directory_block(directoryName: str, updatedAt: float) -> bytes:
    return struct.pack("I", len(directoryName)) + directoryName.encode() + struct.pack("d", updatedAt)


def unpack_directory_block(data: bytes, offset: int) -> tuple[tuple[str, float], int]:
    directoryNameLength = struct.unpack_from("I", data, offset)[0]
    offset += struct.calcsize("I")
    if directoryNameLength == 0:
        directoryName = ""
    else:
        directoryName = bytes.decode(data[offset : offset + directoryNameLength])
    offset += directoryNameLength
    updatedAt = struct.unpack_from("d", data, offset)[0]
    offset += struct.calcsize("d")

    return ((directoryName, updatedAt), offset)


def pack_file_block(fileName: str, updatedAt: float, fileSize: int) -> bytes:
    return struct.pack("I", len(fileName)) + fileName.encode() + struct.pack("dL", updatedAt, fileSize)


def unpack_file_block(data: bytes, offset: int) -> tuple[tuple[str, float, int], int]:
    fileNameLength = struct.unpack_from("I", data, offset)[0]
    offset += struct.calcsize("I")
    if fileNameLength == 0:
        fileName = ""
    else:
        fileName = bytes.decode(data[offset : offset + fileNameLength])
    offset += fileNameLength
    updatedAt, fileSize = struct.unpack_from("dL", data, offset)
    offset += struct.calcsize("dL")

    return ((fileName, updatedAt, fileSize), offset)


# A socket pocket
# with parsing and saving all the layers of the app
class Pocket:
    @staticmethod
    def from_bytes(data: bytes) -> Pocket:
        offset = 0
        basicLayer = BasicLayer.from_bytes(data, offset)
        offset += basicLayer.length()

        pocket = Pocket(basicLayer)

        if basicLayer.pocketType == PocketType.Request:
            pocket.requestLayer = RequestLayer.from_bytes(data, offset)
            offset += pocket.requestLayer.length()
            if basicLayer.pocketSubType == PocketSubType.Upload:
                pocket.uploadRequestLayer = UploadRequestLayer.from_bytes(data, offset)
            elif basicLayer.pocketSubType == PocketSubType.Download:
                pocket.downloadRequestLayer = DownloadRequestLayer.from_bytes(data, offset)
            elif basicLayer.pocketSubType == PocketSubType.List:
                pocket.listRequestLayer = ListRequestLayer.from_bytes(data, offset)

        elif basicLayer.pocketType == PocketType.Response:
            pocket.responseLayer = ResponseLayer.from_bytes(data, offset)
            offset += pocket.responseLayer.length()
            if basicLayer.pocketSubType == PocketSubType.List:
                pocket.listResponseLayer = ListResponseLayer.from_bytes(data, offset)

        elif basicLayer.pocketType == PocketType.Segment:
            pocket.segmentLayer = SegmentLayer.from_bytes(data, offset)
        elif basicLayer.pocketType == PocketType.ACK:
            pocket.akcLayer = AKCLayer.from_bytes(data, offset)

        return pocket

    def __init__(self, basicLayer: BasicLayer) -> None:
        self.basicLayer = basicLayer
        self.requestLayer: RequestLayer | None = None
        self.responseLayer: ResponseLayer | None = None
        self.segmentLayer: SegmentLayer | None = None
        self.akcLayer: AKCLayer | None = None

        self.uploadRequestLayer: UploadRequestLayer | None = None
        self.downloadRequestLayer: DownloadRequestLayer | None = None
        self.listRequestLayer: ListRequestLayer | None = None
        self.listResponseLayer: ListResponseLayer | None = None

    def to_bytes(self) -> bytes:
        data = self.basicLayer.to_bytes()

        if self.requestLayer:
            data += self.requestLayer.to_bytes()
            if self.uploadRequestLayer:
                data += self.uploadRequestLayer.to_bytes()
            elif self.downloadRequestLayer:
                data += self.downloadRequestLayer.to_bytes()
            elif self.listRequestLayer:
                data += self.listRequestLayer.to_bytes()
        elif self.responseLayer:
            data += self.responseLayer.to_bytes()
            if self.listResponseLayer:
                data += self.listResponseLayer.to_bytes()
        elif self.segmentLayer:
            data += self.segmentLayer.to_bytes()
        elif self.akcLayer:
            data += self.akcLayer.to_bytes()

        return data

    def __str__(self):
        ret = str(self.basicLayer)

        if self.requestLayer:
            ret += str(self.requestLayer)
            if self.uploadRequestLayer:
                ret += str(self.uploadRequestLayer)
            elif self.downloadRequestLayer:
                ret += str(self.downloadRequestLayer)
            elif self.listRequestLayer:
                ret += str(self.listRequestLayer)
        elif self.responseLayer:
            ret += str(self.responseLayer)
            if self.listResponseLayer:
                ret += str(self.listResponseLayer)
        elif self.segmentLayer:
            ret += str(self.segmentLayer)
        elif self.akcLayer:
            ret += str(self.akcLayer)

        return ret
