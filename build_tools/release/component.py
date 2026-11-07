"""Validate component release identity and publish only an exact asset list."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[2]
REPOSITORY = 'toastfr35/ZmalaTerminal'
VERSION_PATH = 'VERSION.json'


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()


def read_version(text):
    metadata = json.loads(text)
    version, sequence = metadata['version'], metadata.get('sequence')
    if not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', version):
        raise ValueError('Invalid component release version')
    if type(sequence) is not int or sequence < 1:
        raise ValueError('Invalid terminal update sequence')
    return version, sequence


def check_pr_version():
    base = os.environ['BASE_SHA']
    if not re.fullmatch('[0-9a-f]{40}', base):
        raise ValueError('Expected a full base SHA')
    current = read_version((ROOT/VERSION_PATH).read_text(encoding='utf-8'))
    if not git('ls-tree', base, '--', VERSION_PATH):
        return  # Initial import into a repository-creation README commit.
    previous = read_version(git('show', base+':'+VERSION_PATH))
    if (tuple(map(int, current[0].split('.'))) <= tuple(map(int, previous[0].split('.')))
            or (current[1] is not None and current[1] <= previous[1])):
        raise ValueError('Increase the component version and its update sequence, if applicable')


def validate_leaflet_bundle(path):
    """Accept only both PDF layouts for every terminal locale and printing notes."""
    languages = json.loads((ROOT / 'zmala_terminal/common/shared/terminal-languages.json').read_text(encoding='utf-8'))
    expected = {'PRINTING.txt'} | {
        f'ZmalaTerminal-Leaflet-{code}{suffix}.pdf'
        for code in languages for suffix in ('', '-A4')}
    try:
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            if len(names) != len(expected) or set(names) != expected:
                raise ValueError('Leaflet bundle must contain exactly all language PDFs and PRINTING.txt')
            for item in archive.infolist():
                if not item.file_size or item.flag_bits & 1:
                    raise ValueError('Leaflet bundle contains an empty or encrypted entry')
                if item.filename.endswith('.pdf'):
                    with archive.open(item) as stream:
                        if stream.read(4) != b'%PDF':
                            raise ValueError('Leaflet bundle contains an invalid PDF')
            if archive.testzip() is not None:
                raise ValueError('Leaflet bundle integrity check failed')
    except (zipfile.BadZipFile, OSError, RuntimeError, EOFError) as error:
        raise ValueError('Invalid leaflet bundle') from error



def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('check-pr-version', 'publish'))
    parser.add_argument('assets', nargs='*', type=Path)
    args = parser.parse_args()
    if args.action == 'check-pr-version':
        check_pr_version()
        return
    version, _ = read_version((ROOT/VERSION_PATH).read_text(encoding='utf-8'))
    tag = 'v'+version
    commit = git('rev-parse', 'HEAD')
    if os.environ.get('GITHUB_REPOSITORY') != REPOSITORY or os.environ.get('GITHUB_REF') != 'refs/heads/main':
        raise ValueError('Releases are restricted to the owning repository main branch')
    if git('ls-remote', 'origin', 'refs/heads/main').split()[0] != commit:
        raise ValueError('Refusing to publish a superseded main commit')
    expected = {f'ZmalaTerminal-{version}-linux-arm64.tar.gz', f'ZmalaTerminal-{version}-linux-arm64.tar.gz.sha256', 'ZmalaTerminal-Update.json', 'ZmalaTerminal-Update.tar.gz', 'ZmalaTerminal-Leaflets.zip'}
    if len(args.assets) != len(expected) or {p.name for p in args.assets} != expected:
        raise ValueError('Unexpected release asset list')
    if any(p.is_symlink() or not p.is_file() or not p.stat().st_size for p in args.assets):
        raise ValueError('Missing or empty release asset')
    assets = {path.name: path for path in args.assets}
    validate_leaflet_bundle(assets['ZmalaTerminal-Leaflets.zip'])
    package_name = f'ZmalaTerminal-{version}-linux-arm64.tar.gz'
    digest = hashlib.sha256(assets[package_name].read_bytes()).hexdigest()
    if assets[package_name+'.sha256'].read_text(encoding='utf-8').strip() != f'{digest}  {package_name}':
        raise ValueError('Terminal package checksum does not match its release sidecar')
    notes = 'Built from '+commit+'\n\nSHA-256\n\n'+'\n'.join(
        '- '+p.name+' '+hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(args.assets))
    subprocess.run(['gh', 'release', 'create', tag, *map(str, args.assets), '--repo', REPOSITORY,
                    '--draft', '--target', commit, '--title', tag, '--notes', notes], check=True)
    # Keep failures visible as drafts. GitHub refuses a duplicate release tag.
    subprocess.run(['gh', 'release', 'edit', tag, '--repo', REPOSITORY, '--draft=false'], check=True)


if __name__ == '__main__':
    main()
