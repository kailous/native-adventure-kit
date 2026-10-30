"""Fixed-domain ngrok lifecycle and a loopback, MCP-only origin.

The public origin never serves the map, save downloads, or tunnel administration.
Bearer credentials are checked by the existing MCP handler, never injected here.
"""
import json
import os
import re
import subprocess
import tempfile
import threading
from http_server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit


def fixed_url(value):
    value = str(value).strip()
    if '://' not in value:
        value = 'https://' + value
    parsed = urlsplit(value)
    host = parsed.hostname or ''
    if (parsed.scheme != 'https' or parsed.username or parsed.password or parsed.port
            or parsed.path not in ('', '/', '/mcp') or parsed.query or parsed.fragment
            or not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.(?:ngrok-free\.(?:app|dev)|ngrok\.(?:app|dev|io))', host)):
        raise ValueError('请输入 ngrok 账号分配的固定 HTTPS 域名，例如 example.ngrok-free.app')
    return 'https://' + host


def gateway_handler(base):
    class Gateway(base):
        def local_request(self):
            host = self.headers.get('Host', '')
            public = urlsplit(self.server.public_url).netloc
            local = '127.0.0.1:' + str(self.server.server_port)
            if host not in (public, public + ':443', local):
                self.json_reply(403, {'error': 'Invalid tunnel host'}); return False
            if self.headers.get('Origin') not in (None, self.server.public_url):
                self.json_reply(403, {'error': 'Invalid tunnel origin'}); return False
            return True

        def route(self, method):
            if self.path != '/mcp':
                self.close_connection = True
                self.json_reply(404, {'error': 'Not found'}); return
            return method()

        def do_POST(self): return self.route(super().do_POST)
        def do_GET(self):
            if urlsplit(self.path).path.startswith('/api/media/'):return self.serve_media()
            return self.route(super().do_GET)
        def do_DELETE(self): return self.route(super().do_DELETE)
        def do_HEAD(self):
            if urlsplit(self.path).path.startswith('/api/media/'):return self.serve_media(head=True)
            self.send_response(405);self.send_header('Content-Length','0');self.end_headers()
        def do_OPTIONS(self): self.json_reply(405, {'error': 'Method not allowed'})
        def log_message(self, *args): pass  # Never log RPC bodies or credentials.
    return Gateway


class Tunnel:
    def __init__(self, service, handler, binary):
        self.service, self.handler, self.binary = service, handler, Path(binary)
        self.lock = threading.RLock()
        self.operations = threading.Lock()
        self.process = self.gateway = self.directory = None
        self.value = {'state': 'stopped', 'url': None, 'error': None}

    def status(self):
        with self.lock: return dict(self.value)

    def start(self, domain, token):
        public = fixed_url(domain)
        if not isinstance(token, str) or not token.strip() or len(token) > 4096 or '\n' in token:
            raise ValueError('请填写 ngrok Authtoken')
        if not self.binary.is_file() or not os.access(self.binary, os.X_OK):
            raise ValueError('缺少内置 ngrok 组件，请重新打包客户端')
        with self.operations:
            self._stop()
            gateway = ThreadingHTTPServer(('127.0.0.1', 0), gateway_handler(self.handler))
            gateway.public_url = public
            gateway.mcp_token = self.service.mcp_token
            gateway.map_service = self.service.map_service
            directory = tempfile.TemporaryDirectory(prefix='totk-ngrok-')
            config = Path(directory.name) / 'config.json'
            config.write_text(json.dumps({'version': '3', 'agent': {'web_addr': False, 'update_check': False, 'remote_management': False}}))
            config.chmod(0o600)
            environment = {k: v for k, v in os.environ.items() if k in ('PATH', 'HOME', 'TMPDIR', 'SSL_CERT_FILE', 'SSL_CERT_DIR')}
            environment['NGROK_AUTHTOKEN'] = token.strip()
            try:
                process = subprocess.Popen([str(self.binary), 'http', 'http://127.0.0.1:' + str(gateway.server_port), '--url', public, '--config', str(config), '--inspect=false', '--log', 'stdout', '--log-format', 'json'],
                                           env=environment, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            except Exception:
                gateway.server_close(); directory.cleanup(); raise
            with self.lock:
                self.process, self.gateway, self.directory = process, gateway, directory
                self.value = {'state': 'starting', 'url': None, 'error': None}
            threading.Thread(target=gateway.serve_forever, daemon=True, name='mcp-tunnel-origin').start()
            threading.Thread(target=self._read, args=(process, public), daemon=True, name='ngrok-status').start()
            return self.status()

    def _read(self, process, public):
        code = None
        try:
            for line in process.stdout:
                # Only stable status/code fields leave this process. Raw logs are discarded.
                match = re.search(r'ERR_NGROK_\d+', line)
                if match: code = match[0]
                try: event = json.loads(line)
                except ValueError: continue
                with self.lock:
                    if self.process is not process: return
                    if event.get('msg') == 'started tunnel' and event.get('url') == public:
                        self.value = {'state': 'connected', 'url': public + '/mcp', 'error': None}
                    elif event.get('msg') in ('session closed', 'client session established failed', 'failed to reconnect session'):
                        self.value = {'state': 'starting', 'url': None, 'error': '隧道连接中断，正在重连'}
            process.wait()
        finally:
            process.stdout.close()
            with self.lock:
                if self.process is process:
                    self.value = {'state': 'error', 'url': None, 'error': 'ngrok 隧道已退出，请检查令牌、固定域名及网络' + (' · ' + code if code else '')}

    def _stop(self):
        with self.lock:
            process, gateway, directory = self.process, self.gateway, self.directory
            self.process = self.gateway = self.directory = None
            self.value = {'state': 'stopped', 'url': None, 'error': None}
        if process and process.poll() is None:
            process.terminate()
            try: process.wait(timeout=3)
            except subprocess.TimeoutExpired: process.kill(); process.wait(timeout=3)
        if gateway: gateway.shutdown(); gateway.server_close()
        if directory: directory.cleanup()

    def stop(self):
        with self.operations: self._stop()
        return self.status()
