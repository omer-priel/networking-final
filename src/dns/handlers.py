# DNS handlers

import socket


from src.dns.config import config
from src.dns.database import Database, RecordData
from src.dns.packets import DNSPacket, DNSRecord, ip_to_str, str_to_ip

def request_handler(dnsSocket: socket.socket, parentSocket: socket.socket, database: Database, query: DNSPacket, clientAddress: tuple[str, int]) -> None:
    print(query)

    locals: list[RecordData | None] = [None] * query.queriesCount

    response: DNSPacket | None = None

    # find all the info from this local DNS
    i = 0
    missing = query.queriesCount
    for queryRecord in query.queriesRecords:
        recordData = database.get_active_record(queryRecord.domainName)
        if recordData:
            locals[i] = recordData
            missing -= 1

    # find if need from the parent DNS
    if missing > 0:
        queriesRecords: list[DNSRecord] = []
        for i in range(query.queriesCount):
            if not locals[i]:
                queriesRecords += [query.queriesRecords[i]]

        nextQuery = DNSPacket(query.transactionID, query.flags, len(queriesRecords), 0, 0, 0)
        nextQuery.queriesRecords = queriesRecords

        parentSocket.sendto(bytes(nextQuery), (database.parent_dns, 53))
        try:
            data, parentAddress = parentSocket.recvfrom(config.SOCKET_MAXSIZE)

            response = DNSPacket.from_bytes(data)
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

    outside = response.answersRecords
    response.answersRecords = []

    for recordData in locals:
        if recordData:
            response.answersRecords += [DNSRecord(False, recordData.domain_name, 1, 1, recordData.ttl, str_to_ip(recordData.ip_address))]

    response.answersRecords += outside
    response.answersCount = len(response.answersRecords)

    # send the response
    parentSocket.sendto(bytes(response), clientAddress)
