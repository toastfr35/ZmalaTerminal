"""Apply live developer settings only from the enrolled HTTPS server, never cache them."""
import json
import hashlib
from pathlib import Path
import subprocess
from urllib.parse import urlsplit

HELPER = Path('/usr/local/libexec/zmala-developer-access')
SETTINGS = Path('/etc/zmalacall/developer-access.json')
_applied = None


# @llr LLR-TERM-NET-009
def apply(config, bootstrap):
    global _applied
    if not HELPER.exists():
        return
    if config is not None:
        server = urlsplit(bootstrap['server_url'])
        if server.scheme != 'https' or config.get('terminal_id') != bootstrap['device_id']:
            raise ValueError('Developer access requires authenticated HTTPS enrollment')
        if config.get('host') != server.hostname:
            raise ValueError('Developer tunnel must return to the enrolled server')
    try:
        password_operator = json.loads(SETTINGS.read_text()).get('password_operator') is True
    except FileNotFoundError:
        password_operator = False
    request = config
    if password_operator and urlsplit(bootstrap['server_url']).scheme == 'https':
        enrollment = {key: bootstrap[key] for key in ('server_url', 'device_id', 'device_token')}
        request = {'enrollment': enrollment}
    payload = json.dumps(request, sort_keys=True)
    # A new activation or revocation must trigger a fresh approval even
    # though the privileged request carries only the enrollment.
    signature = hashlib.sha256(json.dumps([request, config], sort_keys=True).encode()).digest()
    if signature == _applied:
        return  # systemd owns reconnects; do not spawn sudo on every settings poll.
    result = subprocess.run(['/usr/bin/sudo', '-n', str(HELPER), 'apply'],
                            input=payload, capture_output=True, text=True, timeout=30)
    if result.returncode:
        raise RuntimeError('Developer access could not be applied')
    _applied = signature
