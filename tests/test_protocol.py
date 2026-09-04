from openscope.protocol import decode_response, encode_command


def test_protocol_round_trip():
    command = encode_command(7, "STATUS")
    assert command.endswith(b"\n")
    assert decode_response('{"v":1,"id":7,"status":"OK","data":{}}')["id"] == 7
