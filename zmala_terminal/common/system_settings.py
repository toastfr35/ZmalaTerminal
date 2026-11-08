"""Local host information and explicitly selected power requests."""
import ipaddress
import json
import logging
import platform
import socket
import subprocess
import sys


def local_ip():
    """Prefer a usable IPv4 address, with IPv6 available on IPv6-only networks."""
    try:
        if sys.platform == 'linux':
            interfaces = json.loads(subprocess.check_output(
                ['ip', '-j', 'address', 'show', 'up', 'scope', 'global'], timeout=2))
            values = (row['local'] for interface in interfaces for row in interface['addr_info'])
        else:
            values = (row[4][0] for row in socket.getaddrinfo(socket.gethostname(), None))
        addresses = sorted(map(ipaddress.ip_address, values), key=lambda address: address.version)
        return next((str(address) for address in addresses
                     if not (address.is_loopback or address.is_link_local or address.is_unspecified)), None)
    except (OSError, ValueError, KeyError, subprocess.SubprocessError):
        return None


# @llr LLR-TERM-CONFIG-020
def host_information():
    if sys.platform == 'linux':
        try:
            release = platform.freedesktop_os_release()
            os_version = release.get('PRETTY_NAME') or release.get('VERSION')
        except OSError:
            os_version = None
    else:
        os_version = platform.platform()
    return os_version, local_ip()


# @llr LLR-TERM-CONFIG-019
def request_host_power(action):
    if sys.platform != 'linux':
        return 'power_unavailable'
    command = {'shutdown': 'poweroff', 'reboot': 'reboot'}[action]
    try:
        subprocess.run(['/usr/bin/systemctl', '--no-ask-password', '--no-block', command],
                       timeout=5, check=True, capture_output=True)
    except (OSError, subprocess.SubprocessError):
        logging.warning('Local terminal power request failed: %s', action)
        return 'power_failed'
    return 'power_requested'
