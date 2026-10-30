#!/usr/bin/env python3
"""Fetch and hash-check pinned receiver sources into a new external directory."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import tempfile
from urllib.request import urlopen
KIT = Path(__file__).resolve().parents[1]


def prepare(work):
    work = work.expanduser().absolute()
    work = work.parent.resolve() / work.name
    if work.exists() or work.is_symlink() or work == KIT or KIT in work.parents:
        raise ValueError('Use a new directory outside this repository')
    manifest = json.loads((KIT / 'map-client/douyin-source.json').read_text())
    commit = manifest['recordedUpstreamCommit']
    if len(commit) != 40 or any(c not in '0123456789abcdef' for c in commit):
        raise ValueError('Invalid pinned commit')
    work.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.nak-receiver-', dir=work.parent) as temp:
        stage = Path(temp) / 'source'
        stage.mkdir()
        for row in manifest['files']:
            name = PurePosixPath(row['path'])
            if name.is_absolute() or '..' in name.parts or '\\' in row['path']:
                raise ValueError('Unsafe source path')
            url = 'https://raw.githubusercontent.com/saermart/DouyinLiveWebFetcher/' + commit + '/' + str(name)
            with urlopen(url, timeout=30) as response:
                data = response.read(8 * 1024 * 1024 + 1)
            if len(data) > 8 * 1024 * 1024 or hashlib.sha256(data).hexdigest() != row['sha256']:
                raise ValueError('Receiver source mismatch: ' + str(name))
            target = stage / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        if work.exists() or work.is_symlink():
            raise ValueError('Destination appeared; refusing overwrite')
        stage.rename(work)
    print(work)
    print('Pinned source only; no service started and no credentials read.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', required=True, type=Path)
    args = parser.parse_args()
    prepare(args.work)
