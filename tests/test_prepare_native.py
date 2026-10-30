"""Exercise reconstruction and refusal cases using an isolated local Git upstream."""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('prepare_native', Path(__file__).resolve().parents[1] / 'scripts/prepare_native.py')
prepare = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(prepare)


class PreparationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.kit = self.root / 'kit'
        self.kit.mkdir()
        for directory in ('patches', 'docs', 'licenses'):
            (self.kit / directory).mkdir()
        for name in prepare.NOTICE_FILES:
            (self.kit / name).write_text('test notice\n')
        self.cache = self.root / 'cache'
        self.cache.mkdir()
        def git(*args):
            return subprocess.check_output(['git', '-C', str(self.cache), *args])
        git('init', '-q')
        (self.cache / 'runtime.txt').write_text('base\n')
        git('add', '.')
        git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'fixture')
        commit = git('rev-parse', 'HEAD').decode().strip()
        # A caller's uncommitted file must be ignored and preserved.
        (self.cache / 'runtime.txt').write_text('user modification\n')
        self.patch_path = self.kit / 'patches/mod.patch'
        self.patch_path.write_text('''diff --git a/runtime.txt b/runtime.txt
--- a/runtime.txt
+++ b/runtime.txt
@@ -1 +1 @@
-base
+modded
diff --git a/new.py b/new.py
new file mode 100755
--- /dev/null
+++ b/new.py
@@ -0,0 +1 @@
+print("mod")
''')
        self.lock = {'schemaVersion': 1, 'upstream': {'url': 'https://github.com/example/upstream.git', 'commit': commit},
                     'patches': [{'path': 'patches/mod.patch', 'sha256': prepare.sha(self.patch_path)}],
                     'files': [
                         {'path': 'runtime.txt', 'baseSha256': hashlib.sha256(b'base\n').hexdigest(),
                          'sha256': hashlib.sha256(b'modded\n').hexdigest(), 'executable': False},
                         {'path': 'new.py', 'baseSha256': None,
                          'sha256': hashlib.sha256(b'print("mod")\n').hexdigest(), 'executable': True}]}
        self.write_lock()
        self.work = self.root / 'assembled'
        self.kit_patch = patch.object(prepare, 'KIT', self.kit)
        self.kit_patch.start()
        self.addCleanup(self.kit_patch.stop)

    def write_lock(self):
        (self.kit / 'upstream.lock.json').write_text(json.dumps(self.lock))

    def build(self):
        with contextlib.redirect_stdout(io.StringIO()):
            prepare.prepare(self.work, prepare.load_lock(), self.cache)

    def test_reconstructs_from_commit_and_preserves_dirty_cache(self):
        self.build()
        self.assertEqual((self.work / 'MacNativeGames/runtime.txt').read_text(), 'modded\n')
        self.assertEqual((self.cache / 'runtime.txt').read_text(), 'user modification\n')
        self.assertTrue((self.work / 'MacNativeGames/new.py').stat().st_mode & 0o111)
        with contextlib.redirect_stdout(io.StringIO()):
            prepare.verify(self.work, prepare.load_lock())
        self.assertTrue((self.work / 'MacNativeGames/.git').is_dir())

    def test_preserves_all_license_materials_in_external_workspace(self):
        for number, name in enumerate(prepare.NOTICE_FILES):
            (self.kit / name).write_text(f'notice {number}: {name}\n')
        self.build()
        for name in prepare.NOTICE_FILES:
            self.assertEqual((self.work / name).read_bytes(), (self.kit / name).read_bytes())

    def test_refuses_existing_directory_without_mutation(self):
        self.work.mkdir()
        marker = self.work / 'user.txt'
        marker.write_text('preserve')
        with self.assertRaises(ValueError):
            self.build()
        self.assertEqual(marker.read_text(), 'preserve')

    def test_rejects_patch_tampering_before_git(self):
        self.patch_path.write_text(self.patch_path.read_text() + '\n')
        with patch.object(prepare, 'git') as git:
            with self.assertRaises(ValueError):
                prepare.load_lock()
            git.assert_not_called()
        self.assertFalse(self.work.exists())

    def test_rejects_upstream_hash_mismatch(self):
        self.lock['files'][0]['baseSha256'] = '0' * 64
        self.write_lock()
        with self.assertRaises(ValueError):
            self.build()
        self.assertFalse(self.work.exists())

    def test_conflict_stops_without_partial_output(self):
        self.patch_path.write_text(self.patch_path.read_text().replace('-base', '-wrong context'))
        self.lock['patches'][0]['sha256'] = prepare.sha(self.patch_path)
        self.write_lock()
        with self.assertRaises(subprocess.CalledProcessError):
            self.build()
        self.assertFalse(self.work.exists())
        self.assertFalse(list(self.root.glob('.nak-prepare-*')))

    def test_verify_detects_user_change(self):
        self.build()
        (self.work / 'MacNativeGames/runtime.txt').write_text('changed')
        with self.assertRaises(ValueError):
            prepare.verify(self.work, prepare.load_lock())

    def test_verify_tolerates_only_cache_for_known_source(self):
        self.build()
        cache = self.work / 'MacNativeGames/__pycache__'
        cache.mkdir()
        (cache / 'new.cpython-314.pyc').write_bytes(b'test cache')
        with contextlib.redirect_stdout(io.StringIO()):
            prepare.verify(self.work, prepare.load_lock())
        (cache / 'unknown.cpython-314.pyc').write_bytes(b'unexpected')
        with self.assertRaises(ValueError):
            prepare.verify(self.work, prepare.load_lock())

    def test_rejects_unsafe_manifest_paths(self):
        self.lock['files'][0]['path'] = '../escape'
        self.write_lock()
        with self.assertRaises(ValueError):
            prepare.load_lock()

    def test_compatibility_file_uses_its_own_pinned_commit(self):
        git = lambda *args: subprocess.check_output(['git', '-C', str(self.cache), *args])
        path = self.cache / 'runtime.txt'
        path.write_text('compat base\n')
        git('add', '.')
        git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'compatibility input')
        commit = git('rev-parse', 'HEAD').decode().strip()
        self.lock['files'][0]['baseCommit'] = commit
        self.lock['files'][0]['baseSha256'] = hashlib.sha256(b'compat base\n').hexdigest()
        self.patch_path.write_text(self.patch_path.read_text().replace('-base\n', '-compat base\n'))
        self.lock['patches'][0]['sha256'] = prepare.sha(self.patch_path)
        self.write_lock()
        path.write_text('caller work preserved\n')
        self.build()
        self.assertEqual((self.work / 'MacNativeGames/runtime.txt').read_text(), 'modded\n')
        self.assertEqual(path.read_text(), 'caller work preserved\n')

    def test_generated_png_is_valid_and_contains_no_original_art(self):
        data = prepare.png(4, 3, (15, 23, 27))
        self.assertTrue(data.startswith(b'\x89PNG\r\n\x1a\n'))
        self.assertIn(b'IHDR', data)
        self.build()
        origin = json.loads((self.work / 'MacNativeGames/games/totk/assets/branding/loading/source.json').read_text())
        self.assertIn('Neutral placeholders', origin['origin'])


if __name__ == '__main__':
    unittest.main()
