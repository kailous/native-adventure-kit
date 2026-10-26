"""Versioned, immutable SQLite content packs, read without extraction."""
import hashlib
import json
import os
import re
import shutil
import sqlite3
import tempfile
import zlib
from contextlib import contextmanager
from pathlib import Path, PurePosixPath
from paths import ROOT, WEBUI

APPLICATION_ID = 0x544f544b
FORMAT_VERSION = 1
MAP_FILES = frozenset(('gamersky-archive.json', 'catalog.json', 'catalogs.json', 'regions.json', 'extra-data.json', 'surface.png', 'sky.png', 'depths.png', 'quest-points.json'))
GUIDE_FILES = frozenset(('structured-guides.json', 'main-story.json', 'quest-guide-links.json', 'compendium.json'))
MAX_RESOURCE_BYTES = 128 * 1024 * 1024


def support_root():
    return Path(os.environ.get('TOTK_SUPPORT_ROOT', Path.home() / 'Library/Application Support/TOTK Offline'))


def content_root():
    return Path(os.environ.get('TOTK_DATA_SUPPORT_ROOT', support_root()))


def resource_kind(name):
    if name in MAP_FILES or name.startswith(('tiles/', 'tiles-hd/', 'terrain/')):
        return 'map'
    if name in GUIDE_FILES or name.startswith(('offline/', 'compendium/')):
        return 'guide'
    return None


def safe_name(name):
    p = PurePosixPath(name)
    return bool(name and not p.is_absolute() and '..' not in p.parts and '\\' not in name and str(p) == name)


@contextmanager
def connect(path):
    conn = sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro&immutable=1', uri=True, timeout=5)
    try:
        yield conn
    finally:
        conn.close()


def decode_resource(payload, codec, size):
    if not 0 <= size <= MAX_RESOURCE_BYTES:
        raise ValueError('数据包资源大小无效')
    if codec == 'zlib':
        decoder = zlib.decompressobj()
        data = decoder.decompress(payload, size + 1)
        if not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
            raise ValueError('数据包压缩资源无效')
    elif codec == 'raw':
        data = payload
    else:
        raise ValueError('不支持的数据包压缩格式')
    if len(data) != size:
        raise ValueError('数据包资源长度不一致')
    return data


def manifest(path):
    with connect(path) as conn:
        if conn.execute('PRAGMA application_id').fetchone()[0] != APPLICATION_ID or conn.execute('PRAGMA user_version').fetchone()[0] != FORMAT_VERSION:
            raise ValueError('不是兼容的 TOTK 数据包')
        row = conn.execute("SELECT value FROM metadata WHERE key='pack'").fetchone()
        info = json.loads(row[0]) if row else {}
    if info.get('format') != 'totkpack/1' or info.get('kind') not in ('map', 'guide') or info.get('contentSchema') != 1 or info.get('pointSchema') != 1:
        raise ValueError('数据包类型或内容版本不兼容')
    for key in ('id', 'version'):
        if not isinstance(info.get(key), str) or not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9._-]{0,63}', info[key]):
            raise ValueError('数据包标识无效')
    return info


def file_hash(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def validate(path):
    """Full check before installation; never trust a filename or extension."""
    info = manifest(path)
    with connect(path) as conn:
        if conn.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('数据包数据库损坏')
        count = 0
        for name, payload, codec, size, digest in conn.execute('SELECT path,data,codec,size,sha256 FROM resources'):
            if not safe_name(name) or resource_kind(name) != info['kind']:
                raise ValueError('数据包包含非法资源路径')
            data = decode_resource(payload, codec, size)
            if hashlib.sha256(data).hexdigest() != digest:
                raise ValueError('数据包资源校验失败: ' + name)
            count += 1
        if count != info.get('resources'):
            raise ValueError('数据包资源数量不一致')
        required = ('gamersky-archive.json', 'catalogs.json', 'regions.json', 'terrain/index.json', 'terrain/coverage.json') if info['kind'] == 'map' else ('structured-guides.json', 'offline/index.json', 'compendium.json', 'main-story.json')
        for name in required:
            if not conn.execute('SELECT 1 FROM resources WHERE path=?', (name,)).fetchone():
                raise ValueError('数据包缺少必要资源: ' + name)
        if info['kind'] == 'map':
            terrain_row = conn.execute("SELECT data,codec,size FROM resources WHERE path='terrain/index.json'").fetchone()
            terrain = json.loads(decode_resource(*terrain_row))
            for region in terrain.get('regions', []):
                for key in ('heightFile', 'meshFile'):
                    name = region.get(key)
                    if name and (not name.startswith('terrain/') or not safe_name(name) or not conn.execute('SELECT 1 FROM resources WHERE path=?', (name,)).fetchone()):
                        raise ValueError('地形索引引用了缺失资源')
            count = 0
            for layer, zoom, x, y, png, digest in conn.execute('SELECT layer,zoom,x,y,png,sha256 FROM tiles'):
                limit = (9 if layer == 's' else 10) * 2 ** (zoom - 3) if isinstance(zoom, int) and 3 <= zoom <= 7 else 0
                if layer not in ('s', 'd', 'k') or not 0 <= x < limit or not 0 <= y < limit or not png.startswith(b'\x89PNG\r\n\x1a\n') or hashlib.sha256(png).hexdigest() != digest:
                    raise ValueError('地图瓦片校验失败')
                count += 1
            if count != info.get('tiles'):
                raise ValueError('地图瓦片数量不一致')
    return info


def read_registry():
    path = content_root() / 'DataPacks/registry.json'
    if not path.exists():
        return {'schema': 1, 'active': {}, 'installed': []}
    value = json.loads(path.read_text())
    if value.get('schema') != 1:
        raise ValueError('数据包注册表版本不兼容')
    return value


def active_pack(kind):
    override = os.environ.get('TOTK_' + kind.upper() + '_PACK')
    if override:
        path = Path(override)
    else:
        entry = read_registry()['active'].get(kind)
        if not entry:
            return None
        path = Path(entry['path'])
    info = manifest(path)
    if info['kind'] != kind:
        raise ValueError('数据包类型不匹配')
    return path


def read_resource(name):
    if not safe_name(name):
        return None
    kind = resource_kind(name)
    if kind:
        try:path = active_pack(kind)
        except (OSError, ValueError, sqlite3.Error, KeyError):return None
        if path:
            with connect(path) as conn:
                row = conn.execute('SELECT data,codec,size,sha256 FROM resources WHERE path=?', (name,)).fetchone()
            if row:
                data = decode_resource(*row[:3])
                if hashlib.sha256(data).hexdigest() != row[3]:
                    raise ValueError('数据包资源校验失败')
                return data
            return None
    # Source-tree development remains usable; packaged apps contain no content fallback.
    path = (WEBUI / name).resolve()
    if path.is_relative_to(WEBUI.resolve()) and path.is_file():
        return path.read_bytes()
    return None


def read_json(name, default=None):
    data = read_resource(name)
    return json.loads(data) if data is not None else default


def pack_status():
    result = {}
    for kind in ('map', 'guide'):
        try:
            path = active_pack(kind)
            result[kind] = {'installed': bool(path), **({**manifest(path), 'bytes': path.stat().st_size} if path else {})}
        except (OSError, ValueError, sqlite3.Error, KeyError) as error:
            result[kind] = {'installed': False, 'error': str(error)}
    return result


def install_pack(source, reference=False):
    """Stage, verify and atomically activate; existing versions stay recoverable."""
    source = Path(source).resolve()
    initial = manifest(source)
    base = content_root() / 'DataPacks'
    base.mkdir(parents=True, exist_ok=True)
    lock = base / '.install-lock'
    try:
        lock.mkdir()
    except FileExistsError:
        raise ValueError('另一个数据包导入正在进行')
    staged = None
    try:
        if reference:
            path = source
        else:
            staging = base / 'Staging'
            staging.mkdir(exist_ok=True)
            fd, temporary = tempfile.mkstemp(suffix='.totkpack', dir=staging)
            os.close(fd)
            staged = Path(temporary)
            shutil.copyfile(source, staged)
            path = staged
        info = validate(path)
        if info['kind'] != initial['kind']:
            raise ValueError('数据包在导入过程中发生变化')
        digest = file_hash(path)
        if not reference:
            folder = base / ('Maps' if info['kind'] == 'map' else 'Guides') / info['id']
            folder.mkdir(parents=True, exist_ok=True)
            destination = folder / (info['version'] + '-' + digest[:12] + '.totkpack')
            if destination.exists():
                if file_hash(destination) != digest:
                    raise ValueError('现有数据包校验失败')
                staged.unlink()
            else:
                staged.replace(destination)
            staged = None
            path = destination
        registry = read_registry()
        entry = {'kind': info['kind'], 'id': info['id'], 'version': info['version'], 'path': str(path), 'sha256': digest, 'reference': reference}
        registry['installed'] = [e for e in registry['installed'] if e['path'] != str(path)] + [entry]
        registry['active'][info['kind']] = entry
        fd, temporary = tempfile.mkstemp(dir=base, suffix='.json')
        with os.fdopen(fd, 'w') as stream:
            json.dump(registry, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, base / 'registry.json')
        return entry
    finally:
        if staged is not None:
            staged.unlink(missing_ok=True)
        lock.rmdir()
