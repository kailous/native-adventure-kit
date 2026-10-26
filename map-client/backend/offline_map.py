"""Indexed read-only offline map archive; never accesses the network."""
import sqlite3,hashlib
from contextlib import closing
from server import ROOT
from data_packs import active_pack, connect

def read_tile(layer,zoom,x,y):
 try:path=active_pack('map') or ROOT/'webui/map-tiles.sqlite'
 except (OSError,ValueError,sqlite3.Error):return None
 if not path.exists():return None
 with closing(sqlite3.connect(path.as_uri()+'?mode=ro',uri=True,timeout=5)) as conn:
  is_pack=path.suffix=='.totkpack'
  result=conn.execute('SELECT png'+(',sha256' if is_pack else '')+' FROM tiles WHERE layer=? AND zoom=? AND x=? AND y=?',(layer,zoom,x,y)).fetchone()
 if result and is_pack and hashlib.sha256(result[0]).hexdigest()!=result[1]:raise ValueError('地图瓦片校验失败')
 return result[0] if result else None


def archive_info():
 try:path=active_pack('map') or ROOT/'webui/map-tiles.sqlite'
 except (OSError,ValueError,sqlite3.Error):return {'complete':False}
 if not path.exists():return {'complete':False}
 try:
  import json
  with closing(sqlite3.connect(path.as_uri()+'?mode=ro',uri=True,timeout=5)) as conn:
   row=conn.execute("SELECT value FROM metadata WHERE key='verification'").fetchone()
  return json.loads(row[0]) if row else {'complete':False}
 except sqlite3.Error:return {'complete':False}
