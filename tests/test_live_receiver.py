"""External receiver preparation never overwrites caller files or skips hashes."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
SPEC = importlib.util.spec_from_file_location('receiver_prepare', Path(__file__).resolve().parents[1] / 'scripts/prepare_live_receiver.py')
receiver = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(receiver)


class ReceiverPreparation(unittest.TestCase):
    def run_case(self, corrupt=False, existing=False):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            kit = root / 'kit'
            (kit / 'map-client').mkdir(parents=True)
            manifest = {'recordedUpstreamCommit': 'a' * 40, 'files': [{'path': 'source.py', 'sha256': hashlib.sha256(b'approved source').hexdigest()}]}
            (kit / 'map-client/douyin-source.json').write_text(json.dumps(manifest))
            work = root / 'external'
            if existing:
                work.mkdir()
                (work / 'user.txt').write_text('keep')
            with patch.object(receiver, 'KIT', kit), patch.object(receiver, 'urlopen', return_value=io.BytesIO(b'corrupt' if corrupt else b'approved source')) as fetch:
                if corrupt or existing:
                    with self.assertRaises(ValueError):
                        receiver.prepare(work)
                else:
                    receiver.prepare(work)
                    self.assertEqual((work / 'source.py').read_bytes(), b'approved source')
                if existing:
                    fetch.assert_not_called()
                    self.assertEqual((work / 'user.txt').read_text(), 'keep')
                elif corrupt:
                    self.assertFalse(work.exists())

    def test_success(self): self.run_case()
    def test_wrong_digest_leaves_no_output(self): self.run_case(corrupt=True)
    def test_existing_work_is_untouched(self): self.run_case(existing=True)
