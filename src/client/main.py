# entry point to Application

import logging
import socket

from src.utils import config, init_config, init_logging
from src.utils.ftp import BasicLayer, PocketType, PocketSubType

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


def main() -> None:
    init_app()
    print("Start Client")

    create_socket()

    appAddress = (config.APP_HOST, config.APP_PORT)

    pocket = BasicLayer(PocketType.Auth, PocketSubType.UploadFileRequest, 100)
    print(pocket.to_bytes())

    clientSocket.sendto(pocket.to_bytes(), appAddress)


if __name__ == "__main__":
    main()
