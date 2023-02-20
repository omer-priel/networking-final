# entry point to Application

import logging
import socket

from src.lib.config import config, init_config, init_logging
from src.lib.ftp import Pocket, BasicLayer, AuthLayer, PocketType, PocketSubType

appSocket: socket.socket

def main() -> None:
    init_app()
    create_socket()
    main_loop()


def init_app() -> None:
    init_config()
    init_logging()

    logging.info('The app is initialized')

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
                logging.error("The first pocket has to be auth type!")
            else:
                handle_request(reqPocket)
        except socket.error:
            pass

# controllers
def handle_request(reqPocket: Pocket) -> None:
    if reqPocket.basicLayer.pocketSubType == PocketSubType.UploadRequest:
        handle_upload_request(reqPocket)
    elif reqPocket.basicLayer.pocketSubType == PocketSubType.DownloadRequest:
        # TODO handle download
        pass
    elif reqPocket.basicLayer.pocketSubType == PocketSubType.ListRequest:
        # TODO handle list request
        pass


def handle_upload_request(reqPocket: Pocket) -> None:
    # valid pocket
    if not reqPocket.uploadRequestLayer:
        pass

    # check if the path is less the FILE_PATH_MAX_LENGTH

    # split to segments info

    # create and init window

    # send auth respose pocket

    # handle segments

    # send close pocket


if __name__ == "__main__":
    main()
