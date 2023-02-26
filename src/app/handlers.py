# FTP handlers

import os
import os.path
import threading
from abc import ABC, abstractclassmethod

from src.app.rudp import *
from src.app.storage import get_path, in_storage
from src.lib.ftp import *


# interfaces
class RequestHandler(ABC):
    def __init__(self, uploadHandler: bool, request: Pocket, clientAddress: tuple[str, int], storagePath: str):
        self.uploadHandler = uploadHandler
        self.request = request
        self._clientAddress = clientAddress
        self.requestID = 0
        self._storagePath = storagePath

    @abstractclassmethod
    def route(self) -> tuple[Pocket, bytes | None] | None:
        pass

    def get_client_address(self) -> tuple[str, int]:
        return self._clientAddress

    def get_requestID(self):
        return self.requestID

    def get_path(self, path: str) -> str:
        return get_path(path, self._storagePath)

    def send_error(self, errorMessage: str) -> None:
        send_error(errorMessage, self._clientAddress)


class UploadRequestHandler(RequestHandler):
    def __init__(self, request: Pocket, clientAddress: tuple[str, int], storagePath: str):
        RequestHandler.__init__(self, True, request, clientAddress, storagePath)
        self.segments: dict[int, bytes] = {}
        self.segmentsAmount = 0

    @abstractclassmethod
    def post_upload(self, data: bytes) -> None:
        pass


class DownloadRequestHandler(RequestHandler):
    def __init__(self, request: Pocket, clientAddress: tuple[str, int], storagePath: str):
        RequestHandler.__init__(self, False, request, clientAddress, storagePath)
        self.data = b""
        self.windowToSend = []
        self.windowSending = []
        self.ready = False
        self.response: Pocket = None
        self.pockets: list[Pocket] = []
        self.locker = threading.Lock()


# handlers
class UploadFileRequestHandler(UploadRequestHandler):
    def route(self) -> tuple[Pocket, bytes | None] | None:
        # validation
        if not self.request.uploadRequestLayer:
            self.send_error("This is not upload request")
            return None

        if len(self.request.uploadRequestLayer.path) > config.FILE_PATH_MAX_LENGTH:
            self.send_error("The file path cannot be more then {} chars".format(config.FILE_PATH_MAX_LENGTH))
            return None

        if not in_storage(self.request.uploadRequestLayer.path, self._storagePath):
            self.send_error("The path {} is not legal".format(self.request.uploadRequestLayer.path))
            return None

        self.requestID = create_new_requestID()
        res = Pocket(BasicLayer(self.requestID, PocketType.Response, PocketSubType.Upload))
        return (res, None)

    def post_upload(self, data: bytes) -> None:
        # create the file
        filePath = self.get_path(self.request.uploadRequestLayer.path)
        directoyPath = os.path.dirname(filePath)

        # delete the file if already exists
        if os.path.isfile(filePath):
            os.remove(filePath)

        if not directoyPath:
            directoyPath = "."
        elif not os.path.isdir(directoyPath):
            os.makedirs(directoyPath, exist_ok=True)

        # save the file
        with open(filePath, "w") as f:
            f.write(data.decode())

        logging.info('The file "{}" uploaded'.format(self.request.uploadRequestLayer.path))


class DownloadFileRequestHandler(DownloadRequestHandler):
    def route(self) -> tuple[Pocket, bytes | None] | None:
        # validation
        if not self.request.downloadRequestLayer:
            self.send_error("This is not download request")
            return None

        filePath = self.get_path(self.request.downloadRequestLayer.path)
        if not os.path.isfile(filePath):
            self.send_error('The file "{}" dos not exists!'.format(self.request.downloadRequestLayer.path))
            return None

        if not in_storage(self.request.downloadRequestLayer.path, self._storagePath):
            self.send_error('The file "{}" dos not exists!'.format(self.request.downloadRequestLayer.path))
            return None

        # read the file
        with open(filePath, "r") as f:
            data = f.read().encode()

        self.requestID = create_new_requestID()
        res = Pocket(BasicLayer(self.requestID, PocketType.Response, PocketSubType.Download))
        return (res, data)


class ListRequestHandler(DownloadRequestHandler):
    def route(self) -> tuple[Pocket, bytes | None] | None:
        # validation
        if not self.request.listRequestLayer:
            self.send_error("This is not list request")
            return None

        directoryPath = self.get_path(self.request.listRequestLayer.path)
        if not os.path.isdir(directoryPath):
            self.send_error('The directory "{}" dos not exists!'.format(self.request.listRequestLayer.path))
            return None

        if not in_storage(self.request.listRequestLayer.path, self._storagePath):
            self.send_error('The directory "{}" dos not exists!'.format(self.request.listRequestLayer.path))
            return None

        # load the content
        data = self.load_directory(directoryPath, "", self.request.listRequestLayer.recursive)

        self.requestID = create_new_requestID()
        res = Pocket(BasicLayer(self.requestID, PocketType.Response, PocketSubType.List))
        return (res, data)

    def load_directory(self, directoryPath: str, parent: str, recursive: bool) -> bytes:
        directoriesAndFiles = os.listdir(directoryPath)
        directories = [directory for directory in directoriesAndFiles if os.path.isdir(directoryPath + "/" + directory)]
        files = [file for file in directoriesAndFiles if os.path.isfile(directoryPath + "/" + file)]

        # soring the directories and files
        directories.sort()
        files.sort()

        # convet to bytes
        data = b""
        for directoryName in directories:
            updatedAt = os.path.getmtime(directoryPath + "/" + directoryName)

            data += pack_directory_block(parent + directoryName, updatedAt)
            if recursive:
                data += self.load_directory(directoryPath + "/" + directoryName, parent + directoryName + "/", recursive)

        for fileName in files:
            updatedAt = os.path.getmtime(directoryPath + "/" + fileName)
            fileSize = os.stat(directoryPath + "/" + fileName).st_size

            data += pack_file_block(parent + fileName, updatedAt, fileSize)

        return data

