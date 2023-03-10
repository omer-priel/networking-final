# commands

import logging
import os
import os.path
import shutil
import struct
import time
import zipfile
from io import BytesIO

from prettytable import PrettyTable

from src.client.options import Options
from src.client.rudp import download_data, upload_data
from src.lib.ftp import (
    BasicLayer,
    DeleteRequestLayer,
    DownloadRequestLayer,
    ListRequestLayer,
    Pocket,
    PocketSubType,
    PocketType,
    RequestLayer,
    UploadRequestLayer,
    unpack_block_type,
    unpack_directory_block,
    unpack_file_block,
)
from src.lib.network import NetworkConnection

# config
MAX_SEGMENT_SIZE = 1000  # [byte]


def upload_command(networkConnection: NetworkConnection, options: Options, targetName: str, destination: str) -> None:
    # load the file info
    isFile = True
    if not os.path.isfile(targetName):
        if os.path.isdir(targetName):
            isFile = False
        else:
            print('Not found the "' + targetName + '"!')
            return None

    if isFile:
        with open(targetName, "rb") as f:
            body = f.read()
    else:
        archive = BytesIO()
        with zipfile.ZipFile(archive, "w") as zip_archive:
            for root, dirs, files in os.walk(targetName):
                for file in files:
                    fileInfo = zipfile.ZipInfo(os.path.relpath(os.path.join(root, file), os.path.join(targetName, ".")))
                    with open(os.path.join(root, file), "rb") as f:
                        zip_archive.writestr(fileInfo, f.read())

        archive.seek(0)
        body = archive.read()

    body = struct.pack("?", isFile) + body

    bodySize = len(body)
    # create request pocket
    reqPocket = Pocket(BasicLayer(0, PocketType.Request, PocketSubType.Upload))
    reqPocket.requestLayer = RequestLayer(
        bodySize, MAX_SEGMENT_SIZE, options.anonymous, options.userName, options.password
    )
    reqPocket.uploadRequestLayer = UploadRequestLayer(destination)

    # send request
    logging.debug("send req pocket: " + str(reqPocket))

    networkConnection.sendto(bytes(reqPocket), options.appAddress)

    # recive response
    try:
        data = networkConnection.recvfrom()[0]
    except OSError:
        if isFile:
            print("Error: faild to upload the file")
        else:
            print("Error: faild to upload the directory")
        return None

    resPocket = Pocket.from_bytes(data)

    # handle response
    logging.debug("get res pocket: " + str(resPocket))

    if not resPocket.responseLayer:
        if isFile:
            print("Error: faild to upload the file")
        else:
            print("Error: faild to upload the directory")
        return None

    if not resPocket.responseLayer.ok:
        print("Error: " + resPocket.responseLayer.errorMessage)
        return None

    # send the file / directory
    upload_data(networkConnection, options, resPocket, body)

    # print ending
    if isFile:
        print('The file "{}" upload as "{}" to the app.'.format(targetName, destination))
    else:
        print('The directory "{}" upload as "{}" to the app.'.format(targetName, destination))


def download_command(networkConnection: NetworkConnection, options: Options, targetName: str, destination: str) -> None:
    # check if the directory of destination exists
    if os.path.isfile(destination):
        os.remove(destination)
    if os.path.isdir(destination):
        shutil.rmtree(destination)

    if not os.path.isdir(os.path.dirname(destination)):
        os.mkdir(os.path.dirname(destination))

    # send download request
    reqPocket = Pocket(BasicLayer(0, PocketType.Request, PocketSubType.Download))
    reqPocket.requestLayer = RequestLayer(0, MAX_SEGMENT_SIZE, options.anonymous, options.userName, options.password)
    reqPocket.downloadRequestLayer = DownloadRequestLayer(targetName)

    logging.debug("send req pocket: " + str(reqPocket))

    networkConnection.sendto(bytes(reqPocket), options.appAddress)

    # recive download response
    data = networkConnection.recvfrom()[0]
    resPocket = Pocket.from_bytes(data)

    # handel response
    logging.debug("get res pocket: " + str(resPocket))

    if not resPocket.responseLayer:
        print("Error: faild to download the file")
        return None

    if not resPocket.responseLayer.ok:
        print("Error: " + resPocket.responseLayer.errorMessage)
        return None

    data = download_data(networkConnection, options, resPocket)

    isFile = struct.unpack_from("?", data)[0]
    data = data[struct.calcsize("?") :]

    if isFile:
        # create the file
        with open(destination, "ab") as f:
            f.write(data)

        logging.info('The file "{}" downloaded to "{}".'.format(targetName, destination))
    else:
        # create the directory
        zipFile = BytesIO(data)
        with zipfile.ZipFile(zipFile, "r") as zip_archive:
            zip_archive.extractall(destination)

        logging.info('The directory "{}" downloaded to "{}".'.format(targetName, destination))


def delete_command(networkConnection: NetworkConnection, options: Options, targetName: str) -> None:
    # send the delete request
    reqPocket = Pocket(BasicLayer(0, PocketType.Request, PocketSubType.Delete))
    reqPocket.requestLayer = RequestLayer(0, MAX_SEGMENT_SIZE, options.anonymous, options.userName, options.password)
    reqPocket.deleteRequestLayer = DeleteRequestLayer(targetName)

    logging.debug("send req pocket: " + str(reqPocket))

    networkConnection.sendto(bytes(reqPocket), options.appAddress)

    # recive delete response
    data = networkConnection.recvfrom()[0]
    resPocket = Pocket.from_bytes(data)

    # handel response
    logging.debug("get res pocket: " + str(resPocket))

    if not resPocket.responseLayer:
        print("Error: faild to delete the file")
        return None

    if not resPocket.responseLayer.ok:
        print("Error: " + resPocket.responseLayer.errorMessage)
        return None

    if not resPocket.deleteResponseLayer:
        print("Error: faild to delete the file")
        return None

    if resPocket.deleteResponseLayer.isFile:
        print('The file "{}" deleted.'.format(targetName))
    else:
        print('The directory "{}" deleted.'.format(targetName))


def list_command(networkConnection: NetworkConnection, options: Options, directoryPath: str, recursive: bool) -> None:
    # send list request
    reqPocket = Pocket(BasicLayer(0, PocketType.Request, PocketSubType.List))
    reqPocket.requestLayer = RequestLayer(0, MAX_SEGMENT_SIZE, options.anonymous, options.userName, options.password)
    reqPocket.listRequestLayer = ListRequestLayer(directoryPath, recursive)

    logging.debug("send req pocket: " + str(reqPocket))

    networkConnection.sendto(bytes(reqPocket), options.appAddress)

    # recive list response
    data = networkConnection.recvfrom()[0]
    resPocket = Pocket.from_bytes(data)

    # handle response
    logging.debug("get res pocket: " + str(resPocket))

    if not resPocket.responseLayer:
        print("Error: the list request faild")
        return None

    if not resPocket.responseLayer.ok:
        print("Error: " + resPocket.responseLayer.errorMessage)
        return None

    if resPocket.responseLayer.dataSize == 0:
        print_directory_content(b"")
        return None

    data = download_data(networkConnection, options, resPocket)

    # print the directory content
    print_directory_content(data)


def print_directory_content(data: bytes) -> None:
    # create printed table
    table = PrettyTable()

    table.field_names = ["", "Name", "Updated At", "Size"]
    table.align["Name"] = "l"

    # print content
    offset = 0
    while offset < len(data):
        isDirectory, offset = unpack_block_type(data, offset)
        if isDirectory:
            (directoryName, updatedAt), offset = unpack_directory_block(data, offset)
            table.add_row(["dir", directoryName, time.ctime(updatedAt), ""])
        else:
            (fileName, updatedAt, fileSize), offset = unpack_file_block(data, offset)
            table.add_row(["", fileName, time.ctime(updatedAt), fileSize])

    print(table)
