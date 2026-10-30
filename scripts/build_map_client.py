#!/usr/bin/env python3
"""Build the native map desktop App from exported sources, with external outputs only."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import plistlib
import platform
import shutil
import subprocess
import sys

KIT = Path(__file__).resolve().parents[1]
SOURCE = KIT / 'map-client'


def build(work, native_source, resources=None, ngrok=None, douyin_source=None):
    if work.exists() or work.is_symlink() or work == KIT or KIT in work.parents:
        raise ValueError('Use a new build directory outside this repository')
    actions = native_source / 'games/totk/assets/input-actions.json'
    lock = json.loads((KIT / 'upstream.lock.json').read_text())
    expected = next(x['sha256'] for x in lock['files'] if x['path'] == 'games/totk/assets/input-actions.json')
    if not actions.is_file() or hashlib.sha256(actions.read_bytes()).hexdigest() != expected:
        raise ValueError('--native-source must be assembled from this kit lock; input action definitions differ')
    if importlib.util.find_spec('PyInstaller') is None or importlib.util.find_spec('PIL') is None:
        raise ValueError('Install map-client/requirements-build.txt in the chosen build Python environment')
    if platform.system() != 'Darwin' or platform.machine() != 'arm64':
        raise ValueError('Native map App packaging requires an Apple silicon Mac')
    if douyin_source is None:
        raise ValueError('--douyin-source must point to the external DouyinLiveWebFetcher source; live support must not be silently omitted')
    receiver = Path(douyin_source).expanduser().resolve()
    receiver_lock = json.loads((SOURCE / 'douyin-source.json').read_text())
    for row in receiver_lock['files']:
        path = receiver / row['path']
        if path.is_symlink() or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != row['sha256']:
            raise ValueError('External receiver source mismatch: ' + row['path'])
    import py_mini_racer
    mini = Path(py_mini_racer.__file__).parent
    work.mkdir(parents=True)
    logs = work / 'logs'
    logs.mkdir()
    spec = importlib.util.spec_from_file_location('map_resources', SOURCE / 'prepare_resources.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    resource_stage = module.prepare(work / 'resources', resources)
    app = work / 'Native Adventure Map.app'
    contents = app / 'Contents'
    (contents / 'MacOS').mkdir(parents=True)
    target_resources = contents / 'Resources'
    shutil.copytree(resource_stage, target_resources)
    shutil.copy2(actions, target_resources / 'input-actions.json')
    env = dict(os.environ, PYINSTALLER_CONFIG_DIR=str(work / 'pyinstaller-config'),
               CLANG_MODULE_CACHE_PATH=str(work / 'clang-cache'))
    def run(command, name):
        with (logs / name).open('w') as log:
            subprocess.run([str(x) for x in command], check=True, env=env, stdout=log, stderr=subprocess.STDOUT)
    receiver_stage = work / 'receiver'
    receiver_stage.mkdir()
    shutil.copy2(SOURCE / 'douyin/danmaku_hook.py', receiver_stage / 'danmaku_hook.py')
    for row in receiver_lock['files']:
        target = receiver_stage / 'DouyinLiveWebFetcher' / row['path']
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(receiver / row['path'], target)
    run([sys.executable, '-m', 'PyInstaller' , '--noconfirm', '--clean', '--onedir', '--name', 'totk-service',
         '--paths', SOURCE / 'backend', '--distpath', work / 'service-dist', '--workpath', work / 'pyinstaller',
         '--specpath', work / 'pyinstaller-config',
         '--paths', receiver_stage, '--paths', receiver_stage / 'DouyinLiveWebFetcher',
         '--hidden-import', 'danmaku_hook', '--hidden-import', 'liveMan', '--hidden-import', 'ac_signature',
         '--hidden-import', 'protobuf.douyin', '--collect-submodules', 'py_mini_racer',
         '--add-binary', str(mini / 'libmini_racer.dylib') + ':.',
         '--add-data', str(mini / 'icudtl.dat') + ':.', '--add-data', str(mini / 'snapshot_blob.bin') + ':.',
         '--add-data', str(receiver_stage) + ':douyin', SOURCE / 'desktop/backend_entry.py'], 'pyinstaller.log')
    shutil.copytree(work / 'service-dist/totk-service', target_resources / 'backend', symlinks=True)
    files = ['main.swift', 'Client.swift', 'ConsoleStyle.swift', 'TunnelUI.swift', 'DataPacks.swift', 'NativeGame.swift']
    run(['swiftc', '-O', '-module-cache-path', work / 'swift-cache', '-target', 'arm64-apple-macosx12.0',
         *[SOURCE / 'desktop' / name for name in files], '-o', contents / 'MacOS/TOTK Offline',
         '-framework', 'AppKit', '-framework', 'WebKit', '-framework', 'Security'], 'swift.log')
    info = {'CFBundleExecutable': 'TOTK Offline', 'CFBundleIdentifier': 'local.totk.native-map',
            'CFBundleName': 'Native Adventure Map', 'CFBundleDisplayName': 'Native Adventure Map',
            'CFBundlePackageType': 'APPL', 'CFBundleShortVersionString': '2.0.24', 'CFBundleVersion': '124',
            'TOTKNativeEdition': True, 'LSMinimumSystemVersion': '12.0', 'NSHighResolutionCapable': True,
            'NSAppTransportSecurity': {'NSAllowsLocalNetworking': True},
            'NSLocalNetworkUsageDescription': '允许同一局域网访问本机地图服务。',
            'CFBundleDocumentTypes': [{'CFBundleTypeExtensions': ['totkpack'], 'CFBundleTypeName': 'Map data pack', 'CFBundleTypeRole': 'Viewer'}]}
    with (contents / 'Info.plist').open('wb') as stream:
        plistlib.dump(info, stream)
    if ngrok:
        supplied = Path(ngrok).expanduser().resolve()
        manifest = json.loads((SOURCE / 'desktop/tunnel-agent.json').read_text())
        if hashlib.sha256(supplied.read_bytes()).hexdigest() != manifest['sha256']:
            raise ValueError('ngrok does not match the recorded binary; review updates explicitly')
        folder = target_resources / 'tunnel-agent'
        folder.mkdir()
        shutil.copy2(supplied, folder / 'ngrok')
        (folder / 'ngrok').chmod(0o755)
        (folder / 'CREDITS.txt').write_bytes(subprocess.check_output([str(supplied), 'credits']))
        (folder / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    run([target_resources / 'backend/totk-service', '--douyin-worker', '--self-test'], 'receiver-self-test.log')
    shutil.copy2(KIT / 'LICENSE', target_resources / 'PROJECT-LICENSE.txt')
    for name in ('com.apple.FinderInfo', 'com.apple.ResourceFork'):
        subprocess.run(['xattr', '-r', '-d', name, str(app)], capture_output=True)
    run(['codesign', '--force', '--deep', '--sign', '-', app], 'codesign.log')
    run(['codesign', '--verify', '--deep', '--strict', app], 'codesign-verify.log')
    print(app)
    print('Built and signed only. App/service/game not launched; no data packs included.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', required=True, type=Path)
    parser.add_argument('--native-source', required=True, type=Path)
    parser.add_argument('--resources', type=Path, help='Optional externally authorized resource root; allowlisted art/reference files only')
    parser.add_argument('--douyin-source', required=True, type=Path, help='External, hash-verified DouyinLiveWebFetcher source directory')
    parser.add_argument('--ngrok-binary', type=Path, help='Optional user-supplied pinned ngrok agent; never downloaded by this builder')
    args = parser.parse_args()
    requested = args.work.expanduser().absolute()
    work = requested.parent.resolve() / requested.name
    build(work, args.native_source.expanduser().resolve(), args.resources, args.ngrok_binary, args.douyin_source)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        print('Map build stopped: ' + str(exc), file=sys.stderr)
        sys.exit(1)
