# network interface from app and client

from abc import ABC, abstractmethod
import socket

from src.lib.config import config

class NetworkConnection(ABC):
    @abstractmethod
    def init(self, hostAddress: tuple[str, int]) -> None: ...

    @abstractmethod
    def sendto(self, data: bytes, clientAddress: tuple[str, int]) -> None: ...

    @abstractmethod
    def recvfrom(self) -> tuple[bytes, tuple[str, int]]: ...


class UDPConnection(NetworkConnection):
    interfceSocket: socket.socket

    def init(self, hostAddress: tuple[str, int]) -> None:
        self.interfceSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        self.interfceSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.interfceSocket.bind(hostAddress)
        self.interfceSocket.setblocking(True)
        self.interfceSocket.settimeout(config.SOCKET_TIMEOUT)

    def sendto(self, data: bytes, address: tuple[str, int]) -> None:
        return self.interfceSocket.sendto(data, address)

    def recvfrom(self) -> tuple[bytes, tuple[str, int]]:
        return self.interfceSocket.recvfrom(config.SOCKET_MAXSIZE)


class TCPConnection(NetworkConnection):
    recvSocket: socket.socket = ...

    def init(self, hostAddress: tuple[str, int]) -> None:
        self.recvSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.recvSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.recvSocket.bind(hostAddress)
        self.recvSocket.setblocking(True)
        self.recvSocket.settimeout(config.SOCKET_TIMEOUT)

        self.recvSocket.listen(1)

    def sendto(self, data: bytes, address: tuple[str, int]) -> None:
        sendSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        sendSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sendSocket.setblocking(True)
        sendSocket.settimeout(config.SOCKET_TIMEOUT)

        try:
            sendSocket.connect(address)
            sendSocket.sendall(data)
        finally:
            sendSocket.close()

    def recvfrom(self) -> tuple[bytes, tuple[str, int]]:
        error: OSError | None = None
        try:
            conn, address = self.recvSocket.accept()
            data = conn.recv(config.SOCKET_MAXSIZE)
        except socket.error as ex:
            error = ex
        finally:
            conn.close()

        if error:
            raise error

        return (data, address)


def create_network_connection(hostAddress: tuple[str, int]) -> NetworkConnection:
    if config.TCP_MODE:
        tcpConnection = TCPConnection()
        tcpConnection.init(hostAddress)
        return tcpConnection

    udpConnection = UDPConnection()
    udpConnection.init(hostAddress)
    return udpConnection
