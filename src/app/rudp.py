# RUDP support

import logging
import socket

from src.app.config import config
from src.lib.ftp import *

lastRequestID = 0


def create_new_requestID() -> int:
    global lastRequestID
    lastRequestID += 1

    return lastRequestID


def create_socket() -> None:
    global appSocket

    appSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    appSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    appSocket.bind((config.APP_HOST, config.APP_PORT))
    appSocket.setblocking(1)
    appSocket.settimeout(config.SOCKET_TIMEOUT)

    logging.info("The app socket initialized on " + config.APP_HOST + ":" + str(config.APP_PORT))


def send_close(clientAddress: tuple[str, int]) -> None:
    closePocket = Pocket(BasicLayer(0, PocketType.Close))
    appSocket.sendto(closePocket.to_bytes(), clientAddress)


def send_error(errorMessage: str, clientAddress: tuple[str, int]) -> None:
    logging.error(errorMessage)
    resPocket = Pocket(BasicLayer(0, PocketType.Response))
    resPocket.responseLayer = ResponseLayer(False, errorMessage, 0, 0, 0)
    appSocket.sendto(resPocket.to_bytes(), clientAddress)
