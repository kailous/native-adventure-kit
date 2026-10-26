"""Exercise publication omissions and accidental private/binary content without extraction."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import stat
import tempfile
import unittest
import zipfile

KIT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('check_release', KIT / 'scripts/check_release.py')
checker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checker)


class PublicationChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / 'kit'
        shutil.copytree(KIT, self.root, ignore=shutil.ignore_patterns('.git', '__pycache__'))

    def kinds(self, **kwargs):
        return {e['kind'] for e in checker.check(**kwargs)['errors']}

    def test_current_source_tree_passes_but_preserves_pending_warning(self):
        result = checker.check(root=self.root)
        self.assertTrue(result['passed'], result)
        self.assertTrue(any('pending' in w for w in result['warnings']))

    def test_missing_gpl_text_fails(self):
        (self.root / 'licenses/GPL-2.0-only.txt').unlink()
        self.assertIn('missing-required-file', self.kinds(root=self.root))

    def test_changed_original_notice_fails(self):
        with (self.root / 'licenses/Marc-Robledo-equipment-MIT.txt').open('a') as stream:
            stream.write('altered')
        self.assertIn('notice-digest-mismatch', self.kinds(root=self.root))

    def test_unlisted_spdx_fails_even_after_patch_lock_update(self):
        path = self.root / 'patches/native-mod.patch'
        with path.open('a') as stream:
            stream.write('\n+++ b/runtime/new.h\n+// SPDX-License-Identifier: GPL-2.0-only\n')
        lock_path = self.root / 'upstream.lock.json'
        lock = json.loads(lock_path.read_text())
        lock['patches'][0]['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
        lock_path.write_text(json.dumps(lock))
        self.assertIn('spdx-inventory-mismatch', self.kinds(root=self.root))

    def test_ignored_inputs_and_empty_app_directory_fail(self):
        (self.root / '.env.local').write_text('PRIVATE=example')
        (self.root / 'example.keys').write_text('example')
        (self.root / 'Game.app').mkdir()
        self.assertIn('excluded-file-type', self.kinds(root=self.root))
        self.assertIn('excluded-content', self.kinds(root=self.root))

    def test_removing_notice_from_manifest_does_not_bypass_validation(self):
        path = self.root / 'docs/gpl-components.json'
        manifest = json.loads(path.read_text())
        del manifest['notices']['licenses/Lotuskit-LICENSE']
        path.write_text(json.dumps(manifest))
        self.assertIn('known-notice-removed', self.kinds(root=self.root))

    def test_removing_known_component_and_its_marker_is_not_license_cleanup(self):
        path = self.root / 'docs/gpl-components.json'
        manifest = json.loads(path.read_text())
        component = manifest['components'].pop()
        path.write_text(json.dumps(manifest))
        patch_path = self.root / manifest['patch']
        lines = patch_path.read_text().splitlines(keepends=True)
        lines[component['patchLine'] - 1] = '+// changed header\n'
        patch_path.write_text(''.join(lines))
        lock_path = self.root / 'upstream.lock.json'
        lock = json.loads(lock_path.read_text())
        lock['patches'][0]['sha256'] = hashlib.sha256(patch_path.read_bytes()).hexdigest()
        lock_path.write_text(json.dumps(lock))
        self.assertIn('known-gpl-component-removed', self.kinds(root=self.root))

    def test_binary_without_extension_fails(self):
        (self.root / 'tool').write_bytes(b'\x7fELF\0example')
        self.assertIn('unexpected-binary', self.kinds(root=self.root))

    def test_possible_credential_is_not_returned_in_report(self):
        sample = 'ghp_' + 'A' * 40
        (self.root / 'config.txt').write_text(sample)
        result = checker.check(root=self.root)
        self.assertIn('possible-credential', {e['kind'] for e in result['errors']})
        self.assertNotIn(sample, json.dumps(result))

    def test_rooted_candidate_zip_passes(self):
        candidate = self.base / 'candidate.zip'
        with zipfile.ZipFile(candidate, 'w', zipfile.ZIP_DEFLATED) as bundle:
            for path in self.root.rglob('*'):
                if path.is_file():
                    bundle.write(path, 'kit/' + path.relative_to(self.root).as_posix())
        self.assertTrue(checker.check(archive=candidate)['passed'])

    def test_zip_traversal_is_rejected_without_extraction(self):
        candidate = self.base / 'unsafe.zip'
        with zipfile.ZipFile(candidate, 'w') as bundle:
            bundle.writestr('kit/../../escape.txt', 'example')
        self.assertIn('unsafe-path', self.kinds(archive=candidate))
        self.assertFalse((self.base / 'escape.txt').exists())

    def test_zip_symlink_is_rejected(self):
        candidate = self.base / 'link.zip'
        info = zipfile.ZipInfo('kit/link')
        info.create_system = 3
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        with zipfile.ZipFile(candidate, 'w') as bundle:
            bundle.writestr(info, '/private/example')
        self.assertIn('symlink', self.kinds(archive=candidate))

    def test_invalid_archive_returns_failure(self):
        candidate = self.base / 'bad.zip'
        candidate.write_text('invalid')
        self.assertIn('unreadable-archive', self.kinds(archive=candidate))

    def test_directory_checks_do_not_modify_files(self):
        before = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        checker.check(root=self.root)
        after = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(before, after)


if __name__ == '__main__':
    unittest.main()
