# entry point to Application

import os
import os.path
import logging
import socket
from typing import Any

from src.lib.config import config, init_config, init_logging

from src.lib.ftp import *

# config

SINGLE_SEGMENT_SIZE_LIMIT = (10, 1500) # [byte]
WINDOW_TIMEOUT_LIMIT = (0.1, 1) # [s]


# globals
appSocket: socket.socket

def main() -> None:
    init_app()
    create_socket()
    main_loop()


def init_app() -> None:
    init_config()
    init_logging()
    init_strorage()

    logging.info('The app is initialized')


def init_strorage():
    if not os.path.isdir(config.APP_STORAGE_PATH):
        os.mkdir(config.APP_STORAGE_PATH)

def get_path(filePath: str) -> str:
    return config.APP_STORAGE_PATH + "/" + filePath

def create_socket() -> None:
    global appSocket

    appSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    appSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    appSocket.bind((config.APP_HOST, config.APP_PORT))
    appSocket.setblocking(1)
    appSocket.settimeout(config.SOCKET_TIMEOUT)

    logging.info('The app socket initialized on ' + config.APP_HOST + ":" + str(config.APP_PORT))


def main_loop() -> None:
    while True:
        try:
            data, clientAddress = appSocket.recvfrom(config.SOCKET_MAXSIZE)

            reqPocket = Pocket.from_bytes(data)

            if not reqPocket.authLayer:
                send_close(reqPocket.get_id(), clientAddress)
            else:
                handle_request(reqPocket, clientAddress)
        except socket.error:
            pass


# working with clients
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


def send_close(pocketID: int, clientAddress: Any) -> None:
    closePocket = Pocket(BasicLayer(pocketID, PocketType.Close))
    appSocket.sendto(closePocket.to_bytes(), clientAddress)


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


# controllers
def handle_request(reqPocket: Pocket, clientAddress: tuple[str, int]) -> None:
    if reqPocket.basicLayer.pocketSubType == PocketSubType.UploadRequest:
        handle_upload_request(reqPocket, clientAddress)
    elif reqPocket.basicLayer.pocketSubType == PocketSubType.DownloadRequest:
        handle_download_request(reqPocket, clientAddress)
    elif reqPocket.basicLayer.pocketSubType == PocketSubType.ListRequest:
        handle_list_request(reqPocket, clientAddress)


def handle_upload_request(reqPocket: Pocket, clientAddress: tuple[str, int]) -> None:
    # valid pocket
    errorMessage: str | None = None
    if not reqPocket.uploadRequestLayer:
        errorMessage = "This is not upload request"
    elif len(reqPocket.uploadRequestLayer.path) > config.FILE_PATH_MAX_LENGTH:
        errorMessage = "The file path cannot be more then " + config.FILE_PATH_MAX_LENGTH + " chars"
    elif reqPocket.uploadRequestLayer.fileSize <= 0:
        errorMessage = "The file cannot be empty"

    if errorMessage:
        logging.error(errorMessage)
        resPocket = Pocket(BasicLayer(0, PocketType.AuthResponse, PocketSubType.UploadResponse))
        resPocket.authResponseLayer = AuthResponseLayer(0, 0, 0)
        resPocket.uploadResponseLayer = UploadResponseLayer(False, errorMessage)
        appSocket.sendto(resPocket.to_bytes(), clientAddress)
        return None

    # create the file
    filePath = get_path(reqPocket.uploadRequestLayer.path)
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
    singleSegmentSize = max(SINGLE_SEGMENT_SIZE_LIMIT[0], reqPocket.authLayer.maxSingleSegmentSize)
    singleSegmentSize = min(SINGLE_SEGMENT_SIZE_LIMIT[1], singleSegmentSize)

    segmentsAmount = int(reqPocket.uploadRequestLayer.fileSize / singleSegmentSize)
    if segmentsAmount * singleSegmentSize < reqPocket.uploadRequestLayer.fileSize:
        segmentsAmount += 1

    windowTimeout = max(WINDOW_TIMEOUT_LIMIT[0], reqPocket.authLayer.maxWindowTimeout)
    windowTimeout = min(WINDOW_TIMEOUT_LIMIT[1], windowTimeout)

    # init the window
    neededSegments = list(range(segmentsAmount))
    segments = [b""] * segmentsAmount

    # send auth respose pocket
    pocketID = create_current_pocketID()
    resPocket = Pocket(BasicLayer(pocketID, PocketType.AuthResponse, PocketSubType.UploadResponse))
    resPocket.authResponseLayer = AuthResponseLayer(segmentsAmount, singleSegmentSize, windowTimeout)
    resPocket.uploadResponseLayer = UploadResponseLayer(True, "")
    appSocket.sendto(resPocket.to_bytes(), clientAddress)

    # recv segments
    while len(neededSegments) > 0:
        try:
            segmentPocket = recv_pocket()

            if (not segmentPocket.segmentLayer) or (not segmentPocket.basicLayer.pocketSubType == PocketSubType.UploadSegment):
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

    logging.info("The file \"{}\" uploaded".format(reqPocket.uploadRequestLayer.path))


def handle_download_request(reqPocket: Pocket, clientAddress: tuple[str, int]) -> None:
    # valid pocket
    errorMessage: str | None = None
    if not reqPocket.downloadRequestLayer:
        errorMessage = "This is not download request"

    filePath = get_path(reqPocket.downloadRequestLayer.path)
    if not os.path.isfile(filePath):
        errorMessage = "The file \"{}\" dos not exists!".format(reqPocket.downloadRequestLayer.path)

    if errorMessage:
        logging.error(errorMessage)
        resPocket = Pocket(BasicLayer(0, PocketType.AuthResponse, PocketSubType.DownloadResponse))
        resPocket.authResponseLayer = AuthResponseLayer(0, 0, 0)
        resPocket.downloadResponseLayer = DownloadResponseLayer(False, errorMessage, 0, 0.0)
        appSocket.sendto(resPocket.to_bytes(), clientAddress)
        return None

    # ready the file for downloading
    fileSize = os.stat(filePath).st_size
    updatedAt = os.path.getmtime(filePath)
    fileStream = open(filePath, "r")

    singleSegmentSize = max(SINGLE_SEGMENT_SIZE_LIMIT[0], reqPocket.authLayer.maxSingleSegmentSize)
    singleSegmentSize = min(SINGLE_SEGMENT_SIZE_LIMIT[1], singleSegmentSize)

    segmentsAmount = int(fileSize / singleSegmentSize)
    if segmentsAmount * singleSegmentSize < fileSize:
        segmentsAmount += 1

    windowTimeout = max(WINDOW_TIMEOUT_LIMIT[0], reqPocket.authLayer.maxWindowTimeout)
    windowTimeout = min(WINDOW_TIMEOUT_LIMIT[1], windowTimeout)

    # send the download respose
    pocketID = create_current_pocketID()

    ready = False
    while not ready:
        resPocket = Pocket(BasicLayer(pocketID, PocketType.AuthResponse, PocketSubType.DownloadResponse))
        resPocket.authResponseLayer = AuthResponseLayer(segmentsAmount, singleSegmentSize, windowTimeout)
        resPocket.downloadResponseLayer = DownloadResponseLayer(True, "", fileSize, updatedAt)
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

                segmentPocket = Pocket(BasicLayer(pocketID, PocketType.Segment, PocketSubType.DownloadSegment))
                segmentPocket.segmentLayer = SegmentLayer(segmentID, segment.encode())

                windowSending.append(segmentID)

                appSocket.sendto(segmentPocket.to_bytes(), clientAddress)
        else:
            # refresh window
            logging.debug("refresh window {}/{}".format(segmentsAmount - len(windowToSend) - len(windowSending), segmentsAmount))
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


def handle_list_request(reqPocket: Pocket, clientAddress: tuple[str, int]) -> None:
    # valid pocket
    errorMessage: str | None = None
    if not reqPocket.listRequestLayer:
        errorMessage = "This is not list request"

    directoryPath = get_path(reqPocket.listRequestLayer.path)
    if not os.path.isdir(directoryPath):
        errorMessage = "The directory \"{}\" dos not exists!".format(reqPocket.listRequestLayer.path)

    if errorMessage:
        logging.error(errorMessage)
        resPocket = Pocket(BasicLayer(0, PocketType.AuthResponse, PocketSubType.ListResponse))
        resPocket.authResponseLayer = AuthResponseLayer(0, 0, 0)
        resPocket.listResponseLayer = ListResponseLayer(False, errorMessage, 0, 0)
        appSocket.sendto(resPocket.to_bytes(), clientAddress)
        return None

    directoriesAndFiles = os.listdir(directoryPath)
    directories = [directory for directory in directoriesAndFiles if os.path.isdir(directoryPath + "/" + directory)]
    files = [file for file in directoriesAndFiles if os.path.isfile (directoryPath + "/" + file)]

    # check if exist directories or files
    if len(directories) == 0 and len(files) == 0:
        resPocket = Pocket(BasicLayer(0, PocketType.AuthResponse, PocketSubType.ListResponse))
        resPocket.authResponseLayer = AuthResponseLayer(0, 0, 0)
        resPocket.listResponseLayer = ListResponseLayer(True, "", 0, 0)
        appSocket.sendto(resPocket.to_bytes(), clientAddress)
        return None

    ## ! TODO all the continue

    # ready the file for downloading
    fileSize = os.stat(filePath).st_size
    updatedAt = os.path.getmtime(filePath)
    fileStream = open(filePath, "r")

    singleSegmentSize = max(SINGLE_SEGMENT_SIZE_LIMIT[0], reqPocket.authLayer.maxSingleSegmentSize)
    singleSegmentSize = min(SINGLE_SEGMENT_SIZE_LIMIT[1], singleSegmentSize)

    segmentsAmount = int(fileSize / singleSegmentSize)
    if segmentsAmount * singleSegmentSize < fileSize:
        segmentsAmount += 1

    windowTimeout = max(WINDOW_TIMEOUT_LIMIT[0], reqPocket.authLayer.maxWindowTimeout)
    windowTimeout = min(WINDOW_TIMEOUT_LIMIT[1], windowTimeout)

    # send the download respose
    pocketID = create_current_pocketID()

    ready = False
    while not ready:
        resPocket = Pocket(BasicLayer(pocketID, PocketType.AuthResponse, PocketSubType.DownloadResponse))
        resPocket.authResponseLayer = AuthResponseLayer(segmentsAmount, singleSegmentSize, windowTimeout)
        resPocket.downloadResponseLayer = DownloadResponseLayer(True, "", fileSize, updatedAt)
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

                segmentPocket = Pocket(BasicLayer(pocketID, PocketType.Segment, PocketSubType.DownloadSegment))
                segmentPocket.segmentLayer = SegmentLayer(segmentID, segment.encode())

                windowSending.append(segmentID)

                appSocket.sendto(segmentPocket.to_bytes(), clientAddress)
        else:
            # refresh window
            logging.debug("refresh window {}/{}".format(segmentsAmount - len(windowToSend) - len(windowSending), segmentsAmount))
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



if __name__ == "__main__":
    main()
