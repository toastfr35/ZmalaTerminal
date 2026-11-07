"""Local enrollment state and QR validation."""
import base64
import json
from pathlib import Path
from zmala_terminal.common.json_storage import write_json
import re
from urllib.parse import urlsplit
from uuid import UUID


# @llr LLR-TERM-NET-003
def parse_wifi(text):
    """Decode standard escaped WIFI fields or the compact UTF-8 payload emitted by setup-pdf.js."""
    if isinstance(text, str) and text.startswith('FAMILY-WIFI:1:'):
        encoded = text[14:]
        if not encoded or len(encoded) > 160 or not re.fullmatch('[a-zA-Z0-9_-]+', encoded):
            raise ValueError('Invalid Zmala Wi-Fi QR')
        data = base64.urlsafe_b64decode(encoded + '=' * (-len(encoded) % 4))
        if len(data) < 3 or data[0] > 3 or not 1 <= data[1] <= 32 or len(data) < data[1]+2:
            raise ValueError('Invalid Zmala Wi-Fi QR')
        ssid = data[2:2+data[1]].decode('utf-8')
        password = data[2+data[1]:].decode('utf-8')
        escape = lambda value: re.sub(r'([\\;,:\"])', r'\\\1', value)
        return parse_wifi(f"WIFI:T:{'WPA' if data[0]&1 else 'nopass'};S:{escape(ssid)};P:{escape(password)};H:{str(bool(data[0]&2)).lower()};;")
    if not isinstance(text, str) or len(text) > 1024 or not text.startswith('WIFI:'):
        raise ValueError('Not a Wi-Fi QR code')
    fields, part, escaped = {}, '', False
    for char in text[5:]:
        if escaped:
            part += char
            escaped = False
        elif char == '\\':
            escaped = True
        elif char == ';':
            if part:
                key, sep, value = part.partition(':')
                if not sep or key in fields:
                    raise ValueError('Invalid Wi-Fi fields')
                fields[key] = value
            part = ''
        else:
            part += char
    if escaped or part:
        raise ValueError('Incomplete Wi-Fi QR code')
    ssid, password = fields.get('S', ''), fields.get('P', '')
    security = fields.get('T', 'nopass')
    if not ssid or len(ssid.encode('utf-8')) > 32 or any(ord(c) < 32 or ord(c) == 127 for c in ssid):
        raise ValueError('Invalid Wi-Fi name')
    if security not in ('WPA', 'nopass') or fields.get('H', 'false').lower() not in ('true', 'false'):
        raise ValueError('Unsupported Wi-Fi security')
    if security == 'WPA' and not ((8 <= len(password) <= 63 and all(32 <= ord(c) <= 126 for c in password)) or re.fullmatch('[a-fA-F0-9]{64}', password)):
        raise ValueError('Invalid Wi-Fi password')
    if security == 'nopass' and password:
        raise ValueError('Open Wi-Fi must not have a password')
    return dict(ssid=ssid, password=password, security=security, hidden=fields.get('H', 'false').lower() == 'true')


_BASE45 = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ $%*+-./:'


def _decode_base45(text):
    if len(text) % 3 == 1:
        raise ValueError('Invalid compact server QR code')
    data = bytearray()
    for start in range(0, len(text), 3):
        chunk = text[start:start+3]
        value = sum(_BASE45.index(char) * 45**i for i, char in enumerate(chunk))
        if len(chunk) == 3 and value <= 65535:
            data.extend(value.to_bytes(2, 'big'))
        elif len(chunk) == 2 and value <= 255:
            data.append(value)
        else:
            raise ValueError('Invalid compact server QR code')
    return bytes(data)


# @llr LLR-TERM-SETUP-030
def _compact_server_fields(text):
    data = _decode_base45(text)
    if len(data) < 3 or data[0] & ~7:
        raise ValueError('Invalid compact server QR header')
    flags = data[0]
    authority_size = int.from_bytes(data[1:3], 'big')
    offset = 3 + authority_size
    if not authority_size or offset >= len(data):
        raise ValueError('Invalid compact server authority')
    authority = data[3:offset].decode('ascii')
    if any(not 33 <= ord(char) <= 126 or char in '/\\@?#' for char in authority):
        raise ValueError('Invalid compact server authority')
    if flags & 2:
        id_size = 16
    else:
        id_size = data[offset]
        offset += 1
    end = offset + id_size
    if not id_size or end >= len(data):
        raise ValueError('Invalid compact server identity')
    identity = data[offset:end]
    token = data[end:]
    return {
        'server_url': ('https://' if flags & 1 else 'http://') + authority,
        'device_id': 'ZM-' + str(UUID(bytes=identity)) if flags & 2 else identity.decode('ascii'),
        'device_token': base64.urlsafe_b64encode(token).decode('ascii').rstrip('=')
        if flags & 4 else token.decode('ascii'),
    }


# @llr LLR-TERM-SETUP-030
def parse_server(text):
    """Decode a compact server QR into a bounded HTTP(S) origin and credentials."""
    if not isinstance(text, str) or len(text) > 4096 or not text.startswith('ZMS1:'):
        raise ValueError('Invalid server QR code')
    value = _compact_server_fields(text[5:])
    url = value.get('server_url')
    if not isinstance(url, str) or len(url) > 512:
        raise ValueError('Invalid server address')
    parts = urlsplit(url)
    if parts.scheme not in ('http', 'https') or not parts.hostname or parts.username or parts.password or parts.query or parts.fragment or parts.path not in ('', '/'):
        raise ValueError('Invalid server address')
    if parts.port is not None and not 1 <= parts.port <= 65535:
        raise ValueError('Invalid server port')
    if not isinstance(value.get('device_id'), str) or not re.fullmatch('[a-zA-Z0-9_-]{1,80}', value['device_id']):
        raise ValueError('Invalid terminal identity')
    if not isinstance(value.get('device_token'), str) or not re.fullmatch('[a-zA-Z0-9_-]{20,256}', value['device_token']):
        raise ValueError('Invalid terminal key')
    return {key: value[key].rstrip('/') if key == 'server_url' else value[key] for key in ('server_url', 'device_id', 'device_token')}


class Enrollment:
    """A reset marker overrides the legacy bootstrap, including after restarts."""
    def __init__(self, directory, force=False):
        # Persistent filenames stay stable when Python packages move.
        self.path = Path(directory) / 'provisioning.json'
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.value = None
        if self.path.exists():
            try:
                self.value = json.loads(self.path.read_text(encoding='utf-8'))
                if not isinstance(self.value, dict) or self.value.get('version') != 1:
                    raise ValueError('Invalid enrollment state')
            except (ValueError, OSError):
                self.value = {'version': 1}
        if force:
            self.reset()

    def save(self):
        write_json(self.path, self.value)

    def reset(self, wifi=None, language=None):
        wifi = wifi or (self.value or {}).get('wifi_cleanup') or (self.value or {}).get('wifi', {})
        self.value = {'version': 1}
        if language:
            self.value['language'] = language
        cleanup = {key: wifi[key] for key in ('windows_profile', 'linux_profile', 'linux_uuid') if wifi.get(key)}
        if cleanup:
            self.value['wifi_cleanup'] = cleanup
        self.save()

    def cleanup_done(self):
        self.value.pop('wifi_cleanup', None)
        self.save()

    def set_wifi(self, wifi):
        language = (self.value or {}).get('language')
        self.value = {'version': 1, 'wifi': wifi}
        if language:
            self.value['language'] = language
        self.save()

    # @llr LLR-TERM-SETUP-031
    def set_server(self, bootstrap):
        self.value['bootstrap'] = bootstrap
        self.save()

    @property
    def stage(self):
        if self.value is None or self.value.get('bootstrap'):
            return None
        return 'server' if self.value.get('wifi') else 'wifi'
