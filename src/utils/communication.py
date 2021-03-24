from json import dumps, loads
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from socket import socket

LEN_BYTE_LEN = 4
BYTE_ORDER = "big"


def send_msg_with_length(socket: "socket", msg: Any):
    msg_byte = str.encode(dumps(msg))
    data = len(msg_byte).to_bytes(LEN_BYTE_LEN, BYTE_ORDER) + msg_byte
    socket.sendall(data)


def recv_msg_with_length(socket: "socket") -> Any:
    length_byte = socket.recv(LEN_BYTE_LEN)
    length = int.from_bytes(length_byte, BYTE_ORDER)
    received_data = socket.recv(length)
    if len(received_data) == 0:
        return None
    received_msg = loads(received_data)

    return received_msg
