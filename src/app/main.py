# entry point to Application

import logging
import os
import os.path
import socket
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
        with open(config.APP_STORAGE_PATH + config.STORAGE_DATA, "a") as outputFile:
            outputFile.write(storageData.json())


def get_path(path: str, storagePath: str) -> str:
    return storagePath + path


def in_storage(path: str, storagePath: str) -> bool:
    return os.path.commonpath([os.path.abspath(get_path(path, storagePath)), os.path.abspath(storagePath)]) == os.path.abspath(storagePath)


# RUDP
currentPocketID = 0
nextPocketID = False


def get_current_pocketID() -> int:
    return currentPocketID


def create_current_pocketID(forNextRequest=False) -> int:
    global currentPocketID, nextPocketID
    if not nextPocketID:
        currentPocketID += 1

    nextPocketID = forNextRequest

    return currentPocketID


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
        resPocket = Pocket(BasicLayer(0, PocketType.AuthResponse))
        resPocket.authResponseLayer = AuthResponseLayer(False, errorMessage, 0, 0, 0)
        appSocket.sendto(resPocket.to_bytes(), clientAddress)


def recv_pocket() -> Pocket:
    try:
        while True:
            data, clientAddress = appSocket.recvfrom(config.SOCKET_MAXSIZE)
            pocket = Pocket.from_bytes(data)
            if pocket.get_id() == get_current_pocketID():
                return pocket
            send_close(pocket.get_id(), clientAddress)
    except socket.error as ex:
        raise ex


class RequestHandler(ABC):
    def __init__(self, request: Pocket, clientAddress: tuple[str, int], requestID: int, storagePath: str):
        self.request = request
        self._clientAddress = clientAddress
        self.requestID = requestID
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
    def __init__(self, request: Pocket, storagePath: str):
        RequestHandler.__init__(self, request, storagePath)
        self.segments: dict[int, str] = {}


    @abstractclassmethod
    def post_upload(self, data: bytes) -> None:
        pass


class DownloadRequestHandler(RequestHandler):
    def __init__(self, request: Pocket, storagePath: str):
        RequestHandler.__init__(self, request, storagePath)
        self.data = b""


class UploadFileRequestHandler(UploadRequestHandler):
    def route(self) -> tuple[Pocket, bytes | None] | None:
        # validation
        if not self.request.uploadRequestLayer:
            self.send_error("This is not upload request")
            return None

        if len(self.request.uploadRequestLayer.path) > config.FILE_PATH_MAX_LENGTH:
            self.send_error("The file path cannot be more then {} chars".format(config.FILE_PATH_MAX_LENGTH))
            return None

        if self.request.authLayer.pocketFullSize <= 0:
            self.send_error("The file cannot be empty")
            return None

        if not in_storage(self.request.uploadRequestLayer.path, self._storagePath):
            self.send_error("The path {} is not legal".format(self.request.uploadRequestLayer.path))
            return None

        self.requestID = create_current_pocketID()
        res = Pocket(BasicLayer(self.requestID, PocketType.AuthResponse, PocketSubType.UploadResponse))
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
            f.write(data)

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
            data = f.read()

        self.requestID = create_current_pocketID()
        res = Pocket(BasicLayer(self.requestID, PocketType.AuthResponse, PocketSubType.DownloadResponse))
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

        self.requestID = create_current_pocketID()
        res = Pocket(BasicLayer(self.requestID, PocketType.AuthResponse, PocketSubType.ListResponse))
        res.listResponseLayer = ListResponseLayer(len(directories), len(files))
        return (res, data)


def main_loop() -> None:
    handlers: dict[int, RequestHandler]  = []
    while True:
        try:
            data, clientAddress = appSocket.recvfrom(config.SOCKET_MAXSIZE)

            pocket = Pocket.from_bytes(data)

            if pocket.authLayer:
                handler = create_handler(pocket, clientAddress)
                if handler:
                    handlers[handler.get_requestID()] = handler
            elif pocket.get_id() in handlers:
                pass
            else:
                send_close(pocket.get_id(), clientAddress)
        except socket.error:
            pass


# controllers
def create_handler(reqPocket: Pocket, clientAddress: tuple[str, int]) -> RequestHandler | None:
    storagePath = config.APP_STORAGE_PATH + config.STORAGE_PUBLIC + "/"

    if not reqPocket.authLayer.anonymous:
        # valid user
        errorMessage: str | None = None
        if reqPocket.authLayer.userName == "":
            errorMessage = "The user name cannot be empty"
        else:
            with open(config.APP_STORAGE_PATH + config.STORAGE_DATA, "r") as dataFile:
                storageData = StorageData(**json.load(dataFile))

        if not errorMessage:
            # check if the user not exists
            userData = storageData.users.get(reqPocket.authLayer.userName)

            if userData:
                if not userData.password == reqPocket.authLayer.password:
                    errorMessage == "the password is incorrect"
            else:
                userData = UserData(id=str(uuid.uuid4()), password=reqPocket.authLayer.password)
                while os.path.isdir(config.APP_STORAGE_PATH + config.STORAGE_PRIVATE + "/" + userData.id):
                    userData.id = str(uuid.uuid4())

                os.mkdir(config.APP_STORAGE_PATH + config.STORAGE_PRIVATE + "/" + userData.id)
                storageData.users[reqPocket.authLayer.userName] = userData

                with open(config.APP_STORAGE_PATH + config.STORAGE_DATA, "w") as dataFile:
                    dataFile.write(storageData.json())

        if errorMessage:
            logging.error(errorMessage)
            resPocket = Pocket(BasicLayer(0, PocketType.AuthResponse))
            resPocket.authResponseLayer = AuthResponseLayer(False, errorMessage, 0, 0, 0)
            appSocket.sendto(resPocket.to_bytes(), clientAddress)
            return None

        storagePath = config.APP_STORAGE_PATH + config.STORAGE_PRIVATE + "/" + userData.id  + "/"

    if reqPocket.basicLayer.pocketSubType == PocketSubType.UploadRequest:
        handle_upload_request(reqPocket, clientAddress, storagePath)
    elif reqPocket.basicLayer.pocketSubType == PocketSubType.DownloadRequest:
        handle_download_request(reqPocket, clientAddress, storagePath)
    elif reqPocket.basicLayer.pocketSubType == PocketSubType.ListRequest:
        handle_list_request(reqPocket, clientAddress, storagePath)


def handle_upload_request(reqPocket: Pocket, clientAddress: tuple[str, int], storagePath: str) -> None:
    # valid pocket
    errorMessage: str | None = None
    if not reqPocket.uploadRequestLayer:
        errorMessage = "This is not upload request"
    elif len(reqPocket.uploadRequestLayer.path) > config.FILE_PATH_MAX_LENGTH:
        errorMessage = "The file path cannot be more then {} chars".format(config.FILE_PATH_MAX_LENGTH)
    elif reqPocket.authLayer.pocketFullSize <= 0:
        errorMessage = "The file cannot be empty"
    elif not in_storage(reqPocket.uploadRequestLayer.path, storagePath):
            errorMessage = "The path {} is not legal".format(reqPocket.uploadRequestLayer.path)

    if errorMessage:
        logging.error(errorMessage)
        resPocket = Pocket(BasicLayer(0, PocketType.AuthResponse, PocketSubType.UploadResponse))
        resPocket.authResponseLayer = AuthResponseLayer(False, errorMessage, 0, 0, 0)
        appSocket.sendto(resPocket.to_bytes(), clientAddress)
        return None

    fileSize = reqPocket.authLayer.pocketFullSize

    # create the file
    filePath = get_path(reqPocket.uploadRequestLayer.path, storagePath)
    directoyPath = os.path.dirname(filePath)

    # delete the file if already exists
    if os.path.isfile(filePath):
        os.remove(filePath)

    if not directoyPath:
        directoyPath = "."
    elif not os.path.isdir(directoyPath):
        os.makedirs(directoyPath, exist_ok=True)

    fileStream = open(filePath, "w")

    # split to segments info
    singleSegmentSize = max(config.SINGLE_SEGMENT_SIZE_MIN, reqPocket.authLayer.maxSingleSegmentSize)
    singleSegmentSize = min(config.SINGLE_SEGMENT_SIZE_MAX, singleSegmentSize)

    segmentsAmount = int(fileSize / singleSegmentSize)
    if segmentsAmount * singleSegmentSize < fileSize:
        segmentsAmount += 1

    windowTimeout = max(config.WINDOW_TIMEOUT_MIN, reqPocket.authLayer.maxWindowTimeout)
    windowTimeout = min(config.WINDOW_TIMEOUT_MAX, windowTimeout)

    # init the window
    neededSegments = list(range(segmentsAmount))
    segments = [b""] * segmentsAmount

    # send auth respose pocket
    pocketID = create_current_pocketID()
    resPocket = Pocket(BasicLayer(pocketID, PocketType.AuthResponse, PocketSubType.UploadResponse))
    resPocket.authResponseLayer = AuthResponseLayer(True, "", segmentsAmount, singleSegmentSize, windowTimeout)
    appSocket.sendto(resPocket.to_bytes(), clientAddress)

    # recv segments
    while len(neededSegments) > 0:
        try:
            segmentPocket = recv_pocket()

            if (not segmentPocket.segmentLayer) or (
                not segmentPocket.basicLayer.pocketType == PocketType.Segment
            ):
                logging.error("Get pocket that is not upload segment")
            else:
                segmentID = segmentPocket.segmentLayer.segmentID
                if segmentID in neededSegments:
                    # add new segment
                    neededSegments.remove(segmentID)
                    segments[segmentID] = segmentPocket.segmentLayer.data

                akcPocket = Pocket(BasicLayer(pocketID, PocketType.ACK))
                akcPocket.akcLayer = AKCLayer(segmentID)
                appSocket.sendto(akcPocket.to_bytes(), clientAddress)
        except socket.error:
            pass

    # send close pocket
    create_current_pocketID(True)
    send_close(pocketID, clientAddress)

    # save the file
    for segment in segments:
        fileStream.write(segment.decode())

    # clean up
    fileStream.close()

    logging.info('The file "{}" uploaded'.format(reqPocket.uploadRequestLayer.path))


def handle_download_request(reqPocket: Pocket, clientAddress: tuple[str, int], storagePath: str) -> None:
    # valid pocket
    errorMessage: str | None = None
    if not reqPocket.downloadRequestLayer:
        errorMessage = "This is not download request"

    filePath = get_path(reqPocket.downloadRequestLayer.path, storagePath)
    if not os.path.isfile(filePath):
        errorMessage = 'The file "{}" dos not exists!'.format(reqPocket.downloadRequestLayer.path)
    elif not in_storage(reqPocket.downloadRequestLayer.path, storagePath):
        errorMessage = 'The file "{}" dos not exists!'.format(reqPocket.downloadRequestLayer.path)

    if errorMessage:
        logging.error(errorMessage)
        resPocket = Pocket(BasicLayer(0, PocketType.AuthResponse, PocketSubType.DownloadResponse))
        resPocket.authResponseLayer = AuthResponseLayer(False, errorMessage, 0, 0, 0)
        appSocket.sendto(resPocket.to_bytes(), clientAddress)
        return None

    # ready the file for downloading
    fileSize = os.stat(filePath).st_size
    fileStream = open(filePath, "r")

    singleSegmentSize = max(config.SINGLE_SEGMENT_SIZE_MIN, reqPocket.authLayer.maxSingleSegmentSize)
    singleSegmentSize = min(config.SINGLE_SEGMENT_SIZE_MAX, singleSegmentSize)

    segmentsAmount = int(fileSize / singleSegmentSize)
    if segmentsAmount * singleSegmentSize < fileSize:
        segmentsAmount += 1

    windowTimeout = max(config.WINDOW_TIMEOUT_MIN, reqPocket.authLayer.maxWindowTimeout)
    windowTimeout = min(config.WINDOW_TIMEOUT_MAX, windowTimeout)

    # send the download respose
    pocketID = create_current_pocketID()

    ready = False
    while not ready:
        resPocket = Pocket(BasicLayer(pocketID, PocketType.AuthResponse, PocketSubType.DownloadResponse))
        resPocket.authResponseLayer = AuthResponseLayer(True, errorMessage, segmentsAmount, singleSegmentSize, windowTimeout)
        appSocket.sendto(resPocket.to_bytes(), clientAddress)

        # recive the ready ACK from the client
        readyPocket = recv_pocket()
        ready = readyPocket.basicLayer.pocketSubType == PocketSubType.DownloadReadyForDownloading

    # downloading the segments
    windowToSend = list(range(segmentsAmount))
    windowSending = []

    last = time.time()

    downloading = True

    while downloading:
        now = time.time()
        if last + windowTimeout > now:
            # send a segment
            if len(windowToSend) > 0:
                segmentID = windowToSend.pop(0)
                fileStream.seek(segmentID * singleSegmentSize)
                if segmentID * singleSegmentSize <= fileSize - singleSegmentSize:
                    # is not the last segment
                    segment = fileStream.read(singleSegmentSize)
                else:
                    # is the last segment
                    segment = fileStream.read(fileSize - singleSegmentSize)

                segmentPocket = Pocket(BasicLayer(pocketID, PocketType.Segment))
                segmentPocket.segmentLayer = SegmentLayer(segmentID, segment.encode())

                windowSending.append(segmentID)

                appSocket.sendto(segmentPocket.to_bytes(), clientAddress)
        else:
            # refresh window
            logging.debug(
                "refresh window {}/{}".format(segmentsAmount - len(windowToSend) - len(windowSending), segmentsAmount)
            )
            timeout = False
            while not timeout:
                try:
                    pocket = recv_pocket()
                except TimeoutError:
                    timeout = True

                if not timeout:
                    if pocket.basicLayer.pocketSubType == PocketSubType.DownloadComplited:
                        # complit the downloading
                        timeout = True
                        downloading = False
                    elif pocket.akcLayer:
                        if pocket.akcLayer.segmentID in windowToSend:
                            windowToSend.remove(pocket.akcLayer.segmentID)
                        if pocket.akcLayer.segmentID in windowSending:
                            windowSending.remove(pocket.akcLayer.segmentID)

                        else:
                            logging.error("Get pocket that not ACK and not download complited")

            windowToSend = windowSending + windowToSend
            windowSending = []

            last = time.time()

    fileStream.close()

    # send close pocket
    send_close(pocketID, clientAddress)


def handle_list_request(reqPocket: Pocket, clientAddress: tuple[str, int], storagePath: str) -> None:
    # valid pocket
    errorMessage: str | None = None
    if not reqPocket.listRequestLayer:
        errorMessage = "This is not list request"

    directoryPath = get_path(reqPocket.listRequestLayer.path, storagePath)
    if not os.path.isdir(directoryPath):
        errorMessage = 'The directory "{}" dos not exists!'.format(reqPocket.listRequestLayer.path)
    elif not in_storage(reqPocket.listRequestLayer.path, storagePath):
        errorMessage = 'The directory "{}" dos not exists!'.format(reqPocket.listRequestLayer.path)

    if errorMessage:
        logging.error(errorMessage)
        resPocket = Pocket(BasicLayer(0, PocketType.AuthResponse, PocketSubType.ListResponse))
        resPocket.authResponseLayer = AuthResponseLayer(False, errorMessage, 0, 0, 0)
        appSocket.sendto(resPocket.to_bytes(), clientAddress)
        return None

    directoriesAndFiles = os.listdir(directoryPath)
    directories = [directory for directory in directoriesAndFiles if os.path.isdir(directoryPath + "/" + directory)]
    files = [file for file in directoriesAndFiles if os.path.isfile(directoryPath + "/" + file)]

    # check if exist directories or files
    if len(directories) == 0 and len(files) == 0:
        resPocket = Pocket(BasicLayer(0, PocketType.AuthResponse, PocketSubType.ListResponse))
        resPocket.authResponseLayer = AuthResponseLayer(True, "", 0, 0, 0)
        appSocket.sendto(resPocket.to_bytes(), clientAddress)
        return None

    # soring the directories and files
    directories.sort()
    files.sort()

    # create the full content in bytes to download
    content = b""
    for directoryName in directories:
        updatedAt = os.path.getmtime(directoryPath + "/" + directoryName)

        content += pack_directory_block(directoryName, updatedAt)

    for fileName in files:
        updatedAt = os.path.getmtime(directoryPath + "/" + fileName)
        fileSize = os.stat(directoryPath + "/" + fileName).st_size

        content += pack_file_block(fileName, updatedAt, fileSize)

    # ready the content for downloading
    contentSize = len(content)

    singleSegmentSize = max(config.SINGLE_SEGMENT_SIZE_MIN, reqPocket.authLayer.maxSingleSegmentSize)
    singleSegmentSize = min(config.SINGLE_SEGMENT_SIZE_MAX, singleSegmentSize)

    segmentsAmount = int(contentSize / singleSegmentSize)
    if segmentsAmount * singleSegmentSize < contentSize:
        segmentsAmount += 1

    windowTimeout = max(config.WINDOW_TIMEOUT_MIN, reqPocket.authLayer.maxWindowTimeout)
    windowTimeout = min(config.WINDOW_TIMEOUT_MAX, windowTimeout)

    # send the list respose
    pocketID = create_current_pocketID()

    ready = False
    while not ready:
        resPocket = Pocket(BasicLayer(pocketID, PocketType.AuthResponse, PocketSubType.ListResponse))
        resPocket.authResponseLayer = AuthResponseLayer(True, "", segmentsAmount, singleSegmentSize, windowTimeout)
        resPocket.listResponseLayer = ListResponseLayer(len(directories), len(files))
        appSocket.sendto(resPocket.to_bytes(), clientAddress)

        # recive the ready ACK from the client
        readyPocket = recv_pocket()
        ready = readyPocket.basicLayer.pocketSubType == PocketSubType.ListReadyForDownloading

    # downloading the segments
    windowToSend = list(range(segmentsAmount))
    windowSending = []

    last = time.time()

    downloading = True

    while downloading:
        now = time.time()
        if last + windowTimeout > now:
            # send a segment
            if len(windowToSend) > 0:
                segmentID = windowToSend.pop(0)
                if segmentID * singleSegmentSize <= contentSize - singleSegmentSize:
                    # is not the last segment
                    segment = content[segmentID * singleSegmentSize : (segmentID + 1) * singleSegmentSize]
                else:
                    segment = content[segmentID * singleSegmentSize :]

                segmentPocket = Pocket(BasicLayer(pocketID, PocketType.Segment))
                segmentPocket.segmentLayer = SegmentLayer(segmentID, segment)

                windowSending.append(segmentID)

                appSocket.sendto(segmentPocket.to_bytes(), clientAddress)
        else:
            # refresh window
            logging.debug(
                "refresh window {}/{}".format(segmentsAmount - len(windowToSend) - len(windowSending), segmentsAmount)
            )
            timeout = False
            while not timeout:
                try:
                    pocket = recv_pocket()
                except TimeoutError:
                    timeout = True

                if not timeout:
                    if pocket.basicLayer.pocketSubType == PocketSubType.ListComplited:
                        # complit the downloading
                        timeout = True
                        downloading = False
                    elif pocket.akcLayer:
                        if pocket.akcLayer.segmentID in windowToSend:
                            windowToSend.remove(pocket.akcLayer.segmentID)
                        if pocket.akcLayer.segmentID in windowSending:
                            windowSending.remove(pocket.akcLayer.segmentID)

                        else:
                            logging.error("Get pocket that not ACK and not list complited")

            windowToSend = windowSending + windowToSend
            windowSending = []

            last = time.time()

    # send close pocket
    send_close(pocketID, clientAddress)


# entry point
def main() -> None:
    init_app()
    create_socket()
    main_loop()


if __name__ == "__main__":
    main()
