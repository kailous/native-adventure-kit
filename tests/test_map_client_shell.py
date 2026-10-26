"""Map source shell works without original game assets or user data."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('map_resources', ROOT / 'map-client/prepare_resources.py')
resources = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(resources)


class MapShellTests(unittest.TestCase):
    def test_neutral_resources_do_not_include_content_or_data_packs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = resources.prepare(Path(directory) / 'resources')
            self.assertEqual(json.loads((root / 'webui/gamersky-archive.json').read_text()), {'points': []})
            self.assertFalse(list(root.rglob('*.totkpack')))
            self.assertFalse(list(root.rglob('*.sqlite')))
            self.assertEqual(json.loads((root / 'RESOURCE_SCOPE.json').read_text())['externalResourcesUsed'], False)
            with self.assertRaises(ValueError):
                resources.prepare(root)

    def test_data_free_backend_can_list_and_query_tools(self):
        with tempfile.TemporaryDirectory() as directory:
            root = resources.prepare(Path(directory) / 'resources')
            env = dict(os.environ, TOTK_RESOURCE_ROOT=str(root), TOTK_SUPPORT_ROOT=str(root / 'private-support'),
                       TOTK_DATA_SUPPORT_ROOT=str(root / 'private-data'), TOTK_CLIENT_EDITION='native',
                       PYTHONPATH=str(ROOT / 'map-client/backend'), PYTHONDONTWRITEBYTECODE='1')
            script = '''from pathlib import Path
import json
from server import SaveSource
from map_service import MapService
from mcp_protocol import dispatch
service=MapService(SaveSource([Path("/nonexistent-map-test-saves")]))
listed=dispatch(service,{"id":1,"method":"tools/list"})
search=service.search("test")
progress=service.progress()
assert search["points"]==[]
assert progress["states"]=={}
assert listed["result"]["tools"]
print("data-free shell works")
'''
            result = subprocess.run([sys.executable, '-B', '-c', script], env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_external_input_is_allowlisted(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            supplied = base / 'supplied'
            (supplied / 'webui').mkdir(parents=True)
            (supplied / 'webui/towers.json').write_text('[]')
            (supplied / 'webui/gamersky-archive.json').write_text('{"points":[{"private":"must not copy"}]}')
            root = resources.prepare(base / 'result', supplied)
            self.assertEqual(json.loads((root / 'webui/gamersky-archive.json').read_text()), {'points': []})


if __name__ == '__main__':
    unittest.main()
