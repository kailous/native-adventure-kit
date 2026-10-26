"""Release gates and portable packaging, with synthetic local MCP only."""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
HELPERS = ROOT / 'AI接入'
sys.path.insert(0, str(HELPERS))
import release_consent
import generate_mcp_bundle


class ReleaseHelpers(unittest.TestCase):
    def test_gate_blocks_missing_and_wrong_consent(self):
        for value in (None, 'yes', '我同意'):
            with patch('sys.stdin.isatty', return_value=False), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(ValueError):
                    release_consent.require_consent(value)

    def test_gate_matches_document(self):
        self.assertIn(release_consent.PHRASE, release_consent.agreement_path().read_text())

    def test_cli_refusal_creates_no_plugin(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'must-not-exist'
            result = subprocess.run([sys.executable, '-B', str(HELPERS / 'generate_mcp_bundle.py'),
                'generate', '--out', str(out)], stdin=subprocess.DEVNULL, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(out.exists())

    def test_portable_plugin_is_self_contained_without_credentials(self):
        # Test the packaging function, not a real user's consent or account installation.
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            out = Path(tmp) / 'sample'
            generate_mcp_bundle.generate(out, 'https://example.invalid/mcp')
            plugin = out / 'totk-native-helper'
            manifest = json.loads((plugin / 'plugin.json').read_text())
            self.assertEqual(manifest['name'], 'totk-native-helper')
            mcp = json.loads((plugin / 'mcp.json').read_text())
            auth = mcp['mcpServers']['totk-native']['extensions']['com.openai']['auth']
            self.assertEqual(auth, {'type': 'api_key', 'headerScheme': 'bearer'})
            self.assertNotIn('headers', mcp['mcpServers']['totk-native'])
            with zipfile.ZipFile(out / 'totk-native-helper.zip') as archive:
                self.assertIsNone(archive.testzip())
                self.assertTrue(any(name.endswith('/references/使用协议.md') for name in archive.namelist()))

    def test_rejects_credentials_in_url_and_nonlocal_http(self):
        for url in ('https://user:password@example.invalid/mcp',
                    'https://example.invalid/mcp?token=secret', 'http://example.invalid/mcp'):
            with self.assertRaises(ValueError):
                generate_mcp_bundle.validate_url(url)

    def test_probe_only_initializes_and_lists(self):
        calls = []
        class Opener:
            def open(self, request, timeout):
                message = json.loads(request.data)
                calls.append(message['method'])
                if 'id' not in message:
                    return io.BytesIO(b'')
                result = {'protocolVersion': '2025-03-26'} if message['method'] == 'initialize' else {
                    'tools': [{'name': 'synthetic_search', 'inputSchema': {'type': 'object'}}]}
                return io.BytesIO(json.dumps({'jsonrpc': '2.0', 'id': message['id'], 'result': result}).encode())
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / 'private.json'
            config.write_text(json.dumps({'mcpServers': {'test': {
                'url': 'http://127.0.0.1:12345/mcp',
                'headers': {'Authorization': 'Bearer synthetic-test-token'}}}}))
            output = io.StringIO()
            with patch('urllib.request.build_opener', return_value=Opener()), contextlib.redirect_stdout(output):
                generate_mcp_bundle.check(config)
            self.assertNotIn('synthetic-test-token', output.getvalue())
        self.assertEqual(calls, ['initialize', 'notifications/initialized', 'tools/list'])


if __name__ == '__main__':
    unittest.main()
