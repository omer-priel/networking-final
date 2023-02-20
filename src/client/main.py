# entry point to Application

import logging
import socket

from src.lib.config import config, init_config, init_logging
from src.lib.ftp import Pocket, BasicLayer, AuthLayer, PocketType, PocketSubType

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


def upload_file(filename: str, dest: str = "."):
    create_socket()

    appAddress = (config.APP_HOST, config.APP_PORT)

    pocket = Pocket(BasicLayer(10, PocketType.Auth), AuthLayer(100, 101, 102))
    print(pocket.to_bytes())

    clientSocket.sendto(pocket.to_bytes(), appAddress)

    data = clientSocket.recvfrom(config.SOCKET_MAXSIZE)[0]
    pocket = Pocket.from_bytes(data)

    logging.debug("get message: " + str(pocket))

def main() -> None:
    init_app()

    print("Start Client")

    upload_file("uploads/A.md")



if __name__ == "__main__":
    main()
