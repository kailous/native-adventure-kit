#!/usr/bin/env python3
"""Generate a credential-free private plugin, or perform a read-only MCP handshake."""
import argparse
import json
from pathlib import Path
import sys
import urllib.error
import urllib.request
from urllib.parse import urlsplit
import zipfile
from release_consent import require_consent


def validate_url(value, remote=False):
    parsed = urlsplit(value)
    if parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path != '/mcp':
        raise ValueError('MCP URL 必须以 /mcp 结尾，不含凭据、查询或片段')
    if not parsed.hostname or (parsed.scheme != 'https' and not
            (not remote and parsed.scheme == 'http' and parsed.hostname in ('localhost', '127.0.0.1', '::1'))):
        raise ValueError('远程必须使用 HTTPS；HTTP 仅允许本机回环地址')
    return value


def guide_files():
    here = Path(__file__).resolve()
    if (here.parent / 'AI_GUIDE.md').is_file():
        return {**{name: here.parent / name for name in ('AI_GUIDE.md', 'MCP_USER_GUIDE.md', 'PLUGIN_GUIDE.md')}, '使用协议.md': here.parent.parent / '使用协议.md'}
    docs = here.parents[2] / 'docs'
    return {'AI_GUIDE.md': docs / 'native-ai-guide.md',
            'MCP_USER_GUIDE.md': docs / 'native-mcp-user-guide.md',
            'PLUGIN_GUIDE.md': docs / 'native-plugin-guide.md',
            '使用协议.md': here.parents[2] / 'MacNativeGames/docs/usage-agreement.md'}


def generate(output, url=None):
    if url:
        validate_url(url, remote=True)
    output.mkdir(parents=True, exist_ok=False)
    plugin = output / 'totk-native-helper'
    skill = plugin / 'skills/totk-native-guide'
    refs = skill / 'references'
    refs.mkdir(parents=True)
    for name, source in guide_files().items():
        text = source.read_text()
        for old, new in [('native-mcp-user-guide.md', 'MCP_USER_GUIDE.md'),
                         ('native-ai-guide.md', 'AI_GUIDE.md'),
                         ('native-plugin-guide.md', 'PLUGIN_GUIDE.md')]:
            text = text.replace(old, new)
        (refs / name).write_text(text)
    manifest = {'$schema': 'https://agent-plugins.org/schemas/1.0.0/plugin.schema.json',
                'name': 'totk-native-helper', 'version': '1.0.0',
                'description': 'Use your own native TOTK map MCP with portable agent guidance.',
                'author': {'name': 'TOTK native helper'},
                'extensions': {'com.openai': {'interface': {
                    'displayName': 'TOTK 原生助手', 'shortDescription': '连接自己的地图与原生游戏',
                    'longDescription': '个人地图、攻略与原生游戏工具指导；需使用者自己的 MCP 服务和协议确认。',
                    'developerName': 'TOTK native helper', 'category': 'Productivity',
                    'capabilities': ['Interactive'], 'defaultPrompt': '帮我接入自己的 TOTK 地图 MCP，先阅读使用协议并做只读验证。'}}}}
    (plugin / 'plugin.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    (skill / 'SKILL.md').write_text('''---
name: totk-native-guide
description: Help a user connect their own native TOTK map MCP, query guides, or use authorized native game tools.
---

先提供 references/使用协议.md 全文入口，说明合法输入、许可与远程/游戏风险，按当前任务取得明确授权；不能把协作确认作为 MIT 权利的附加条件，也不得伪造用户回复。
随后阅读 references/AI_GUIDE.md、references/MCP_USER_GUIDE.md 和 references/PLUGIN_GUIDE.md。
使用者的真实 MCP 连接由宿主配置；没有工具时只协助配置，不能声称已连接。
先发现实际 tools/list 及 schema。只读验证；未经明确游戏任务授权，不调用写入工具。
不要复用原作者服务、收集秘密或覆盖现有配置。
''')
    if url:
        mcp = {'$schema': 'https://agent-plugins.org/schemas/1.0.0/mcp.schema.json',
               'mcpServers': {'totk-native': {'type': 'streamable-http', 'url': url,
                   'extensions': {'com.openai': {'auth': {'type': 'api_key', 'headerScheme': 'bearer'}}}}}}
        (plugin / 'mcp.json').write_text(json.dumps(mcp, ensure_ascii=False, indent=2) + '\n')
    with zipfile.ZipFile(output / 'totk-native-helper.zip', 'x', zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(plugin.rglob('*')):
            if path.is_file():
                archive.write(path, path.relative_to(output))
    print('插件文件已生成；尚未部署服务、安装到账号或验证 MCP 连接。')


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # Never forward a bearer token to a redirect destination.


def check(config):
    servers = json.loads(config.read_text())['mcpServers']
    if not isinstance(servers, dict) or len(servers) != 1:
        raise ValueError('请使用地图工具复制的单服务配置')
    server = next(iter(servers.values()))
    url = validate_url(server['url'])
    headers = dict(server.get('headers', {}))
    if not str(headers.get('Authorization', '')).startswith('Bearer '):
        raise ValueError('缺少地图服务 Bearer 认证；请重新复制配置')
    headers.update({'Content-Type': 'application/json', 'Accept': 'application/json, text/event-stream'})
    opener = urllib.request.build_opener(NoRedirect)

    def rpc(message):
        request = urllib.request.Request(url, json.dumps(message).encode(), headers, method='POST')
        with opener.open(request, timeout=20) as response:
            payload = response.read(8 * 1024 * 1024 + 1)
            if len(payload) > 8 * 1024 * 1024:
                raise ValueError('响应过大')
            if 'id' not in message:
                return None
            data = json.loads(payload)
            if data.get('id') != message['id'] or 'error' in data:
                raise ValueError('MCP 返回协议错误；未输出服务端详情以保护隐私')
            return data['result']

    result = rpc({'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {
        'protocolVersion': '2025-03-26', 'capabilities': {},
        'clientInfo': {'name': 'totk-release-check', 'version': '1.0.0'}}})
    version = result['protocolVersion']
    if version not in ('2024-11-05', '2025-03-26', '2025-06-18', '2025-11-25'):
        raise ValueError('服务协商了不支持的协议版本')
    headers['MCP-Protocol-Version'] = version
    rpc({'jsonrpc': '2.0', 'method': 'notifications/initialized'})
    tools = rpc({'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list'})['tools']
    if not isinstance(tools, list) or not all(isinstance(t, dict) and isinstance(t.get('name'), str)
            and isinstance(t.get('inputSchema'), dict) for t in tools):
        raise ValueError('工具列表格式错误')
    print(f'只读握手成功：协议 {version}，工具 {len(tools)} 个。未调用地图或游戏工具。')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    gen = sub.add_parser('generate')
    gen.add_argument('--out', type=Path, required=True)
    gen.add_argument('--url')
    probe = sub.add_parser('check')
    probe.add_argument('--config', type=Path, required=True)
    for command in (gen, probe):
        command.add_argument('--consent', help='Exact reply already provided by the human; never fabricate it')
    args = parser.parse_args()
    require_consent(args.consent)
    if args.action == 'generate':
        generate(args.out, args.url)
    else:
        check(args.config)


if __name__ == '__main__':
    try:
        main()
    except urllib.error.HTTPError as exc:
        print(f'HTTP {exc.code}；请按教程检查认证/传输。未输出凭据。', file=sys.stderr)
        sys.exit(1)
    except (ValueError, KeyError, OSError) as exc:
        # Network errors may embed the private endpoint; keep diagnostics bounded.
        print(str(exc) if isinstance(exc, ValueError) else '操作失败；检查私人配置、文件路径和网络，不要公开凭据。', file=sys.stderr)
        sys.exit(1)
