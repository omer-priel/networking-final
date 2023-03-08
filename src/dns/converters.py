# converters


def unpack_int_from(data: bytes, offset: int, size: int) -> tuple[int, int]:
    return (int.from_bytes(data[offset : offset + size], "big"), offset + size)


def pack_int(number: int, size: bytes) -> bytes:
    return number.to_bytes(size, "big")


def unpack_host_name(data: bytes, offset: int) -> tuple[str, int]:
    domainName = ""
    labelLen = int(data[offset])
    offset += 1

    while labelLen > 0 and offset < len(data):
        if len(domainName) > 0:
            domainName += "."
        domainName += data[offset : offset + labelLen].decode()
        offset += labelLen
        if offset < len(data):
            labelLen = int(data[offset])
            offset += 1

    return (domainName, offset)


def ip_bytes_to_str(data: bytes) -> str:
    return "{}.{}.{}.{}".format(data[0], data[1], data[2], data[3])


def ip_str_to_bytes(address: str) -> bytes:
    return bytes([int(num) for num in address.split(".")])
