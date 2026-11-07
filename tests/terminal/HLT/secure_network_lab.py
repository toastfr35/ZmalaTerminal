# @test T-HLT-033
# @requirements HLR-TERM-COM-009
# @environment linux-root
# @plan Run the shared secure-network matrix against the actual terminal Engine with its server-provided TLS/TURN policy. Verify native SRTP and relay state plus decoded peer media while UDP is denied at each home, in both directions. Use synthetic media and a disposable CA. Reject an untrusted CA and a wrong certificate name through the native SIP client. Physical Pi load and moving-camera quality are not measured.
# @pass All matrix checks pass, with fresh decoded tones/frames and no transport configuration monkeypatch.

import os
from pathlib import Path
import subprocess
import sys


if __name__ == '__main__':
    checkout = os.environ.get('ZMALA_IMAGE_BUILDER_ROOT')
    if not checkout:
        raise SystemExit('Set ZMALA_IMAGE_BUILDER_ROOT to the prepared Zmala checkout')
    root = Path(checkout).resolve()
    entry = root/'tests/support/network_lab/tls_scenarios.py'
    if not entry.is_file():
        raise SystemExit('The Zmala checkout does not contain the network lab')
    subprocess.run([sys.executable, '-m', 'tests.support.network_lab.tls_scenarios', *sys.argv[1:]],
                   cwd=root, check=True)
