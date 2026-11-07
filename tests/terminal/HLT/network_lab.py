# @test T-HLT-032
# @requirements HLR-TERM-CALL-009, HLR-TERM-CALL-010
# @environment linux-root
# @plan Run the shared Docker NAT lab with the real terminal Engine, its server proof checks, Liblinphone and production decoder. Replace physical camera/audio, Pi V4L2 encoding and UI control with generated media, OpenH264 software encoding and queued commands. Exercise outgoing, authenticated incoming, hangup, idle incoming and firewall recovery; inspect decoded opposite audio tones and video frame progress. The scenario is shared with S-HLT-029. With --udp-blocked, block all forwarded UDP before fresh registration at each home gateway, verify HTTP still works and calls fail in both directions, then separately block RTP/RTCP and verify connected SIP with no decoded media. Remove each fault and require a successful recovery call. Observe firewall drop counters; these are bounded negative tests of the current UDP-only configuration.
# @pass Calls start, accept a valid server proof, deliver decoded media and return to idle on both clients. No claim is made for user-facing countdown/UI, invalid-proof rejection, Pi hardware performance or arbitrary external networks; those require their separate tests.

import os
from pathlib import Path
import subprocess
import sys


if __name__ == '__main__':
    checkout = os.environ.get('ZMALA_IMAGE_BUILDER_ROOT')
    if not checkout:
        raise SystemExit('Set ZMALA_IMAGE_BUILDER_ROOT to the prepared Zmala checkout')
    root = Path(checkout).resolve()
    entry = root/'tests/support/network_lab/scenarios.py'
    if not entry.is_file():
        raise SystemExit('The Zmala checkout does not contain the network lab')
    subprocess.run([sys.executable, '-m', 'tests.support.network_lab.scenarios', *sys.argv[1:]],
                   cwd=root, check=True)
