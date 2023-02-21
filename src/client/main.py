# entry point to Application

import os
import time
import logging
import socket

from src.lib.config import config, init_config, init_logging
from src.lib.ftp import *

clientSocket: socket.socket

def init_app() -> None:
    init_config()
    init_logging()

    logging.info('The app is initialized')

def create_socket() -> None:
    global clientSocket

    clientSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    clientSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    clientSocket.bind((config.CLIENT_HOST, config.CLIENT_PORT))
    clientSocket.setblocking(1)
    clientSocket.settimeout(config.SOCKET_TIMEOUT)

    print('The client socket initialized on ' + config.CLIENT_HOST + ":" + str(config.CLIENT_PORT))

currentPocketID = 0

def get_current_pocketID() -> int:
    return currentPocketID

def create_current_pocketID() -> int:
    global currentPocketID
    currentPocketID += 1
    return currentPocketID

def upload_file(filename: str, destination: str) -> None:
    create_socket()

    maxSingleSegmentSize = 4
    maxWindowTimeout = 100 # [ms]

    # load the file info
    if not os.path.isfile(filename):
        print("The file\"" + filename + "\" don't exists!")
        return None

    fileStream = open(filename, "r")

    pocketFullSize = fileSize = os.stat(filename).st_size

    # create request pocket

    appAddress = (config.APP_HOST, config.APP_PORT)
    pocketID = create_current_pocketID()

    reqPocket = Pocket(BasicLayer(pocketID, PocketType.Auth, PocketSubType.UploadRequest))
    reqPocket.authLayer = AuthLayer(pocketFullSize, maxSingleSegmentSize, maxWindowTimeout)
    reqPocket.uploadRequestLayer = UploadRequestLayer(destination, fileSize)

    # send request

    logging.debug("send req pocket: " + str(reqPocket))

    clientSocket.sendto(reqPocket.to_bytes(), appAddress)

    # recive response

    data = clientSocket.recvfrom(config.SOCKET_MAXSIZE)[0]
    resPocket = Pocket.from_bytes(data)

    # handle response
    logging.debug("get res pocket: " + str(resPocket))

    if not resPocket.authResponseLayer or not resPocket.uploadResponseLayer:
        print("Error: faild to send the file")
        fileStream.close()
        return None

    if not resPocket.uploadResponseLayer.ok:
        print("Error: " + resPocket.uploadResponseLayer.errorMessage)
        fileStream.close()
        return None

    # send the file
    singleSegmentSize = resPocket.authResponseLayer.singleSegmentSize
    segmentsAmount = resPocket.authResponseLayer.segmentsAmount
    windowTimeout = resPocket.authResponseLayer.windowTimeout

    windowToSend = list(range(segmentsAmount))
    windowSending = []

    last = time.time()

    uploading = True

    while uploading:
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

                segmentPocket = Pocket(BasicLayer(pocketID, PocketType.Segment, PocketSubType.UploadSegment))
                segmentPocket.segmentLayer = SegmentLayer(segmentID, segment.encode())

                windowSending.append(segmentID)

                clientSocket.sendto(segmentPocket.to_bytes(), appAddress)
                logging.debug("send segment {}".format(segmentID))
        else:
            # refresh window
            logging.debug("refresh window {}/{}".format(segmentsAmount - len(windowToSend) - len(windowSending), segmentsAmount))
            timeout = False
            while not timeout:
                try:
                    data = clientSocket.recvfrom(config.SOCKET_MAXSIZE)[0]
                except TimeoutError:
                    timeout = True

                if not timeout:
                    pocket = Pocket.from_bytes(data)
                    if pocket.get_id() == get_current_pocketID():
                        if pocket.basicLayer.pocketType == PocketType.Close:
                            # complit the upload
                            print("The file \"{}\" upload as \"{}\" to the app.".format(filename, destination))
                            uploading = False
                        elif pocket.akcLayer:
                            if pocket.akcLayer.segmentID in windowToSend:
                                windowToSend.remove(pocket.akcLayer.segmentID)
                            if pocket.akcLayer.segmentID in windowSending:
                                windowSending.remove(pocket.akcLayer.segmentID)

                        else:
                            print("Error: get pocket that not ACK and not Close")
                    else:
                        print("Error: get pocket that has warng pocket ID")

            windowToSend = windowSending + windowToSend
            windowSending = []

            last = time.time()


    fileStream.close()


def main() -> None:
    init_app()

    upload_file("uploads/A.md", "A.md")



if __name__ == "__main__":
    main()
