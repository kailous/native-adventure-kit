"""Read-only checks for this source-only kit or a candidate ZIP; never legal clearance."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import zipfile

KIT = Path(__file__).resolve().parents[1]
REQUIRED = (
    'LICENSE', 'LICENSE_SCOPE.md', 'README.md', '使用协议.md',
    'docs/third-party-notices.md', 'docs/gpl-components.md',
    'docs/gpl-components.json', 'docs/generated-data-provenance.md',
    'docs/release-governance.md', 'docs/historical-release-review.md',
    'docs/split-releases.md', 'docs/upstream-merge-policy.md', 'scripts/install_map_tunnel.command',
    'licenses/README.md', 'licenses/MacNativeGames-LICENSE',
    'licenses/GPL-2.0-only.txt', 'licenses/Lotuskit-LICENSE',
    'licenses/Marc-Robledo-equipment-MIT.txt',
    'map-client/webui/icons/reicon/LICENSE',
    'map-client/webui/icons/reicon/SOURCE.md', 'upstream.lock.json',
)
MAX_FILE = 16 * 1024 * 1024
MAX_TOTAL = 128 * 1024 * 1024
BASE_GPL_PATHS = {
    'games/totk/runtime/' + name for name in (
        'camera_math.h', 'camera_probe.h', 'equipment_defaults.h', 'pouch_control.h',
        'quantity_control.h', 'spawn_catalog.h', 'spawn_control.h', 'weather_control.h',
    )
}
BASE_NOTICES = {
    'LICENSE', 'licenses/MacNativeGames-LICENSE', 'licenses/GPL-2.0-only.txt',
    'licenses/Lotuskit-LICENSE', 'licenses/Marc-Robledo-equipment-MIT.txt',
}
FORBIDDEN_SUFFIXES = {
    '.xci', '.xcz', '.nsp', '.nsz', '.nca', '.nso', '.keys', '.key', '.pem',
    '.sav', '.bfttf', '.totkpack', '.zip', '.gz', '.tar', '.dmg', '.exe',
    '.dylib', '.so', '.a', '.pyc', '.png', '.jpg', '.jpeg', '.webp', '.icns',
}
SECRET_PATTERNS = (
    re.compile(r'\bgh[pousr]_[A-Za-z0-9]{30,}\b'),
    re.compile(r'\bgithub_pat_[A-Za-z0-9_]{40,}\b'),
    re.compile(r'-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----'),
)


def check(root=None, archive=None):
    """Return paths and error kinds only; never echo suspected credential values."""
    errors, warnings, files = [], [], {}

    def error(kind, path):
        errors.append({'kind': kind, 'path': str(path)})

    def accept(name, size, read):
        path = PurePosixPath(name)
        parts = path.parts
        if not parts or path.is_absolute() or '..' in parts or '\\' in name:
            error('unsafe-path', name)
            return
        if any(p.lower() in {'datapacks', '__pycache__', '__macosx', '.git'}
               or p.lower().endswith('.app') for p in parts):
            error('excluded-content', name)
        if path.suffix.lower() in FORBIDDEN_SUFFIXES or path.name.lower().startswith('.env'):
            error('excluded-file-type', name)
        if name in files:
            error('duplicate-path', name)
            return
        if size > MAX_FILE:
            error('oversized-file', name)
            return
        data = read()
        if len(data) > MAX_FILE:
            error('oversized-file', name)
            return
        files[name] = data
        try:
            text = data.decode('utf-8')
        except UnicodeDecodeError:
            error('unexpected-binary', name)
            return
        if '\0' in text or any(data.startswith(magic) for magic in
                               (b'MZ', b'\x7fELF', b'\xcf\xfa\xed\xfe', b'\xfe\xed\xfa\xcf', b'PK\x03\x04')):
            error('unexpected-binary', name)
        if any(pattern.search(text) for pattern in SECRET_PATTERNS):
            error('possible-credential', name)

    if archive is not None:
        try:
            with zipfile.ZipFile(archive) as bundle:
                entries = bundle.infolist()
                if sum(i.file_size for i in entries) > MAX_TOTAL:
                    error('archive-too-large', '<archive>')
                    entries = []
                # A single enclosing directory is allowed; root-level files are also allowed.
                names = [i.filename for i in entries if not i.is_dir()]
                prefixes = {n.split('/')[0] for n in names}
                prefix = next(iter(prefixes)) + '/' if len(prefixes) == 1 and all('/' in n for n in names) else ''
                for item in entries:
                    raw = item.filename
                    if raw.startswith('/') or '..' in PurePosixPath(raw).parts or '\\' in raw:
                        error('unsafe-path', raw)
                        continue
                    name = raw[len(prefix):] if prefix and raw.startswith(prefix) else raw
                    if not name:
                        continue
                    if stat.S_ISLNK(item.external_attr >> 16):
                        error('symlink', name)
                    elif item.is_dir():
                        if any(p.lower().endswith('.app') or p.lower() == 'datapacks'
                               for p in PurePosixPath(name).parts):
                            error('excluded-content', name)
                    else:
                        accept(name, item.file_size, lambda i=item: bundle.read(i))
        except (OSError, ValueError, RuntimeError, zipfile.BadZipFile, NotImplementedError):
            error('unreadable-archive', '<archive>')
    else:
        root = Path(root or KIT)
        if not root.is_dir():
            error('missing-root', '<root>')
        total = 0
        for path in sorted(root.rglob('*')):
            name = path.relative_to(root).as_posix()
            if '.git' in path.relative_to(root).parts:
                continue
            if path.is_symlink():
                error('symlink', name)
            elif path.is_file():
                total += path.stat().st_size
                if total > MAX_TOTAL:
                    error('source-too-large', '<root>')
                    break
                accept(name, path.stat().st_size, path.read_bytes)
            elif path.is_dir() and (path.name.lower().endswith('.app') or path.name.lower() == 'datapacks'):
                error('excluded-content', name)

    for name in REQUIRED:
        if name not in files:
            error('missing-required-file', name)

    try:
        manifest = json.loads(files['docs/gpl-components.json'])
        lock = json.loads(files['upstream.lock.json'])
        patch_path = manifest['patch']
        patch_bytes = files[patch_path]
        patch_text = patch_bytes.decode('utf-8')
        locked_patches = {p['path']: p['sha256'] for p in lock['patches']}
        if hashlib.sha256(patch_bytes).hexdigest() != locked_patches[patch_path]:
            error('patch-lock-mismatch', patch_path)
        markers, target = [], None
        for number, line in enumerate(patch_text.splitlines(), 1):
            if line.startswith('+++ b/'):
                target = line[6:]
            elif line.startswith('+') and not line.startswith('+++'):
                match = re.search(r'SPDX-License-Identifier:\s*([^\r\n]+)', line)
                if match:
                    markers.append((target, number, match.group(1).strip()))
        declared = [(c['path'], c['patchLine'], c['license']) for c in manifest['components']]
        if sorted(markers) != sorted(declared):
            error('spdx-inventory-mismatch', 'docs/gpl-components.json')
        if not BASE_GPL_PATHS.issubset({c['path'] for c in manifest['components']}):
            error('known-gpl-component-removed', 'docs/gpl-components.json')
        if not BASE_NOTICES.issubset(manifest['notices']):
            error('known-notice-removed', 'docs/gpl-components.json')
        source_lock = {f['path']: f for f in lock['files']}
        for component in manifest['components']:
            path = component['path']
            if component['sha256'] != source_lock[path]['sha256']:
                error('component-lock-mismatch', path)
            if component['license'] != 'GPL-2.0-only':
                error('license-needs-review', path)
            if path not in files['docs/gpl-components.md'].decode('utf-8'):
                error('missing-source-description', path)
        for name, expected in manifest['notices'].items():
            if hashlib.sha256(files[name]).hexdigest() != expected:
                error('notice-digest-mismatch', name)
        if not manifest['components'] or not manifest['notices']:
            error('empty-license-inventory', 'docs/gpl-components.json')
        pending = sum(c.get('rightsReview') != 'verified' for c in manifest['components'])
        if pending:
            warnings.append(f'{pending} component rights reviews remain pending; this is not legal clearance.')
    except (KeyError, TypeError, ValueError, UnicodeError):
        error('invalid-or-incomplete-license-inventory', 'docs/gpl-components.json')

    warnings.append('Filename, UTF-8 and limited credential-pattern checks cannot prove absence of protected material or secrets.')
    return {'passed': not errors, 'filesChecked': len(files), 'errors': errors, 'warnings': warnings}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--root', type=Path, help='Candidate source directory; includes Git-ignored files, excludes .git')
    group.add_argument('--archive', type=Path, help='Inspect a candidate ZIP without extracting or executing it')
    args = parser.parse_args()
    result = check(args.root, args.archive)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
