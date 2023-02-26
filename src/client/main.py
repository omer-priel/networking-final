# entry point to Application

import logging
import os
import os.path
import socket
import sys
import time

from prettytable import PrettyTable

from src.lib.config import config, init_logging
from src.lib.ftp import *

clientSocket: socket.socket

MAX_SEGMENT_SIZE = 1000  # [byte]
MAX_WINDOW_TIMEOUT = 1  # [s]

class Options:
    def __init__(self) -> None:
        self.clientAddress: tuple[str, int] = ("localhost", 8001)
        self.appAddress: tuple[str, int] = ("localhost", 8000)
        self.anonymous = True
        self.userName = ""
        self.password = ""


options: Options = Options()

def init_app() -> None:
    config.LOGGING_LEVEL = logging.CRITICAL

    init_logging()

    logging.info("The app is initialized")


def create_socket() -> None:
    global clientSocket

    clientSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    clientSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    clientSocket.bind(options.clientAddress)
    clientSocket.setblocking(1)
    clientSocket.settimeout(config.SOCKET_TIMEOUT)

    print("The client socket initialized on " + options.clientAddress[0] + ":" + str(options.clientAddress[1]))


def upload_file(filename: str, destination: str) -> None:
    # load the file info
    if not os.path.isfile(filename):
        print('The file"' + filename + "\" don't exists!")
        return None

    fileStream = open(filename, "r")

    fileSize = os.stat(filename).st_size

    # create request pocket
    reqPocket = Pocket(BasicLayer(0, PocketType.Request, PocketSubType.Upload))
    reqPocket.requestLayer = RequestLayer(fileSize, MAX_SEGMENT_SIZE, MAX_WINDOW_TIMEOUT, options.anonymous, options.userName, options.password)
    reqPocket.uploadRequestLayer = UploadRequestLayer(destination)

    # send request
    logging.debug("send req pocket: " + str(reqPocket))

    clientSocket.sendto(reqPocket.to_bytes(), options.appAddress)

    # recive response
    data = clientSocket.recvfrom(config.SOCKET_MAXSIZE)[0]
    resPocket = Pocket.from_bytes(data)

    # handle response
    logging.debug("get res pocket: " + str(resPocket))

    if not resPocket.responseLayer:
        print("Error: faild to send the file")
        fileStream.close()
        return None

    if not resPocket.responseLayer.ok:
        print("Error: " + resPocket.responseLayer.errorMessage)
        fileStream.close()
        return None

    # send the file
    requestID = resPocket.basicLayer.requestID

    singleSegmentSize = resPocket.responseLayer.singleSegmentSize
    segmentsAmount = resPocket.responseLayer.segmentsAmount
    windowTimeout = resPocket.responseLayer.windowTimeout

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

                segmentPocket = Pocket(BasicLayer(requestID, PocketType.Segment))
                segmentPocket.segmentLayer = SegmentLayer(segmentID, segment.encode())

                windowSending.append(segmentID)

                clientSocket.sendto(segmentPocket.to_bytes(), options.appAddress)
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
    reqPocket = Pocket(BasicLayer(0, PocketType.Request, PocketSubType.Download))
    reqPocket.requestLayer = RequestLayer(0, MAX_SEGMENT_SIZE, MAX_WINDOW_TIMEOUT, options.anonymous, options.userName, options.password)
    reqPocket.downloadRequestLayer = DownloadRequestLayer(filePath)

    logging.debug("send req pocket: " + str(reqPocket))

    clientSocket.sendto(reqPocket.to_bytes(), options.appAddress)

    # recive download response
    data = clientSocket.recvfrom(config.SOCKET_MAXSIZE)[0]
    resPocket = Pocket.from_bytes(data)

    # handel response
    logging.debug("get res pocket: " + str(resPocket))

    if not resPocket.responseLayer:
        print("Error: faild to download the file")
        return None

    if not resPocket.responseLayer.ok:
        print("Error: " + resPocket.responseLayer.errorMessage)
        return None

    # init segments for downloading
    requestID = resPocket.basicLayer.requestID

    segmentsAmount = resPocket.responseLayer.segmentsAmount

    neededSegments = list(range(segmentsAmount))
    segments = [b""] * segmentsAmount

    # send ack for start downloading
    readyPocket = Pocket(BasicLayer(requestID, PocketType.ReadyForDownloading))
    readyPocket.akcLayer = AKCLayer(0)

    logging.debug("send ready ack pocket: " + str(readyPocket))

    # send ready pockets until segment comes
    itFirstSegment = False

    while not itFirstSegment:
        clientSocket.sendto(readyPocket.to_bytes(), options.appAddress)

        try:
            data = clientSocket.recvfrom(config.SOCKET_MAXSIZE)[0]
            segmentPocket = Pocket.from_bytes(data)
            itFirstSegment = segmentPocket.basicLayer.pocketType == PocketType.Segment
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
                not segmentPocket.basicLayer.pocketType == PocketType.Segment
            ):
                logging.error("Get pocket that is not download segment")
            else:
                segmentID = segmentPocket.segmentLayer.segmentID
                if segmentID in neededSegments:
                    # add new segment
                    neededSegments.remove(segmentID)
                    segments[segmentID] = segmentPocket.segmentLayer.data

                akcPocket = Pocket(BasicLayer(requestID, PocketType.ACK))
                akcPocket.akcLayer = AKCLayer(segmentID)
                clientSocket.sendto(akcPocket.to_bytes(), options.appAddress)
        except socket.error:
            pass

    # send complited download pocket to knowning the app that the file complited
    # until recive close pocket
    complitedPocket = Pocket(BasicLayer(requestID, PocketType.DownloadComplited))

    closed = False

    while not closed:
        clientSocket.sendto(complitedPocket.to_bytes(), options.appAddress)

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
    reqPocket = Pocket(BasicLayer(0, PocketType.Request, PocketSubType.List))
    reqPocket.requestLayer = RequestLayer(0, MAX_SEGMENT_SIZE, MAX_WINDOW_TIMEOUT, options.anonymous, options.userName, options.password)
    reqPocket.listRequestLayer = ListRequestLayer(directoryPath)

    logging.debug("send req pocket: " + str(reqPocket))

    clientSocket.sendto(reqPocket.to_bytes(), options.appAddress)

    # recive list response
    data = clientSocket.recvfrom(config.SOCKET_MAXSIZE)[0]
    resPocket = Pocket.from_bytes(data)

    # handle response
    logging.debug("get res pocket: " + str(resPocket))

    if not resPocket.responseLayer:
        print("Error: the list request faild")
        return None

    if not resPocket.responseLayer.ok:
        print("Error: " + resPocket.responseLayer.errorMessage)
        return None

    if resPocket.listResponseLayer.directoriesCount == 0 and resPocket.listResponseLayer.filesCount == 0:
        print("The directory is empty")
        return None

    # init segments for downloading
    requestID = resPocket.basicLayer.requestID

    segmentsAmount = resPocket.responseLayer.segmentsAmount

    neededSegments = list(range(segmentsAmount))
    segments = [b""] * segmentsAmount

    # send ack for start downloading
    readyPocket = Pocket(BasicLayer(requestID, PocketType.ReadyForDownloading))

    logging.debug("send ready ack pocket: " + str(readyPocket))

    # send ready pockets until segment comes
    itFirstSegment = False

    while not itFirstSegment:
        clientSocket.sendto(readyPocket.to_bytes(), options.appAddress)

        try:
            data = clientSocket.recvfrom(config.SOCKET_MAXSIZE)[0]
            segmentPocket = Pocket.from_bytes(data)
            itFirstSegment = segmentPocket.basicLayer.pocketType == PocketType.Segment
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

            if (not segmentPocket.segmentLayer) or (not segmentPocket.basicLayer.pocketType == PocketType.Segment):
                logging.error("Get pocket that is not list segment")
            else:
                segmentID = segmentPocket.segmentLayer.segmentID
                if segmentID in neededSegments:
                    # add new segment
                    neededSegments.remove(segmentID)
                    segments[segmentID] = segmentPocket.segmentLayer.data

                akcPocket = Pocket(BasicLayer(requestID, PocketType.ACK))
                akcPocket.akcLayer = AKCLayer(segmentID)
                clientSocket.sendto(akcPocket.to_bytes(), options.appAddress)
        except socket.error:
            pass

    # send complited list pocket to knowning the app that the list download complited
    # until recive close pocket
    complitedPocket = Pocket(BasicLayer(requestID, PocketType.DownloadComplited))
    complitedPocket.akcLayer = AKCLayer(0)

    closed = False

    while not closed:
        clientSocket.sendto(complitedPocket.to_bytes(), options.appAddress)

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
    print("  client [options] upload [--dest <destination>] <file> - upload file")
    print("  client [options] download <remote file> [destination] - download file")
    print("  client [options] list [remote directory]              - print directory content")
    print("Options:")
    print("--user <user name>    - set user name")
    print("--password <password> - set user password, require --user")
    print("--host <host> - set the server host address, defualt: localhost")
    print("--port <port> - set the server port, defualt: 8000")
    print("--client-host <host> - set the client host address, defualt: localhost")
    print("--client-port <port> - set the client port, defualt: 8001")

def main() -> None:
    global options

    init_app()

    if len(sys.argv) < 2 or "--help" in sys.argv:
        print_help()
        return None

    i = 1

    while i < len(sys.argv) and sys.argv[i].startswith("--"):
        if sys.argv[i] == "--user":
            if i + 1 == len(sys.argv):
                print("User Name is missing")
                return None
            else:
                options.userName = sys.argv[i + 1]
                options.anonymous = False
            i += 2
        elif sys.argv[i] == "--password":
            if i + 1 == len(sys.argv):
                print("Password is missing")
                return None
            else:
                options.password = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--host":
            if i + 1 == len(sys.argv):
                print("Host address is missing")
                return None
            else:
                options.appAddress = (sys.argv[i + 1], options.appAddress[1])
            i += 2
        elif sys.argv[i] == "--port":
            if i + 1 == len(sys.argv):
                print("Port address is missing")
                return None
            else:
                options.appAddress = (options.appAddress[0], int(sys.argv[i + 1]))
            i += 2
        elif sys.argv[i] == "--client-host":
            if i + 1 == len(sys.argv):
                print("Host address is missing")
                return None
            else:
                options.clientAddress = (sys.argv[i + 1], options.clientAddress[1])
            i += 2
        elif sys.argv[i] == "--client-port":
            if i + 1 == len(sys.argv):
                print("Port address is missing")
                return None
            else:
                options.clientAddress = (options.clientAddress[0], int(sys.argv[i + 1]))
            i += 2
        else:
            print("The option {} dose not exists!".format(sys.argv[i]))
            return None

    if options.password != "" and options.userName == "":
        print("The --password need User Name!")
        return None

    if i == len(sys.argv):
        print("Not found any command")
        return None

    if sys.argv[i] == "upload":
        filename = None
        destination = None

        i += 1
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
    elif sys.argv[i] == "download":
        if len(sys.argv) == i + 1:
            print("File path and destination path are Missing!")
            return None
        if len(sys.argv) == i + 2:
            print("Destination path are Missing!")
            return None

        filePath = sys.argv[i + 1]
        destination = sys.argv[i + 2]

        create_socket()
        download_file(filePath, destination)

    elif sys.argv[i] == "list":
        if len(sys.argv) == i + 1:
            directoryPath = "."
        else:
            directoryPath = sys.argv[i + 1]

        create_socket()
        send_list_command(directoryPath)
    else:
        print('The command "{}" not exists'.format(sys.argv[i]))


if __name__ == "__main__":
    main()
