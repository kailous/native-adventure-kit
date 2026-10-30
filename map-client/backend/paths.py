"""Filesystem roots shared by source and bundled execution."""
import os
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
ROOT = Path(os.environ.get('TOTK_RESOURCE_ROOT', PROJECT_ROOT))
WEBUI = ROOT / 'webui'

def local_https_path():
    from data_packs import support_root
    return support_root() / 'LocalHTTPS'


def douyin_rules_path():
    from data_packs import support_root
    return support_root() / 'douyin-rules.json'


def danmaku_settings_path():
    from data_packs import support_root
    return support_root() / 'danmaku.json'
