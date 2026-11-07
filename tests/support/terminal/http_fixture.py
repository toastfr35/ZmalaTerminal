"""Private HTTP test service, stopped and removed when the test leaves its context."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import subprocess
from zmala_terminal.common.native_runtime import process_options
import tempfile
import time

@contextmanager
def http_server_fixture():
    source = os.environ.get('ZMALA_TEST_SERVER_ROOT')
    if not source:
        raise RuntimeError('Set ZMALA_TEST_SERVER_ROOT to the prepared ZmalaServer checkout')
    server = Path(source).resolve()
    entry = server/'tests/support/server/http-live-server.js'
    if not entry.is_file():
        raise RuntimeError('The ZmalaServer checkout does not contain the isolated HTTP fixture')
    with tempfile.TemporaryDirectory(prefix='provisioning-') as temporary:
        ready = Path(temporary) / 'ready'
        log_path = Path(temporary) / 'server.log'
        with log_path.open('wb') as log:
            process = subprocess.Popen(
                ['node', str(entry), str(ready)],
                cwd=server, stdin=subprocess.PIPE, stdout=log, stderr=log,
                **process_options(),
            )
            try:
                deadline = time.monotonic() + 10
                while not ready.exists():
                    if process.poll() is not None or time.monotonic() >= deadline:
                        raise RuntimeError('Isolated HTTP fixture did not start:\n'+log_path.read_text(errors='replace')[-4000:])
                    time.sleep(.05)
                directory = Path(ready.read_text(encoding='utf-8'))
                yield json.loads((directory / 'server.json').read_text(encoding='utf-8'))
            finally:
                process.stdin.close()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
