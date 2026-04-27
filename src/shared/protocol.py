import struct

# [Connection ID (4 bytes)] [Payload Size (4 bytes)] [Raw HTTP Data...]
# '!II' means Network Byte Order (Big Endian), followed by two Unsigned Integers
HEADER_FORMAT = '!II'
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)


def pack_message(connection_id, payload):

    payload_size = len(payload)
    header = struct.pack(HEADER_FORMAT, connection_id, payload_size)

    return header + payload

async def read_message(reader):

    header_data = await reader.readexactly(HEADER_SIZE)
    if not header_data:
        return None, None

    connection_id, payload_size = struct.unpack(HEADER_FORMAT, header_data)

    payload = await reader.readexactly(payload_size)

    return connection_id, payload