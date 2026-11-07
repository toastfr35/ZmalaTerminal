"""Local command boundary for the unprivileged Terminal Settings screen."""
import json
import os
from pathlib import Path
import re
import stat


# @llr LLR-TERM-MAINT-030
class UpdateMailbox:
    def __init__(self, runtime):
        self.runtime = runtime
        self.offer = Path(runtime.request).with_name('offer.json')
        self.command = Path(runtime.status).with_name('update-command.json')
        self.previous = None

    def receive(self):
        try:
            fd = os.open(self.command, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            with os.fdopen(fd, 'rb') as stream:
                info = os.fstat(stream.fileno())
                if (not stat.S_ISREG(info.st_mode) or info.st_uid != self.runtime.uid
                        or info.st_mode & 0o077 or info.st_size > 4096):
                    return None
                request = json.loads(stream.read(4097))
            identity = request['request']
            action = request['action']
            if (request['schema'] != 1 or not re.fullmatch('[0-9a-f]{32}', identity)
                    or identity == self.previous or not 0 <= self.runtime.clock()-request['issued'] <= 40
                    or action not in ('check', 'apply')):
                return None
            fields = {'schema', 'request', 'action', 'issued'}
            if action == 'apply':
                fields.add('release')
                if not re.fullmatch('[0-9a-f]{64}', request['release']):
                    return None
            if set(request) != fields:
                return None
        except (OSError, ValueError, KeyError, TypeError):
            return None
        self.previous = identity
        return request

    def publish(self, state, identity='', **data):
        target = self.offer.with_suffix('.next')
        target.write_text(json.dumps({'schema': 1, 'request': identity, 'state': state, **data}), encoding='utf-8')
        target.chmod(0o644)
        os.replace(target, self.offer)
