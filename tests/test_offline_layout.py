"""Atomic native-map directory migration preserves content and rejects conflicts."""
from pathlib import Path
import hashlib
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'map-client/backend'))
import offline_layout as layout
import data_packs

class OfflineLayoutTests(unittest.TestCase):
    def fixture(self,base):
        support=base/'Library/Application Support';state=support/'TOTK Native Map';state.mkdir(parents=True)
        (state/'game-control.json').write_text('{"unchanged":true}')
        (state/'LocalHTTPS').mkdir(mode=0o700);key=state/'LocalHTTPS/ca.key';key.write_bytes(b'private-test-key');key.chmod(0o600)
        packs=support/'TOTK Offline/DataPacks';f=packs/'Maps/hyrule/1-hash.totkpack';f.parent.mkdir(parents=True);f.write_bytes(b'synthetic-pack')
        e={'kind':'map','id':'hyrule','version':'1','path':str(f),'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'reference':False}
        (packs/'registry.json').write_text(json.dumps({'schema':1,'active':{'map':e},'installed':[e]}))
        return state,packs
    def test_move_paths_hashes_key_permissions_and_idempotence(self):
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp);old,packs=self.fixture(home);result=layout.migrate(home);base=layout.root(home)
            self.assertEqual(result['status'],'complete');self.assertFalse(old.exists());self.assertFalse(packs.parent.exists())
            self.assertEqual((base/'State/game-control.json').read_text(),'{"unchanged":true}')
            self.assertEqual((base/'State/LocalHTTPS/ca.key').stat().st_mode&0o777,0o600)
            registry=json.loads((base/'DataPacks/registry.json').read_text());self.assertEqual(registry['active']['map']['path'],str(base/'DataPacks/Maps/hyrule/1-hash.totkpack'))
            self.assertEqual(registry['installed'][0]['path'],registry['active']['map']['path'])
            self.assertEqual(layout.migrate(home),result)
    def test_conflicting_state_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp);old,_=self.fixture(home);state=layout.root(home)/'State';state.mkdir(parents=True);(state/'game-control.json').write_text('different')
            with self.assertRaisesRegex(RuntimeError,'同名状态'):layout.migrate(home)
            self.assertTrue(old.exists());self.assertEqual((state/'game-control.json').read_text(),'different')
    def test_corrupt_pack_prevents_any_state_move(self):
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp);old,packs=self.fixture(home);next(packs.rglob('*.totkpack')).write_bytes(b'corrupt')
            with self.assertRaisesRegex(ValueError,'digest'):layout.migrate(home)
            self.assertTrue((old/'game-control.json').exists())
    def test_live_service_blocks_before_migration(self):
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp);old,_=self.fixture(home);(old/'connection.json').write_text(json.dumps({'pid':os.getpid()}))
            with self.assertRaisesRegex(RuntimeError,'仍在运行'):layout.migrate(home)
            self.assertFalse(layout.root(home).exists())
    def test_registry_repair_after_directory_rename_interruption(self):
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp);_,packs=self.fixture(home);base=layout.root(home);base.mkdir(parents=True);packs.rename(base/'DataPacks')
            layout.migrate(home);d=json.loads((base/'DataPacks/registry.json').read_text());self.assertTrue(Path(d['active']['map']['path']).exists())
    def test_external_reference_stays_external(self):
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp);_,packs=self.fixture(home);d=json.loads((packs/'registry.json').read_text());external=home/'external.totkpack';external.write_bytes(b'external')
            entry={'path':str(external),'reference':True};d['installed'].append(entry);(packs/'registry.json').write_text(json.dumps(d));layout.migrate(home)
            result=json.loads((layout.root(home)/'DataPacks/registry.json').read_text());self.assertEqual(result['installed'][-1]['path'],str(external))
    def test_symlink_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp);old,_=self.fixture(home);(old/'alias').symlink_to(home)
            with self.assertRaisesRegex(ValueError,'symlink'):layout.migrate(home)
    def test_default_roots_and_explicit_isolation(self):
        with patch.dict(os.environ,{},clear=True),patch.object(layout.Path,'home',return_value=Path('/fake-home')):
            self.assertEqual(data_packs.support_root(),layout.root()/'State');self.assertEqual(data_packs.content_root(),layout.root())
        with patch.dict(os.environ,{'TOTK_SUPPORT_ROOT':'/tmp/isolated-state'},clear=True):
            self.assertEqual(data_packs.content_root(),Path('/tmp/isolated-state'))
