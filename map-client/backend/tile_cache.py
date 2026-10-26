"""Fixed-source HD map tiles, cached locally for subsequent offline use."""
import os,urllib.request,urllib.error,threading,tempfile,struct,zlib
from pathlib import Path
from server import ROOT
LAYERS={'s':'ground','d':'underground','k':'sky'}
def empty_tile():
 def chunk(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
 return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',256,256,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(b'\x00'*(256*(1+256*4))))+chunk(b'IEND',b'')
DOWNLOADS=threading.BoundedSemaphore(4)
LOCK=threading.Lock();PENDING={}
def tile(layer,zoom,x,y,allow_download=False):
 if layer not in LAYERS or not 3<=zoom<=7:raise ValueError('Invalid tile')
 count=(9 if layer=='s' else 10)*2**(zoom-3)
 if not (0<=x<count and 0<=y<count):raise ValueError('Invalid tile coordinates')
 from offline_map import read_tile
 archived=read_tile(layer,zoom,x,y)
 if archived is not None:return archived
 bundled=ROOT/f'webui/tiles-hd/{layer}/{zoom}/{x}_{y}.png'
 if bundled.exists():return bundled.read_bytes()
 cache=Path(os.environ.get('TOTK_TILE_CACHE',str(ROOT/'tile-cache')));path=cache/layer/str(zoom)/f'{x}_{y}.png'
 with LOCK:
  lock=PENDING.setdefault(str(path),threading.Lock())
 try:
  with lock:
   if path.exists():return path.read_bytes()
   if zoom==3:
    base=ROOT/f'webui/tiles/{layer}/{x}_{y}.png'
    if base.exists():return base.read_bytes()
   if not allow_download:raise FileNotFoundError('高清瓦片尚未存入离线地图，运行时不会联网下载')
   url=f'https://image.gamersky.com/webimg13/db/game_map/zelda_tok/tilesHD_Zeldamaps_5/{LAYERS[layer]}/{zoom}/{x}_{y}.png'
   with DOWNLOADS:
    try:
     with urllib.request.urlopen(url,timeout=15) as response:data=response.read(2*1024*1024)
    except urllib.error.HTTPError as exc:
     if exc.code!=404:raise
     data=empty_tile() # Padding outside the source tile pyramid.
   if not data.startswith(b'\x89PNG\r\n\x1a\n') or len(data)>=2*1024*1024:raise ValueError('Invalid PNG tile')
   path.parent.mkdir(parents=True,exist_ok=True)
   with tempfile.NamedTemporaryFile(dir=path.parent,delete=False) as temp:temp.write(data);name=temp.name
   try:os.replace(name,path)
   finally:
    if os.path.exists(name):os.unlink(name)
   return data
 finally:
  # Retain the small per-path lock map to avoid racing queued downloads.
  pass
