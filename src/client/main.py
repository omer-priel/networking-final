# entry point to Application

import logging
import os
import os.path
import socket
import sys
import time

from prettytable import PrettyTable

from src.lib.config import config, init_config, init_logging
from src.lib.ftp import *

clientSocket: socket.socket

MAX_SEGMENT_SIZE = 1000  # [byte]
MAX_WINDOW_TIMEOUT = 1  # [s]


def init_app() -> None:
    init_config()

    config.LOGGING_LEVEL = logging.CRITICAL

    init_logging()

    logging.info("The app is initialized")


def create_socket() -> None:
    global clientSocket

    clientSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    clientSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    clientSocket.bind((config.CLIENT_HOST, config.CLIENT_PORT))
    clientSocket.setblocking(1)
    clientSocket.settimeout(config.SOCKET_TIMEOUT)

    print("The client socket initialized on " + config.CLIENT_HOST + ":" + str(config.CLIENT_PORT))


def upload_file(filename: str, destination: str) -> None:
    # load the file info
    if not os.path.isfile(filename):
        print('The file"' + filename + "\" don't exists!")
        return None

    fileStream = open(filename, "r")

    fileSize = os.stat(filename).st_size

    # create request pocket

    appAddress = (config.APP_HOST, config.APP_PORT)

    reqPocket = Pocket(BasicLayer(0, PocketType.Auth, PocketSubType.UploadRequest))
    reqPocket.authLayer = AuthLayer(fileSize, MAX_SEGMENT_SIZE, MAX_WINDOW_TIMEOUT)
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
            logging.debug(
                "refresh window {}/{}".format(segmentsAmount - len(windowToSend) - len(windowSending), segmentsAmount)
            )
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
                        print('The file "{}" upload as "{}" to the app.'.format(filename, destination))
                        timeout = True
                        uploading = False
                    elif pocket.akcLayer:
                        if pocket.akcLayer.segmentID in windowToSend:
                            windowToSend.remove(pocket.akcLayer.segmentID)
                        if pocket.akcLayer.segmentID in windowSending:
                            windowSending.remove(pocket.akcLayer.segmentID)
                        else:
                            print("Error: get pocket that not ACK and not Close")

            windowToSend = windowSending + windowToSend
            windowSending = []

            last = time.time()

    fileStream.close()


def download_file(filePath: str, destination: str):
    # check if the directory of destination exists
    if os.path.isfile(destination):
        os.remove(destination)
    elif not os.path.isdir(os.path.dirname(destination)):
        os.mkdir(os.path.dirname(destination))

    # remove if need the destination
    # create and remove again destination for checking
    fileStream = open(destination, "a")
    if not fileStream.writable():
        print('Error: The file "{}" is not writable!'.format(destination))
        fileStream.close()
        os.remove(destination)
        return None

    fileStream.close()
    os.remove(destination)

    # send download request
    appAddress = (config.APP_HOST, config.APP_PORT)

    reqPocket = Pocket(BasicLayer(0, PocketType.Auth, PocketSubType.DownloadRequest))
    reqPocket.authLayer = AuthLayer(0, MAX_SEGMENT_SIZE, MAX_WINDOW_TIMEOUT)
    reqPocket.downloadRequestLayer = DownloadRequestLayer(filePath)

    logging.debug("send req pocket: " + str(reqPocket))

    clientSocket.sendto(reqPocket.to_bytes(), appAddress)

    # recive download response
    data = clientSocket.recvfrom(config.SOCKET_MAXSIZE)[0]
    resPocket = Pocket.from_bytes(data)

    # handel response
    logging.debug("get res pocket: " + str(resPocket))

    if not resPocket.authResponseLayer or not resPocket.downloadResponseLayer:
        print("Error: faild to download the file")
        return None

    if not resPocket.downloadResponseLayer.ok:
        print("Error: " + resPocket.downloadResponseLayer.errorMessage)
        return None

    # init segments for downloading
    pocketID = resPocket.basicLayer.pocketID

    segmentsAmount = resPocket.authResponseLayer.segmentsAmount

    neededSegments = list(range(segmentsAmount))
    segments = [b""] * segmentsAmount

    # send ack for start downloading
    readyPocket = Pocket(BasicLayer(pocketID, PocketType.ACK, PocketSubType.DownloadReadyForDownloading))
    readyPocket.akcLayer = AKCLayer(0)

    logging.debug("send ready ack pocket: " + str(readyPocket))

    # send ready pockets until segment comes
    itFirstSegment = False

    while not itFirstSegment:
        clientSocket.sendto(readyPocket.to_bytes(), appAddress)

        try:
            data = clientSocket.recvfrom(config.SOCKET_MAXSIZE)[0]
            segmentPocket = Pocket.from_bytes(data)
            itFirstSegment = segmentPocket.basicLayer.pocketSubType == PocketSubType.DownloadSegment
        except socket.error:
            pass

    # handle segments
    while len(neededSegments) > 0:
        try:
            if itFirstSegment:
                itFirstSegment = False
            else:
                data = clientSocket.recvfrom(config.SOCKET_MAXSIZE)[0]
                segmentPocket = Pocket.from_bytes(data)

            if (not segmentPocket.segmentLayer) or (
                not segmentPocket.basicLayer.pocketSubType == PocketSubType.DownloadSegment
            ):
                logging.error("Get pocket that is not download segment")
            else:
                segmentID = segmentPocket.segmentLayer.segmentID
                if segmentID in neededSegments:
                    # add new segment
                    neededSegments.remove(segmentID)
                    segments[segmentID] = segmentPocket.segmentLayer.data

                akcPocket = Pocket(BasicLayer(pocketID, PocketType.ACK))
                akcPocket.akcLayer = AKCLayer(segmentID)
                clientSocket.sendto(akcPocket.to_bytes(), appAddress)
        except socket.error:
            pass

    # send complited download pocket to knowning the app that the file complited
    # until recive close pocket
    complitedPocket = Pocket(BasicLayer(pocketID, PocketType.ACK, PocketSubType.DownloadComplited))
    complitedPocket.akcLayer = AKCLayer(0)

    closed = False

    while not closed:
        clientSocket.sendto(complitedPocket.to_bytes(), appAddress)

        try:
            data = clientSocket.recvfrom(config.SOCKET_MAXSIZE)[0]
            closePocket = Pocket.from_bytes(data)
            closed = closePocket.basicLayer.pocketType == PocketType.Close
        except socket.error:
            pass

    # create the file
    fileStream = open(destination, "a")
    for segment in segments:
        fileStream.write(segment.decode())

    # clean up
    fileStream.close()

    logging.info('The file "{}" downloaded to "{}".'.format(filePath, destination))


def send_list_command(directoryPath: str):
    # send list request
    appAddress = (config.APP_HOST, config.APP_PORT)

    reqPocket = Pocket(BasicLayer(0, PocketType.Auth, PocketSubType.ListRequest))
    reqPocket.authLayer = AuthLayer(0, MAX_SEGMENT_SIZE, MAX_WINDOW_TIMEOUT)
    reqPocket.listRequestLayer = ListRequestLayer(directoryPath)

    logging.debug("send req pocket: " + str(reqPocket))

    clientSocket.sendto(reqPocket.to_bytes(), appAddress)

    # recive list response
    data = clientSocket.recvfrom(config.SOCKET_MAXSIZE)[0]
    resPocket = Pocket.from_bytes(data)

    # handle response
    logging.debug("get res pocket: " + str(resPocket))

    if not resPocket.authResponseLayer or not resPocket.listResponseLayer:
        print("Error: the list request faild")
        return None

    if not resPocket.listResponseLayer.ok:
        print("Error: " + resPocket.listResponseLayer.errorMessage)
        return None

    if resPocket.listResponseLayer.directoriesCount == 0 and resPocket.listResponseLayer.directoriesCount == 0:
        print("The directory is empty")
        return None

    # init segments for downloading
    pocketID = resPocket.basicLayer.pocketID

    segmentsAmount = resPocket.authResponseLayer.segmentsAmount

    neededSegments = list(range(segmentsAmount))
    segments = [b""] * segmentsAmount

    # send ack for start downloading
    readyPocket = Pocket(BasicLayer(pocketID, PocketType.ACK, PocketSubType.ListReadyForDownloading))
    readyPocket.akcLayer = AKCLayer(0)

    logging.debug("send ready ack pocket: " + str(readyPocket))

    # send ready pockets until segment comes
    itFirstSegment = False

    while not itFirstSegment:
        clientSocket.sendto(readyPocket.to_bytes(), appAddress)

        try:
            data = clientSocket.recvfrom(config.SOCKET_MAXSIZE)[0]
            segmentPocket = Pocket.from_bytes(data)
            itFirstSegment = segmentPocket.basicLayer.pocketSubType == PocketSubType.ListSegment
        except socket.error:
            pass

    # handle segments
    while len(neededSegments) > 0:
        try:
            if itFirstSegment:
                itFirstSegment = False
            else:
                data = clientSocket.recvfrom(config.SOCKET_MAXSIZE)[0]
                segmentPocket = Pocket.from_bytes(data)

            if (not segmentPocket.segmentLayer) or (
                not segmentPocket.basicLayer.pocketSubType == PocketSubType.ListSegment
            ):
                logging.error("Get pocket that is not list segment")
            else:
                segmentID = segmentPocket.segmentLayer.segmentID
                if segmentID in neededSegments:
                    # add new segment
                    neededSegments.remove(segmentID)
                    segments[segmentID] = segmentPocket.segmentLayer.data

                akcPocket = Pocket(BasicLayer(pocketID, PocketType.ACK))
                akcPocket.akcLayer = AKCLayer(segmentID)
                clientSocket.sendto(akcPocket.to_bytes(), appAddress)
        except socket.error:
            pass

    # send complited list pocket to knowning the app that the list download complited
    # until recive close pocket
    complitedPocket = Pocket(BasicLayer(pocketID, PocketType.ACK, PocketSubType.ListComplited))
    complitedPocket.akcLayer = AKCLayer(0)

    closed = False

    while not closed:
        clientSocket.sendto(complitedPocket.to_bytes(), appAddress)

        try:
            data = clientSocket.recvfrom(config.SOCKET_MAXSIZE)[0]
            closePocket = Pocket.from_bytes(data)
            closed = closePocket.basicLayer.pocketType == PocketType.Close
        except socket.error:
            pass

    # combain the segments
    data = b""
    for segment in segments:
        data += segment

    # load the directory content
    directories = []
    files = []

    i = 0
    offset = 0
    while i < resPocket.listResponseLayer.directoriesCount:
        directoryInfo, offset = unpack_directory_block(data, offset)
        directories.append(directoryInfo)
        i += 1

    i = 0
    while i < resPocket.listResponseLayer.filesCount:
        fileInfo, offset = unpack_file_block(data, offset)
        files.append(fileInfo)
        i += 1

    # print the directory content
    print_directory_content(files, directories)


def print_directory_content(files: list, directories: list) -> None:
    # create printed table
    table = PrettyTable()

    table.field_names = ["", "Name", "Updated At", "Size"]

    # print content
    for directoryName, updatedAt in directories:
        table.add_row(["dir", directoryName, time.ctime(updatedAt), ""])
    for fileName, updatedAt, fileSize in files:
        table.add_row(["", fileName, time.ctime(updatedAt), fileSize])

    print(table)


def print_help():
    print("client is CLI client for custom app like \"FTP\" based on UDP.")
    print("  client --help                               - print the help content")
    print("  client upload [--dest <destination>] <file> - upload file")
    print("  client download <remote file> [destination] - download file")
    print("  client list [remote directory]              - print directory content")


def main() -> None:
    init_app()

    if len(sys.argv) < 2 or "--help" in sys.argv[1]:
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

        create_socket()
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

        create_socket()
        download_file(filePath, destination)

    elif sys.argv[1] == "list":
        if len(sys.argv) == 2:
            directoryPath = "."
        else:
            directoryPath = sys.argv[2]

        create_socket()
        send_list_command(directoryPath)
    else:
        print('The command "{}" not exists'.format(sys.argv[1]))


if __name__ == "__main__":
    main()
