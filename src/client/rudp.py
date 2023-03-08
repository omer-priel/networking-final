# rudp

import logging
import time

from src.client.options import Options
from src.lib.config import config
from src.lib.ftp import AKCLayer, BasicLayer, Pocket, PocketType, SegmentLayer
from src.lib.network import NetworkConnection


def upload_data(networkConnection: NetworkConnection, options: Options, resPocket: Pocket, body: bytes) -> None:
    bodySize = len(body)

    requestID = resPocket.basicLayer.requestID

    assert resPocket.responseLayer
    singleSegmentSize = resPocket.responseLayer.singleSegmentSize
    segmentsAmount = resPocket.responseLayer.segmentsAmount

    windowToSend = list(range(segmentsAmount))
    windowSending: list[int] = []

    rtt = config.SOCKET_TIMEOUT
    cwnd = cwndMax = config.CWND_START_VALUE
    C, B = 0.4, 0.7

    last = time.time()

    uploading = True

    while uploading:
        now = time.time()
        if last + rtt > now and len(windowToSend) > 0 and len(windowSending) < cwnd:
            segmentID = windowToSend.pop(0)
            if segmentID * singleSegmentSize <= bodySize - singleSegmentSize:
                # is not the last segment
                segment = body[segmentID * singleSegmentSize : (segmentID + 1) * singleSegmentSize]
            else:
                # is the last segment
                segment = body[segmentID * singleSegmentSize :]

            segmentPocket = Pocket(BasicLayer(requestID, PocketType.Segment))
            segmentPocket.segmentLayer = SegmentLayer(segmentID, segment)

            windowSending.append(segmentID)

            networkConnection.sendto(bytes(segmentPocket), options.appAddress)
        else:
            # refresh window
            logging.debug(
                "refresh window {}/{}".format(segmentsAmount - len(windowToSend) - len(windowSending), segmentsAmount)
            )
            timeout = False
            while not timeout:
                try:
                    data = networkConnection.recvfrom()[0]
                except TimeoutError:
                    now = time.time()
                    timeout = last + rtt < now

                if not timeout:
                    pocket = Pocket.from_bytes(data)
                    if pocket.basicLayer.pocketType == PocketType.Close:
                        # complit the upload
                        timeout = True
                        uploading = False
                    elif pocket.akcLayer:
                        if pocket.akcLayer.segmentID in windowToSend:
                            windowToSend.remove(pocket.akcLayer.segmentID)
                        if pocket.akcLayer.segmentID in windowSending:
                            windowSending.remove(pocket.akcLayer.segmentID)

            if len(windowSending) > 0:
                windowToSend = windowSending + windowToSend
                windowSending = []
                cwndMax = cwnd
                cwnd = int(max(cwnd / 2, 1))
            else:
                cwnd = int(max(C * ((rtt - (cwndMax * (1 - B) / C) ** (1 / 3)) ** 3) + cwndMax, 1))

            rtt = time.time() - last
            last = time.time()


def download_data(networkConnection: NetworkConnection, options: Options, resPocket: Pocket) -> bytes:
    # init segments for downloading
    requestID = resPocket.basicLayer.requestID

    assert resPocket.responseLayer
    segmentsAmount = resPocket.responseLayer.segmentsAmount

    neededSegments = list(range(segmentsAmount))
    segments = [b""] * segmentsAmount

    # send ack for start downloading
    readyPocket = Pocket(BasicLayer(requestID, PocketType.ReadyForDownloading))
    readyPocket.akcLayer = AKCLayer(0)

    logging.debug("send ready ack pocket: " + str(readyPocket))

    # send ready pockets until segment comes
    itFirstSegment = False

    while not itFirstSegment:
        networkConnection.sendto(bytes(readyPocket), options.appAddress)

        try:
            data = networkConnection.recvfrom()[0]
            segmentPocket = Pocket.from_bytes(data)
            itFirstSegment = segmentPocket.basicLayer.pocketType == PocketType.Segment
        except OSError:
            pass

    # handle segments
    while len(neededSegments) > 0:
        try:
            if itFirstSegment:
                itFirstSegment = False
            else:
                data = networkConnection.recvfrom()[0]
                segmentPocket = Pocket.from_bytes(data)

            if (not segmentPocket.segmentLayer) or (not segmentPocket.basicLayer.pocketType == PocketType.Segment):
                logging.error("Get pocket that is not download segment")
            else:
                segmentID = segmentPocket.segmentLayer.segmentID
                if segmentID in neededSegments:
                    # add new segment
                    neededSegments.remove(segmentID)
                    segments[segmentID] = segmentPocket.segmentLayer.data

                akcPocket = Pocket(BasicLayer(requestID, PocketType.ACK))
                akcPocket.akcLayer = AKCLayer(segmentID)
                networkConnection.sendto(bytes(akcPocket), options.appAddress)
        except OSError:
            pass

    # send complited download pocket to knowning the app that the file complited
    # until recive close pocket
    complitedPocket = Pocket(BasicLayer(requestID, PocketType.DownloadComplited))

    closed = False

    while not closed:
        networkConnection.sendto(bytes(complitedPocket), options.appAddress)

        try:
            data = networkConnection.recvfrom()[0]
            closePocket = Pocket.from_bytes(data)
            closed = closePocket.basicLayer.pocketType == PocketType.Close
        except OSError:
            pass

    # load body
    data = b""
    for segment in segments:
        data += segment

    return data
