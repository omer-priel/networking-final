# entry point to Application

import sys
import os
import time
import logging
import socket

from src.lib.config import config, init_config, init_logging
from src.lib.ftp import *

clientSocket: socket.socket

MAX_SEGMENT_SIZE = 1000 # [byte]
MAX_WINDOW_TIMEOUT = 1 # [s]

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


def upload_file(filename: str, destination: str) -> None:
    create_socket()

    # load the file info
    if not os.path.isfile(filename):
        print("The file\"" + filename + "\" don't exists!")
        return None

    fileStream = open(filename, "r")

    pocketFullSize = fileSize = os.stat(filename).st_size

    # create request pocket

    appAddress = (config.APP_HOST, config.APP_PORT)

    reqPocket = Pocket(BasicLayer(0, PocketType.Auth, PocketSubType.UploadRequest))
    reqPocket.authLayer = AuthLayer(pocketFullSize, MAX_SEGMENT_SIZE, MAX_WINDOW_TIMEOUT)
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
    pocketID = resPocket.basicLayer.pocketID

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
                    if pocket.basicLayer.pocketType == PocketType.Close:
                        # complit the upload
                        print("The file \"{}\" upload as \"{}\" to the app.".format(filename, destination))
                        timeout = True
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


def download_file(filePath: str, destination: str):
    # check if the directory of destination exists

    # remove if need the destination

    # create and remove again destination for checking

    # send download request

    # recive download response

    # handel response

    # init containers for downloading

    # send ack for start downloading

    # handel segments

    # send complite ACK knowning the app that the file complited

    # wait for closeing and sending ACK's in the same time

    # close the connection

    # create the file

    # clean up
    pass


def send_list_command(directoryPath: str):
    # TODO list command
    pass


def print_help():
    # TODO print help command
    pass

def main() -> None:
    init_app()

    if len(sys.argv) < 2:
        print_help()
        return None

    if sys.argv[1] == "upload":
        filename = None
        destination = None

        i = 2
        while i < len(sys.argv):
            if sys.argv[i] == "--dest":
                if i == len(sys.argv) - 1:
                    print("The option --dest need destaion as paramter")
                    return None
                destination = sys.argv[i + 1]
                i += 1
            else:
                filename = sys.argv[i]
            i += 1

        if not filename:
            print("Missing file path to upload")
            return None

        if not destination:
            destination = os.path.basename(filename)

        upload_file(filename, destination)
    elif sys.argv[1] == "download":
        if len(sys.argv) == 2:
            print("File path and destination path are Missing!")
            return None
        if len(sys.argv) == 3:
            print("Destination path are Missing!")
            return None

        filePath = sys.argv[2]
        destination = sys.argv[3]

        download_file(filePath, destination)

    elif sys.argv[1] == "list":
        if len(sys.argv) == 2:
            directoryPath = "."
        else:
            directoryPath = sys.argv[2]

        send_list_command(directoryPath)

    else:
        print("The command \"{}\" not exists".format(sys.argv[1]))



if __name__ == "__main__":
    main()
