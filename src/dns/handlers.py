# DNS handlers

import socket
import logging

from src.dns.config import config
from src.dns.database import Database, RecordData
from src.dns.packets import DNSPacket, DNSQueryRecord, DNSAnswerRecord, str_to_ip

def request_handler(clientsSocket: socket.socket, parentSocket: socket.socket, database: Database, query: DNSPacket, clientAddress: tuple[str, int]) -> None:
    logging.info("Recived query from client")

    print(query)

    locals: list[RecordData | None] = [None] * query.queriesCount

    response: DNSPacket | None = None

    # find all the info from this local DNS
    queriesRecords: list[DNSQueryRecord] = []
    i = 0
    missing = query.queriesCount

    for queryRecord in query.queriesRecords:
        recordData = database.get_active_record(queryRecord.domainName)
        if recordData:
            locals[i] = recordData
            missing -= 1
        else:
            queriesRecords += [queryRecord]

        i += 1

    # find if need from the parent DNS
    if missing > 0:
        nextQuery = DNSPacket(query.transactionID, query.flags, len(queriesRecords), 0, 0, 0)
        nextQuery.queriesRecords = queriesRecords

        logging.info("Send query to parent DNS")

        parentSocket.sendto(bytes(nextQuery), (database.parent_dns, 53))
        try:
            data = parentSocket.recvfrom(config.SOCKET_MAXSIZE)[0]

            response = DNSPacket.from_bytes(data)

            logging.info("Recived response from parent DNS")
            print(response)
        except socket.error:
            pass

    # create the response

    if not response:
        response = DNSPacket(query.transactionID, query.flags, query.queriesCount, 0, 0, 0)

    response.flags.isResponse = True
    response.flags.authoritative = False
    response.flags.recavail = True
    response.flags.authenticated = False
    response.flags.checkdisable = False

    response.queriesCount = query.queriesCount

    for recordData in locals:
        if recordData:
            response.answersRecords += [DNSAnswerRecord(recordData.domain_name, 1, 1, recordData.ttl, str_to_ip(recordData.ip_address))]

    response.answersCount = len(response.answersRecords)

    # send the response

    logging.info("Send response to client")

    print(clientAddress)

    clientsSocket.sendto(bytes(response), clientAddress)
