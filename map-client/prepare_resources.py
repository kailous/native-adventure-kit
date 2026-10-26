"""Create a data-free map shell; optional resources are explicit external inputs."""
import json
from pathlib import Path, PurePosixPath
import shutil
import struct
import zlib

ROOT = Path(__file__).resolve().parent
REFERENCE_FILES = ('save-reference.json', 'towers.json', 'quest-reference.json', 'compendium-save-reference.json', 'ui-assets.json')
ART_DIRECTORIES = ('branding', 'icons/game', 'item-icons', 'amiibo', 'ui-assets')


def png():
    def chunk(kind, payload):
        return struct.pack('>I', len(payload)) + kind + payload + struct.pack('>I', zlib.crc32(kind + payload) & 0xffffffff)
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(b'\0\x10\x20\x20')) + chunk(b'IEND', b'')


def prepare(destination, supplied=None):
    if destination.exists():
        raise ValueError('Resource destination must be new')
    destination.mkdir(parents=True)
    web = destination / 'webui'
    shutil.copytree(ROOT / 'webui', web)
    objects = {k: [] for k in ('shrines', 'lightroots', 'towers', 'hidden_koroks', 'carry_koroks', 'bubbuls', 'caves', 'wells', 'chasms', 'old_maps', 'sages_wills', 'addison_signposts', 'schema_stones', 'yiga_schematics')}
    defaults = {
        'save-reference.json': {'cats': [], 'objs': objects}, 'towers.json': [],
        'quest-reference.json': {'quests': [], 'pointQuests': {}},
        'compendium-save-reference.json': {'books': {}, 'armor': {}, 'variants': {}, 'pointArmor': {}, 'materials': {}, 'materialNamesHash': 0, 'materialStockHash': 0, 'armorNamesHash': 0, 'enums': {'Unopened': 0, 'TakePhoto': 1, 'Buy': 2}},
        'ui-assets.json': {}, 'gamersky-archive.json': {'points': []}, 'catalogs.json': {},
        'regions.json': [], 'compendium.json': {'entries': []}, 'main-story.json': {},
        'structured-guides.json': {}, 'quest-guide-links.json': {}}
    for name, content in defaults.items():
        (web / name).write_text(json.dumps(content, ensure_ascii=False) + '\n')
    for name in json.loads((ROOT / 'resource-requests.json').read_text())['neutralPlaceholders']:
        path = PurePosixPath(name)
        if path.is_absolute() or '..' in path.parts:
            raise ValueError('Unsafe placeholder path')
        target = web / name
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.suffix == '.png':
            target.write_bytes(png())
        else:
            target.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><circle cx="12" cy="12" r="7" fill="none" stroke="#b7c9c1" stroke-width="2"/></svg>\n')
    if supplied:
        supplied = Path(supplied).expanduser().resolve()
        for name in REFERENCE_FILES:
            source = supplied / 'webui' / name
            if source.exists():
                if source.is_symlink() or not source.is_file():
                    raise ValueError('External resources must be ordinary files')
                json.loads(source.read_text())
                shutil.copy2(source, web / name)
        for folder in ART_DIRECTORIES:
            source = supplied / 'webui' / folder
            if source.is_symlink():
                raise ValueError('External resource directories must not be links')
            if source.is_dir():
                for path in source.rglob('*'):
                    if path.is_symlink():
                        raise ValueError('External resource links are not allowed')
                    if path.is_file() and path.suffix.lower() in ('.svg', '.png', '.jpg', '.jpeg', '.webp'):
                        target = web / folder / path.relative_to(source)
                        target.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(path, target)
    (destination / 'RESOURCE_SCOPE.json').write_text(json.dumps({
        'dataPacksIncluded': False, 'defaultReferences': 'empty placeholders',
        'defaultBranding': 'neutral generated shapes', 'externalResourcesUsed': bool(supplied)}, indent=2) + '\n')
    return destination
