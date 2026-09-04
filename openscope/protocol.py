import json

PROTOCOL_VERSION = 1


def encode_command(command_id: int, command: str, **fields) -> bytes:
    """Encode one newline-delimited protocol command."""
    payload = {"v": PROTOCOL_VERSION, "id": command_id, "cmd": command, **fields}
    return (json.dumps(payload, separators=(",", ":")) + "\n").encode("utf-8")


def decode_response(line: bytes | str) -> dict:
    """Decode and validate one protocol response."""
    if isinstance(line, bytes):
        line = line.decode("utf-8")
    response = json.loads(line)
    if response.get("v") != PROTOCOL_VERSION:
        raise ValueError("unsupported device protocol version")
    if "id" not in response or "status" not in response:
        raise ValueError("malformed device response")
    return response
