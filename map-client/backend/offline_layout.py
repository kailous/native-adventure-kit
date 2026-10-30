"""One-time, resumable migration of native map state and content directories.

No game profile, control settings, browser storage or system trust is modified.
An existing destination with different state is never overwritten.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import tempfile


def root(home=None):
    return (Path(home) if home else Path.home()) / 'Library/Application Support/MacNativeGames/TOTK/Offline'


def sha256(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(4*1024*1024),b''):h.update(block)
    return h.hexdigest()


def write_json(path,value):
    fd,name=tempfile.mkstemp(prefix='.layout-',dir=path.parent)
    try:
        with os.fdopen(fd,'w') as f:
            json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
        os.replace(name,path)
    finally:
        if os.path.exists(name):os.unlink(name)


def live_connection(directory):
    p=directory/'connection.json'
    if not p.exists():return False
    try:data=json.loads(p.read_text())
    except (ValueError,OSError):return False
    pid=data.get('pid')
    if type(pid) is not int or pid<=0:return False
    try:os.kill(pid,0);return True
    except ProcessLookupError:return False
    except PermissionError:return True


def file_hashes(path):
    if path.is_symlink():raise ValueError('Migration refuses symlinks: '+str(path))
    if path.is_file():return {'':sha256(path)}
    result={}
    for p in path.rglob('*'):
        if p.is_symlink():raise ValueError('Migration refuses symlinks: '+str(p))
        if p.is_file():result[str(p.relative_to(path))]=sha256(p)
    return result


def migrate(home=None):
    home=Path(home) if home else Path.home()
    base=root(home);state=base/'State';packs=base/'DataPacks'
    old_state=home/'Library/Application Support/TOTK Native Map'
    old_content=home/'Library/Application Support/TOTK Offline'
    old_packs=old_content/'DataPacks'
    for p in [base,state,packs,old_state,old_packs]:
        if p.is_symlink():raise ValueError('Migration refuses symlink roots: '+str(p))
    # Refuse before creating new state when a legacy or another current service owns it.
    if live_connection(old_state) or live_connection(state):
        raise RuntimeError('地图服务仍在运行，请先退出其他地图客户端后重试；原数据未覆盖')
    base.mkdir(parents=True,exist_ok=True,mode=0o700);state.mkdir(exist_ok=True,mode=0o700)
    lock=state/'.layout-migration.lock'
    fd=os.open(lock,os.O_CREAT|os.O_RDWR,0o600)
    try:
        try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise RuntimeError('另一个地图数据迁移正在进行') from None
        receipt_path=state/'layout-migration.json'
        if receipt_path.exists():
            receipt=json.loads(receipt_path.read_text())
            if receipt.get('schema')!=1:raise ValueError('Unknown layout migration receipt')
        else:receipt={'schema':1,'status':'preparing','moved':[],'packPathsRewritten':0}
        entries=sorted(old_state.iterdir()) if old_state.exists() else []
        for p in entries:
            if p.name in ('.layout-migration.lock','layout-migration.json'):raise ValueError('Reserved legacy state filename')
            if (state/p.name).exists() or (state/p.name).is_symlink():
                raise RuntimeError('旧/新目录均有同名状态，保留原件，拒绝覆盖: '+p.name)
            file_hashes(p)
        if old_packs.exists() and packs.exists():
            raise RuntimeError('旧/新目录均有DataPacks，保留原件，拒绝合并覆盖')
        source_packs=old_packs if old_packs.exists() else packs
        registry_path=source_packs/'registry.json';registry=None;rewritten=[]
        if registry_path.exists():
            registry=json.loads(registry_path.read_text())
            if registry.get('schema')!=1:raise ValueError('Unknown DataPacks registry')
            # Rewrite only owned files below the exact old pack root. External references stay external.
            for e in list(registry.get('installed',[]))+list(registry.get('active',{}).values()):
                if not isinstance(e,dict) or not isinstance(e.get('path'),str):raise ValueError('Invalid pack registry entry')
                p=Path(e['path'])
                try:relative=p.relative_to(old_packs)
                except ValueError:relative=None
                if relative is not None:
                    if '..' in relative.parts:raise ValueError('Invalid pack registry path')
                    existing=source_packs/relative
                    if not existing.is_file() or existing.is_symlink():raise ValueError('Missing managed data pack: '+str(existing))
                    if sha256(existing)!=e.get('sha256'):raise ValueError('Data pack digest mismatch: '+str(existing))
                    e['path']=str(packs/relative);rewritten.append(str(relative))
                elif not e.get('reference',False) and not p.is_relative_to(packs):
                    raise ValueError('Managed pack outside expected root')
        receipt['planned']=[{'from':str(p),'to':str(state/p.name),'files':file_hashes(p)} for p in entries]
        if live_connection(old_state) or live_connection(state):raise RuntimeError('地图服务已重新启动，停止迁移')
        receipt['status']='moving';write_json(receipt_path,receipt)
        # Every completed top-level rename is journalled. A restart can continue with remaining legacy files.
        for p in entries:
            expected=file_hashes(p);target=state/p.name;p.rename(target)
            if file_hashes(target)!=expected:raise RuntimeError('Moved state digest mismatch: '+p.name)
            receipt['moved'].append({'from':str(p),'to':str(target),'files':expected});write_json(receipt_path,receipt)
        if old_packs.exists():
            old_packs.rename(packs)
            receipt['moved'].append({'from':str(old_packs),'to':str(packs),'kind':'data-packs'});write_json(receipt_path,receipt)
        else:packs.mkdir(exist_ok=True)
        if registry is not None and rewritten:
            backup=state/'data-pack-registry-before-layout.json'
            if not backup.exists():write_json(backup,json.loads((packs/'registry.json').read_text()))
            write_json(packs/'registry.json',registry)
            receipt['packPathsRewritten']+=len(set(rewritten))
        for p in [old_state,old_content]:
            if p.exists() and not any(p.iterdir()):p.rmdir()
        receipt['status']='complete';write_json(receipt_path,receipt)
        return {'status':'complete','state':str(state),'dataPacks':str(packs),'movedEntries':len(receipt['moved']),'packPathsRewritten':receipt['packPathsRewritten']}
    finally:os.close(fd)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--migrate-offline-layout',action='store_true')
    ap.add_argument('--home',type=Path,help='Explicit isolated test home; never used by normal App startup')
    args=ap.parse_args()
    try:print(json.dumps(migrate(args.home),ensure_ascii=False))
    except Exception as e:raise SystemExit(str(e)) from e


if __name__=='__main__':main()
