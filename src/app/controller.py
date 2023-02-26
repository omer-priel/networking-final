# main controller

import json
import logging
import os
import os.path
import socket
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor

from src.app.handlers import *
from src.app.rudp import *
from src.app.storage import *
from src.lib.ftp import *

# globals
appSocket: socket.socket
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
            data, clientAddress = appSocket.recvfrom(config.SOCKET_MAXSIZE)
        except socket.error:
            data = None

        if data:
            pocket = Pocket.from_bytes(data)

        for key in notReady:
            if data and not key == pocket.basicLayer.requestID:
                appSocket.sendto(notReady[key], handlers[key].get_requestID())

        if data:
            if pocket.basicLayer.pocketType == PocketType.Request:
                result = create_handler(pocket, clientAddress)
                if result:
                    handler, res = result
                    if not handler.uploadHandler:
                        notReady[handler.get_requestID()] = res

                    handlersLock.acquire()
                    handlers[handler.get_requestID()] = handler
                    handlersLock.release()
            elif pocket.basicLayer.requestID in handlers:
                handler = handlers[pocket.basicLayer.requestID]
                if handler.uploadHandler:
                    if not handle_upload_pocket(handler, pocket):
                        handlersLock.acquire()
                        handlers.pop(handler.get_requestID())
                        handlersLock.release()
                else:
                    if not handler.ready:
                        handler.ready = True
                        notReady.pop(handler.get_requestID())

                        def downloading_task(handler: DownloadRequestHandler):
                            global handlers, handlersLock

                            handler.locker.acquire()
                            windowTimeout = handler.response.responseLayer.windowTimeout
                            singleSegmentSize = handler.response.responseLayer.singleSegmentSize
                            segmentsAmount = handler.response.responseLayer.segmentsAmount
                            dataSize = len(handler.data)
                            handler.locker.release()

                            last = time.time()
                            downloading = True

                            while downloading:
                                now = time.time()
                                if last + windowTimeout > now:
                                    # send a segment
                                    if len(handler.windowToSend) == 0:
                                        time.sleep(last + windowTimeout - now)
                                    else:
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
                                        appSocket.sendto(segmentPocket.to_bytes(), clientAddress)
                                else:
                                    # refresh window
                                    logging.debug(
                                        "refresh window {}/{}".format(
                                            segmentsAmount - len(handler.windowToSend) - len(handler.windowSending),
                                            segmentsAmount,
                                        )
                                    )
                                    handler.locker.acquire()
                                    while len(handler.pockets) > 0:
                                        pocket = handler.pockets.pop(0)
                                        if pocket.basicLayer.pocketType == PocketType.DownloadComplited:
                                            # complit the downloading
                                            handler.pockets = []
                                            downloading = False
                                        elif pocket.akcLayer:
                                            if pocket.akcLayer.segmentID in handler.windowToSend:
                                                handler.windowToSend.remove(pocket.akcLayer.segmentID)
                                            if pocket.akcLayer.segmentID in handler.windowSending:
                                                handler.windowSending.remove(pocket.akcLayer.segmentID)
                                            else:
                                                logging.error("Get pocket that not ACK and not download complited")

                                    handler.locker.release()

                                    handler.windowToSend = handler.windowSending + handler.windowToSend
                                    handler.windowSending = []
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

            userData = UserData(id=str(uuid.uuid4()), password=request.requestLayer.password)
            while os.path.isdir(config.APP_STORAGE_PATH + config.STORAGE_PRIVATE + "/" + userData.id):
                userData.id = str(uuid.uuid4())

            os.mkdir(config.APP_STORAGE_PATH + config.STORAGE_PRIVATE + "/" + userData.id)
            storageData.users[request.requestLayer.userName] = userData

            with open(config.APP_STORAGE_PATH + config.STORAGE_DATA, "w") as f:
                f.write(storageData.json())

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

    if handler.uploadHandler:
        dataSize = request.requestLayer.pocketFullSize
    else:
        dataSize = len(data)

    if dataSize == 0:
        res.responseLayer = ResponseLayer(True, "", 0, 0, 0)
        appSocket.sendto(res.to_bytes(), clientAddress)
        return None

    singleSegmentSize = max(config.SINGLE_SEGMENT_SIZE_MIN, request.requestLayer.maxSingleSegmentSize)
    singleSegmentSize = min(config.SINGLE_SEGMENT_SIZE_MAX, singleSegmentSize)

    segmentsAmount = int(dataSize / singleSegmentSize)
    if segmentsAmount * singleSegmentSize < dataSize:
        segmentsAmount += 1

    windowTimeout = max(config.WINDOW_TIMEOUT_MIN, request.requestLayer.maxWindowTimeout)
    windowTimeout = min(config.WINDOW_TIMEOUT_MAX, windowTimeout)

    res.responseLayer = ResponseLayer(True, "", segmentsAmount, singleSegmentSize, windowTimeout)

    if handler.uploadHandler:
        handler.segmentsAmount = segmentsAmount
    else:
        handler.data = data
        handler.windowToSend = list(range(segmentsAmount))
        handler.windowSending = []
        handler.response = res

    appSocket.sendto(res.to_bytes(), clientAddress)
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
        appSocket.sendto(akcPocket.to_bytes(), handler.get_client_address())

        if len(handler.segments) == handler.segmentsAmount:
            # upload all
            data = b""
            for key in sorted(handler.segments):
                data += handler.segments[key]

            send_close(handler.get_client_address())

            handler.post_upload(data)
            return False

    return True
