# main controller

import json
import logging
import os
import os.path
import socket
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

import jsbeautifier  # type: ignore

from src.app.config import config
from src.app.handlers import (
    DownloadFileRequestHandler,
    DownloadRequestHandler,
    ListRequestHandler,
    RequestHandler,
    UploadFileRequestHandler,
    UploadRequestHandler,
)
from src.app.rudp import recvfrom, send_close, send_error, sendto
from src.app.storage import StorageData, UserData
from src.lib.ftp import AKCLayer, BasicLayer, Pocket, PocketSubType, PocketType, ResponseLayer, SegmentLayer

# globals
executor = ThreadPoolExecutor(2)

# dict of handlers for the requests
handlers: dict[int, RequestHandler] = {}
handlersLock = threading.Lock()


def main_loop() -> None:
    global handlers, handlersLock

    # dict of responses for unready requests
    notReady: dict[int, Pocket] = {}
    while True:
        try:
            data, clientAddress = recvfrom()
        except socket.error:
            data = None

        if data:
            pocket = Pocket.from_bytes(data)

        for key in notReady:
            if data and not key == pocket.basicLayer.requestID:
                sendto(notReady[key], handlers[key].get_client_address())

        if data:
            if pocket.basicLayer.pocketType == PocketType.Request:
                result = create_handler(pocket, clientAddress)
                if result:
                    handler, res = result
                    if isinstance(handler, DownloadRequestHandler):
                        notReady[handler.get_requestID()] = res

                    handlersLock.acquire()
                    handlers[handler.get_requestID()] = handler
                    handlersLock.release()
            elif pocket.basicLayer.requestID in handlers:
                handler = handlers[pocket.basicLayer.requestID]
                if isinstance(handler, UploadRequestHandler):
                    if not handle_upload_pocket(handler, pocket):
                        handlersLock.acquire()
                        handlers.pop(handler.get_requestID())
                        handlersLock.release()
                elif isinstance(handler, DownloadRequestHandler):
                    if not handler.ready:
                        handler.ready = True
                        notReady.pop(handler.get_requestID())

                        def downloading_task(handler: DownloadRequestHandler) -> None:
                            global handlers, handlersLock

                            handler.locker.acquire()
                            assert handler.response.responseLayer
                            singleSegmentSize = handler.response.responseLayer.singleSegmentSize
                            segmentsAmount = handler.response.responseLayer.segmentsAmount
                            dataSize = len(handler.data)
                            handler.locker.release()

                            rtt = config.SOCKET_TIMEOUT
                            cwnd = cwndMax = config.CWND_START_VALUE
                            C, B = 0.4, 0.7

                            last = time.time()
                            downloading = True

                            while downloading:
                                now = time.time()
                                if (
                                    last + rtt > now
                                    and len(handler.windowToSend) > 0
                                    and len(handler.windowSending) < cwnd
                                ):
                                    # send a segment
                                    segmentID = handler.windowToSend.pop(0)
                                    if segmentID * singleSegmentSize <= dataSize - singleSegmentSize:
                                        # is not the last segment
                                        segment = handler.data[
                                            segmentID * singleSegmentSize : (segmentID + 1) * singleSegmentSize
                                        ]
                                    else:
                                        # is the last segment
                                        segment = handler.data[segmentID * singleSegmentSize :]

                                    segmentPocket = Pocket(BasicLayer(handler.get_requestID(), PocketType.Segment))
                                    segmentPocket.segmentLayer = SegmentLayer(segmentID, segment)

                                    handler.windowSending.append(segmentID)
                                    sendto(segmentPocket, clientAddress)
                                else:
                                    # refresh window
                                    logging.debug(
                                        "refresh window {}/{}".format(
                                            segmentsAmount - len(handler.windowToSend) - len(handler.windowSending),
                                            segmentsAmount,
                                        )
                                    )
                                    timeout = False
                                    while not timeout:
                                        if len(handler.pockets) > 0:
                                            handler.locker.acquire()
                                            pocket = handler.pockets.pop(0)
                                            handler.locker.release()
                                        else:
                                            pocket = None
                                            now = time.time()
                                            timeout = last + rtt < now

                                        if pocket:
                                            if pocket.basicLayer.pocketType == PocketType.DownloadComplited:
                                                # complit the downloading
                                                handler.pockets = []
                                                downloading = False
                                            elif pocket.akcLayer:
                                                if pocket.akcLayer.segmentID in handler.windowToSend:
                                                    handler.windowToSend.remove(pocket.akcLayer.segmentID)
                                                if pocket.akcLayer.segmentID in handler.windowSending:
                                                    handler.windowSending.remove(pocket.akcLayer.segmentID)

                                    if len(handler.windowSending) > 0:
                                        handler.windowToSend = handler.windowSending + handler.windowToSend
                                        handler.windowSending = []
                                        cwndMax = cwnd
                                        cwnd = int(max(cwnd / 2, 1))
                                    else:
                                        cwnd = int(
                                            max(C * ((rtt - (cwndMax * (1 - B) / C) ** (1 / 3)) ** 3) + cwndMax, 1)
                                        )

                                    rtt = time.time() - last
                                    last = time.time()

                            send_close(handler.get_client_address())

                            handlersLock.acquire()
                            handlers.pop(handler.get_requestID())
                            handlersLock.release()

                        executor.submit(downloading_task, handler)
                    else:
                        handler.locker.acquire()
                        handler.pockets += [pocket]
                        handler.locker.release()

            else:
                send_close(clientAddress)


def create_handler(request: Pocket, clientAddress: tuple[str, int]) -> tuple[RequestHandler, Pocket] | None:
    storagePath = config.APP_STORAGE_PATH + config.STORAGE_PUBLIC + "/"

    assert request.requestLayer

    if not request.requestLayer.anonymous:
        # valid user
        if request.requestLayer.userName == "":
            send_error("The user name cannot be empty", clientAddress)
            return None

        with open(config.APP_STORAGE_PATH + config.STORAGE_DATA, "r") as f:
            storageData = StorageData(**json.load(f))

        # check if the user not exists
        userData = storageData.users.get(request.requestLayer.userName)

        if userData:
            if not userData.password == request.requestLayer.password:
                send_error("the password is incorrect", clientAddress)
                return None
        else:
            userData = UserData(id=str(uuid.uuid4()), password=request.requestLayer.password)
            while os.path.isdir(config.APP_STORAGE_PATH + config.STORAGE_PRIVATE + "/" + userData.id):
                userData.id = str(uuid.uuid4())

            os.mkdir(config.APP_STORAGE_PATH + config.STORAGE_PRIVATE + "/" + userData.id)
            storageData.users[request.requestLayer.userName] = userData

            with open(config.APP_STORAGE_PATH + config.STORAGE_DATA, "w") as f:
                opts = jsbeautifier.default_options()
                opts.indent_size = 2
                f.write(jsbeautifier.beautify(storageData.json(), opts))

        storagePath = config.APP_STORAGE_PATH + config.STORAGE_PRIVATE + "/" + userData.id + "/"

    handler: RequestHandler

    if request.basicLayer.pocketSubType == PocketSubType.Upload:
        handler = UploadFileRequestHandler(request, clientAddress, storagePath)
    elif request.basicLayer.pocketSubType == PocketSubType.Download:
        handler = DownloadFileRequestHandler(request, clientAddress, storagePath)
    elif request.basicLayer.pocketSubType == PocketSubType.List:
        handler = ListRequestHandler(request, clientAddress, storagePath)

    result = handler.route()
    if not result:
        return None

    res, data = result

    dataSize = 0
    if isinstance(handler, UploadRequestHandler):
        dataSize = request.requestLayer.pocketFullSize
    elif data:
        dataSize = len(data)

    if dataSize == 0:
        res.responseLayer = ResponseLayer(True, "", 0, 0, 0)
        sendto(res, clientAddress)

        if isinstance(handler, UploadRequestHandler):
            handler.post_upload(b"")

        return None

    singleSegmentSize = max(config.SINGLE_SEGMENT_SIZE_MIN, request.requestLayer.maxSingleSegmentSize)
    singleSegmentSize = min(config.SINGLE_SEGMENT_SIZE_MAX, singleSegmentSize)

    segmentsAmount = int(dataSize / singleSegmentSize)
    if segmentsAmount * singleSegmentSize < dataSize:
        segmentsAmount += 1

    res.responseLayer = ResponseLayer(True, "", dataSize, segmentsAmount, singleSegmentSize)

    if isinstance(handler, UploadRequestHandler):
        handler.segmentsAmount = segmentsAmount
    elif isinstance(handler, DownloadRequestHandler):
        assert data is not None
        handler.data = data
        handler.windowToSend = list(range(segmentsAmount))
        handler.windowSending = []
        handler.response = res

    sendto(res, clientAddress)
    return (handler, res)


def handle_upload_pocket(handler: UploadRequestHandler, pocket: Pocket) -> bool:
    if (not pocket.segmentLayer) or (not pocket.basicLayer.pocketType == PocketType.Segment):
        logging.error("Get pocket that is not upload segment")
    else:
        segmentID = pocket.segmentLayer.segmentID
        if segmentID not in handler.segments:
            # add new segment
            handler.segments[segmentID] = pocket.segmentLayer.data

        akcPocket = Pocket(BasicLayer(handler.get_requestID(), PocketType.ACK))
        akcPocket.akcLayer = AKCLayer(segmentID)
        sendto(akcPocket, handler.get_client_address())

        if len(handler.segments) == handler.segmentsAmount:
            # upload all
            data = b""
            for key in sorted(handler.segments):
                data += handler.segments[key]

            send_close(handler.get_client_address())

            handler.post_upload(data)
            return False

    return True
