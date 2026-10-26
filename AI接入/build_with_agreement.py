#!/usr/bin/env python3
"""Release build entry: show agreement and require explicit consent before building."""
import argparse
from pathlib import Path
import subprocess
import sys
from release_consent import require_consent, agreement_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True, help='Assembled external MacNativeGames source directory')
    parser.add_argument('--consent', help='Exact user reply; agents must obtain it from the human first')
    parser.add_argument('build_args', nargs=argparse.REMAINDER, help='Arguments after -- go to build_app.py')
    args = parser.parse_args()
    require_consent(args.consent)
    build_args = args.build_args
    if build_args[:1] == ['--']:
        build_args = build_args[1:]
    if not build_args:
        parser.error('Pass game build arguments after --; no build has started')
    root = args.source.expanduser().resolve()
    if not (root / 'build_app.py').is_file():
        raise ValueError('Prepare upstream sources first; --source must contain build_app.py')
    return subprocess.call([sys.executable, str(root / 'build_app.py'), *build_args])


if __name__ == '__main__':
    try:
        sys.exit(main())
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(2)
