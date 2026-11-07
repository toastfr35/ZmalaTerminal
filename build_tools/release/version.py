"""Read the terminal release identity independently of the Android app."""
import json
import re


def terminal_version(root):
    record = json.loads((root/'VERSION.json').read_text(encoding='utf-8'))
    version, sequence = record['version'], record['sequence']
    if not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', version) or type(sequence) is not int or sequence < 1:
        raise ValueError('Invalid terminal release version or sequence')
    return version, sequence
