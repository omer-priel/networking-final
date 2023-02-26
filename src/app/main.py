# entry point to Application

import logging
import os
import os.path
import socket
from concurrent.futures import ThreadPoolExecutor
import threading
from typing import Any
from abc import ABC, abstractclassmethod
import json
import uuid
from pydantic import BaseModel

from src.app.config import config, init_config, init_logging
from src.lib.ftp import *


class UserData(BaseModel):
    id: str
    password: str


class StorageData(BaseModel):
    users: dict[str, UserData] = {}


# globals
appSocket: socket.socket
executor = ThreadPoolExecutor(2)


def init_app() -> None:
    init_config()
    init_logging()
    init_strorage()

    logging.info("The app is initialized")


def init_strorage() -> None:
    if not os.path.isdir(config.APP_STORAGE_PATH):
        os.mkdir(config.APP_STORAGE_PATH)

    if not os.path.isdir(config.APP_STORAGE_PATH + config.STORAGE_PUBLIC):
        os.mkdir(config.APP_STORAGE_PATH + config.STORAGE_PUBLIC)

    if not os.path.isdir(config.APP_STORAGE_PATH + config.STORAGE_PRIVATE):
        os.mkdir(config.APP_STORAGE_PATH + config.STORAGE_PRIVATE)

    if not os.path.isfile(config.APP_STORAGE_PATH + config.STORAGE_DATA):
        storageData = StorageData()
        with open(config.APP_STORAGE_PATH + config.STORAGE_DATA, "a") as f:
            f.write(storageData.json())


def get_path(path: str, storagePath: str) -> str:
    return storagePath + path


def in_storage(path: str, storagePath: str) -> bool:
    return os.path.commonpath([os.path.abspath(get_path(path, storagePath)), os.path.abspath(storagePath)]) == os.path.abspath(storagePath)


# RUDP
lastRequestID = 0


def create_new_requestID() -> int:
    global lastRequestID
    lastRequestID += 1

    return lastRequestID


def create_socket() -> None:
    global appSocket

    appSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    appSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    appSocket.bind((config.APP_HOST, config.APP_PORT))
    appSocket.setblocking(1)
    appSocket.settimeout(config.SOCKET_TIMEOUT)

    logging.info("The app socket initialized on " + config.APP_HOST + ":" + str(config.APP_PORT))


def send_close(clientAddress: Any) -> None:
    closePocket = Pocket(BasicLayer(0, PocketType.Close))
    appSocket.sendto(closePocket.to_bytes(), clientAddress)


def send_error(errorMessage: str, clientAddress: Any) -> None:
        logging.error(errorMessage)
        resPocket = Pocket(BasicLayer(0, PocketType.Response))
        resPocket.responseLayer = ResponseLayer(False, errorMessage, 0, 0, 0)
        appSocket.sendto(resPocket.to_bytes(), clientAddress)


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


class UploadFileRequestHandler(UploadRequestHandler):
    def route(self) -> tuple[Pocket, bytes | None] | None:
        # validation
        if not self.request.uploadRequestLayer:
            self.send_error("This is not upload request")
            return None

        if len(self.request.uploadRequestLayer.path) > config.FILE_PATH_MAX_LENGTH:
            self.send_error("The file path cannot be more then {} chars".format(config.FILE_PATH_MAX_LENGTH))
            return None

        if self.request.requestLayer.pocketFullSize <= 0:
            self.send_error("The file cannot be empty")
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

            data += pack_directory_block(directoryName, updatedAt)

        for fileName in files:
            updatedAt = os.path.getmtime(directoryPath + "/" + fileName)
            fileSize = os.stat(directoryPath + "/" + fileName).st_size

            data += pack_file_block(fileName, updatedAt, fileSize)

        self.requestID = create_new_requestID()
        res = Pocket(BasicLayer(self.requestID, PocketType.Response, PocketSubType.List))
        res.listResponseLayer = ListResponseLayer(len(directories), len(files))
        return (res, data)


# dict of handlers for the requests
handlers: dict[int, RequestHandler] = {}
handlersLock = threading.Lock()

def main_loop() -> None:
    global handlers, handlersLock

    # dict of responses for unready requests
    notReady: dict[int, Pocket] = {}
    while True:
        try:
            data, clientAddress = appSocket.recvfrom(config.SOCKET_MAXSIZE)
        except socket.error:
            data = None

        if data:
            pocket = Pocket.from_bytes(data)

        for key in notReady:
            if data and not key == pocket.basicLayer.requestID:
                appSocket.sendto(notReady[key], handlers[key].get_requestID())

        if data:
            if pocket.basicLayer.pocketType == PocketType.Request:
                result = create_handler(pocket, clientAddress)
                if result:
                    handler, res = result
                    if not handler.uploadHandler:
                        notReady[handler.get_requestID()] = res

                    handlersLock.acquire()
                    handlers[handler.get_requestID()] = handler
                    handlersLock.release()
            elif pocket.basicLayer.requestID in handlers:
                handler = handlers[pocket.basicLayer.requestID]
                if handler.uploadHandler:
                    if not handle_upload_pocket(handler, pocket):
                        handlersLock.acquire()
                        handlers.pop(handler.get_requestID())
                        handlersLock.release()
                else:
                    if not handler.ready:
                        handler.ready = True
                        notReady.pop(handler.get_requestID())

                        def downloading_task(handler: DownloadRequestHandler):
                            global handlers, handlersLock

                            handler.locker.acquire()
                            windowTimeout = handler.response.responseLayer.windowTimeout
                            singleSegmentSize = handler.response.responseLayer.singleSegmentSize
                            segmentsAmount = handler.response.responseLayer.segmentsAmount
                            dataSize = len(handler.data)
                            handler.locker.release()

                            last = time.time()
                            downloading = True

                            while downloading:
                                now = time.time()
                                if last + windowTimeout > now:
                                    # send a segment
                                    if len(handler.windowToSend) == 0:
                                        time.sleep(last + windowTimeout - now)
                                    else:
                                        segmentID = handler.windowToSend.pop(0)
                                        if segmentID * singleSegmentSize <= dataSize - singleSegmentSize:
                                            # is not the last segment
                                            segment = handler.data[segmentID * singleSegmentSize: (segmentID + 1) * singleSegmentSize]
                                        else:
                                            # is the last segment
                                            segment = handler.data[segmentID * singleSegmentSize:]

                                        segmentPocket = Pocket(BasicLayer(handler.get_requestID(), PocketType.Segment))
                                        segmentPocket.segmentLayer = SegmentLayer(segmentID, segment)

                                        handler.windowSending.append(segmentID)
                                        appSocket.sendto(segmentPocket.to_bytes(), clientAddress)
                                else:
                                    # refresh window
                                    logging.debug(
                                        "refresh window {}/{}".format(segmentsAmount - len(handler.windowToSend) - len(handler.windowSending), segmentsAmount)
                                    )
                                    handler.locker.acquire()
                                    while len(handler.pockets) > 0:
                                        pocket = handler.pockets.pop(0)
                                        if pocket.basicLayer.pocketType == PocketType.DownloadComplited:
                                            # complit the downloading
                                            handler.pockets = []
                                            downloading = False
                                        elif pocket.akcLayer:
                                            if pocket.akcLayer.segmentID in handler.windowToSend:
                                                handler.windowToSend.remove(pocket.akcLayer.segmentID)
                                            if pocket.akcLayer.segmentID in handler.windowSending:
                                                handler.windowSending.remove(pocket.akcLayer.segmentID)
                                            else:
                                                logging.error("Get pocket that not ACK and not download complited")

                                    handler.locker.release()

                                    handler.windowToSend = handler.windowSending + handler.windowToSend
                                    handler.windowSending = []
                                    last = time.time()

                            send_close(handler.get_client_address())

                            handlersLock.acquire()
                            handlers.pop(handler.get_requestID())
                            handlersLock.release()

                        executor.submit(downloading_task, handler)
                    else:
                        handler.locker.acquire()
                        handler.pockets += [pocket]
                        handler.locker.release()

            else:
                send_close(clientAddress)

# controllers
def create_handler(request: Pocket, clientAddress: tuple[str, int]) -> tuple[RequestHandler, Pocket] | None:
    storagePath = config.APP_STORAGE_PATH + config.STORAGE_PUBLIC + "/"

    if not request.requestLayer.anonymous:
        # valid user
        if request.requestLayer.userName == "":
            send_error("The user name cannot be empty", clientAddress)
            return None

        with open(config.APP_STORAGE_PATH + config.STORAGE_DATA, "r") as f:
            storageData = StorageData(**json.load(f))

        # check if the user not exists
        userData = storageData.users.get(request.requestLayer.userName)

        if userData:
            if not userData.password == request.requestLayer.password:
                send_error("the password is incorrect", clientAddress)
                return None

            userData = UserData(id=str(uuid.uuid4()), password=request.requestLayer.password)
            while os.path.isdir(config.APP_STORAGE_PATH + config.STORAGE_PRIVATE + "/" + userData.id):
                userData.id = str(uuid.uuid4())

            os.mkdir(config.APP_STORAGE_PATH + config.STORAGE_PRIVATE + "/" + userData.id)
            storageData.users[request.requestLayer.userName] = userData

            with open(config.APP_STORAGE_PATH + config.STORAGE_DATA, "w") as f:
                f.write(storageData.json())

        storagePath = config.APP_STORAGE_PATH + config.STORAGE_PRIVATE + "/" + userData.id  + "/"

    handler: RequestHandler

    if request.basicLayer.pocketSubType == PocketSubType.Upload:
        handler = UploadFileRequestHandler(request, clientAddress, storagePath)
    elif request.basicLayer.pocketSubType == PocketSubType.Download:
        handler = DownloadFileRequestHandler(request, clientAddress, storagePath)
    elif request.basicLayer.pocketSubType == PocketSubType.List:
        handler = ListRequestHandler(request, clientAddress, storagePath)

    result = handler.route()
    if not result:
        return None

    res, data = result

    if handler.uploadHandler:
        dataSize = request.requestLayer.pocketFullSize
    else:
        dataSize = len(data)

    if dataSize == 0:
        res.responseLayer = ResponseLayer(True, "", 0, 0, 0)
        appSocket.sendto(res.to_bytes(), clientAddress)
        return None

    singleSegmentSize = max(config.SINGLE_SEGMENT_SIZE_MIN, request.requestLayer.maxSingleSegmentSize)
    singleSegmentSize = min(config.SINGLE_SEGMENT_SIZE_MAX, singleSegmentSize)

    segmentsAmount = int(dataSize / singleSegmentSize)
    if segmentsAmount * singleSegmentSize < dataSize:
        segmentsAmount += 1

    windowTimeout = max(config.WINDOW_TIMEOUT_MIN, request.requestLayer.maxWindowTimeout)
    windowTimeout = min(config.WINDOW_TIMEOUT_MAX, windowTimeout)

    res.responseLayer = ResponseLayer(True, "", segmentsAmount, singleSegmentSize, windowTimeout)

    if handler.uploadHandler:
        handler.segmentsAmount = segmentsAmount
    else:
        handler.data = data
        handler.windowToSend = list(range(segmentsAmount))
        handler.windowSending = []
        handler.response = res

    appSocket.sendto(res.to_bytes(), clientAddress)
    return (handler, res)


def handle_upload_pocket(handler: UploadRequestHandler, pocket: Pocket) -> bool:
    if (not pocket.segmentLayer) or (not pocket.basicLayer.pocketType == PocketType.Segment):
        logging.error("Get pocket that is not upload segment")
    else:
        segmentID = pocket.segmentLayer.segmentID
        if segmentID not in handler.segments:
            # add new segment
            handler.segments[segmentID] = pocket.segmentLayer.data

        akcPocket = Pocket(BasicLayer(handler.get_requestID(), PocketType.ACK))
        akcPocket.akcLayer = AKCLayer(segmentID)
        appSocket.sendto(akcPocket.to_bytes(), handler.get_client_address())

        if len(handler.segments) == handler.segmentsAmount:
            # upload all
            data = b""
            for key in sorted(handler.segments):
                data += handler.segments[key]

            send_close(handler.get_client_address())

            handler.post_upload(data)
            return False

    return True


# entry point
def main() -> None:
    init_app()
    create_socket()
    main_loop()


if __name__ == "__main__":
    main()
