# entry point to Application

import os
import os.path
import logging
import socket
from typing import Any

from src.lib.config import config, init_config, init_logging

from src.lib.ftp import *

# config

SINGLE_SEGMENT_SIZE_LIMIT = (4, 1500) # [byte]
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

def get_current_pocketID() -> int:
    return currentPocketID

def create_current_pocketID() -> int:
    global currentPocketID
    currentPocketID += 1
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
        # TODO handle download
        pass
    elif reqPocket.basicLayer.pocketSubType == PocketSubType.ListRequest:
        # TODO handle list request
        pass


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
        reqPocket.uploadResponseLayer = UploadResponseLayer(False, errorMessage)
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

    if not os.path.isdir(directoyPath):
        os.mkdir(directoyPath)

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
            segmetPocket = recv_pocket()

            if (not segmetPocket.segmentLayer) or (not segmetPocket.basicLayer.pocketSubType == PocketSubType.UploadSegment):
                logging.error("Get pocket that is not upload segment")
            else:
                segmentID = segmetPocket.segmentLayer.segmentID
                if segmentID in neededSegments:
                    # add new segment
                    neededSegments.remove(segmentID)
                    segments[segmentID] = segmetPocket.segmentLayer.data

                akcPocket = Pocket(BasicLayer(pocketID, PocketType.ACK))
                akcPocket.akcLayer = AKCLayer(segmentID)
                appSocket.sendto(akcPocket.to_bytes(), clientAddress)
        except socket.error:
            pass

    # send close pocket
    send_close(pocketID, clientAddress)

    # save the file
    for segment in segments:
        fileStream.write(segment.decode())

    # clean up
    fileStream.close()

    logging.info("The file \"{}\" uploaded".format(reqPocket.uploadRequestLayer.path))


if __name__ == "__main__":
    main()
