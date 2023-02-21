# entry point to Application

import os
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
        return None

    if not resPocket.uploadResponseLayer.ok:
        print("Error: " + resPocket.uploadResponseLayer.errorMessage)
        return None

    # send the file
    # TODO

def main() -> None:
    init_app()

    print("Start Client")

    upload_file("uploads/A.md", "A.md")



if __name__ == "__main__":
    main()
