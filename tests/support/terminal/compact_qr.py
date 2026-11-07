"""Construct literal-field enrollment QR fixtures for an isolated HTTP peer."""

ALPHABET = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ $%*+-./:'


def compact_qr(authority, device_id, token):
    host = authority.encode('ascii')
    identity = device_id.encode('ascii')
    data = b'\0' + len(host).to_bytes(2, 'big') + host + bytes([len(identity)]) + identity + token.encode('ascii')
    text = 'ZMS1:'
    for start in range(0, len(data), 2):
        pair = data[start:start+2]
        value = int.from_bytes(pair, 'big')
        for _ in range(len(pair)+1):
            value, digit = divmod(value, 45)
            text += ALPHABET[digit]
    return text
