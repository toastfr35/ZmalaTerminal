"""Local physical activation on a combined appliance."""
import json
import subprocess
from pathlib import Path

from zmala_terminal.common.provisioning import validate_bootstrap

ACTIVATION_QR = 'ZMALA:ACTIVATE-SERVER:1'
HELPER = Path('/usr/local/libexec/zmala-activate-server')
ACTIVE = Path('/etc/zmalacall/operator/terminal/server-active')


def activation_available(value):
    return value == ACTIVATION_QR and HELPER.is_file()


# @llr LLR-TERM-CONFIG-025
def activate_server():
    reply = subprocess.run(['sudo', '-n', str(HELPER)], capture_output=True, timeout=30, check=True)
    return validate_bootstrap(json.loads(reply.stdout))
