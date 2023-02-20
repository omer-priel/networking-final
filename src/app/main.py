# entry point to Application

import logging
import socket

from src.utils import config, init_config, init_logging
from src.utils.ftp import Pocket, BasicLayer, AuthLayer, PocketType, PocketSubType

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

            pocket = Pocket.from_bytes(data)

            logging.debug("get message: " + str(pocket))

            appSocket.sendto(pocket.to_bytes(), clientAddress)
        except socket.error:
            pass



if __name__ == "__main__":
    main()
