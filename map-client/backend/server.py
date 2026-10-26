"""Local TOTK map, read-only saves, experimental game control and HTTP MCP."""
import argparse,json,struct,threading,os,sys,secrets,hmac,time,ipaddress,hashlib,copy,io,mimetypes
from pathlib import Path
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from urllib.parse import urlsplit,parse_qs,unquote
from http.cookies import SimpleCookie,CookieError
from paths import ROOT, WEBUI
from data_packs import read_resource, resource_kind, pack_status, install_pack
def default_save_roots():
 base=Path.home()/'Library/Application Support'
 if os.environ.get('TOTK_CLIENT_EDITION')=='native':return [base/'MacNativeGames/TOTK/profile']
 return [base/'Ryujinx/bis/user/save',base/'Ryubing/bis/user/save',base/'yuzu/nand/user/save',base/'suyu/nand/user/save']
def parse_flags(data):
 if len(data)<48 or struct.unpack_from('<I',data)[0]!=0x01020304:raise ValueError('不是有效的王国之泪 progress.sav')
 flags={}
 for off in range(0x28,len(data)-7,8):
  key,value=struct.unpack_from('<II',data,off)
  if key==0xa3db7114:
   if value<off+8 or value>len(data):raise ValueError('存档索引不完整')
   return flags
  flags[key]=value
 raise ValueError('存档缺少索引结束标记')
class SaveSource:
 def __init__(self,roots):
  self.roots,self.lock=roots,threading.Lock();self.cached=None;self.signature=None;self.watch_stop=threading.Event()
 def start(self):
  def watch():
   while not self.watch_stop.is_set():
    self.newest();self.watch_stop.wait(.5)
  threading.Thread(target=watch,name='totk-save-watch',daemon=True).start()
 def stop(self):self.watch_stop.set()
 def newest(self):
  with self.lock:
   candidates,errors=[],[];files=[]
   for root in self.roots:
    files.extend([root] if root.is_file() else root.rglob('progress.sav'))
   try:signature=tuple(sorted((str(p),p.stat().st_mtime_ns,p.stat().st_ctime_ns,p.stat().st_size) for p in files))
   except OSError:signature=None
   if signature is not None and signature==self.signature and self.cached:return self.cached[0],copy.deepcopy(self.cached[1])
   for root in self.roots:
    paths=[root] if root.is_file() else root.rglob('progress.sav')
    for path in paths:
     try:
      before=path.stat();data=path.read_bytes();after=path.stat()
      if before.st_mtime_ns!=after.st_mtime_ns or len(data)!=after.st_size:raise ValueError('存档正在写入，稍后重试')
      flags=parse_flags(data);candidates.append((after.st_mtime_ns,flags.get(0xe573f564,0),path,data,flags))
     except (OSError,ValueError) as exc:errors.append(str(path)+': '+str(exc))
   if not candidates and self.cached:return self.cached[0],copy.deepcopy(self.cached[1])
   if not candidates:return None,{'error':'未找到有效存档','roots':[str(r) for r in self.roots],'warnings':errors}
   latest=max(candidates,key=lambda c:(c[0],c[1]))
   # Ryujinx commits can touch every slot within one second; copied slot order is not game chronology.
   family=latest[2].parent.parent.parent
   recent=[c for c in candidates if latest[0]-c[0]<=1_000_000_000 and c[2].parent.parent.parent==family]
   mtime,playtime,path,data,flags=max(recent,key=lambda c:(c[1],c[0]));towers=json.loads((ROOT/'webui/towers.json').read_text())
   for tower in towers:tower['unlocked']=flags.get(tower['h'])==1
   status={'path':str(path),'mtime':mtime/1e6,'version':hashlib.sha256(data).hexdigest(),'playtime':playtime,'slots':len(candidates),'towers':towers,'warnings':errors}
   self.cached=(data,status);self.signature=signature if not errors else None
   return data,copy.deepcopy(status)
class Handler(SimpleHTTPRequestHandler):
 protocol_version="HTTP/1.1"
 def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(WEBUI),**kwargs)
 def send_head(self):
  name=unquote(urlsplit(self.path).path).lstrip('/')
  if name in ('','index.html') and read_resource('gamersky-archive.json') is None:
   data='<!doctype html><meta charset="utf-8"><title>地图数据包未安装</title><body style="background:#171d1b;color:#e7ebe5;font:18px system-ui;padding:64px"><h1>请导入地图数据包</h1><p>在桌面客户端的「服务 → 导入数据包…」中选择地图 .totkpack 文件。</p><p>攻略与图鉴可另行导入，MCP 和游戏连接服务仍可使用。</p></body>'.encode()
   return self.resource_reply(data,'text/html; charset=utf-8')
  if resource_kind(name):
   try:data=read_resource(name)
   except (OSError,ValueError):data=None
   if data is None and name=='compendium.json':data=b'{"entries":[]}'
   if data is None:self.send_error(404,'Content pack resource unavailable');return None
   if name.startswith('terrain/'):
    self.send_error(404);return None
   return self.resource_reply(data,mimetypes.guess_type(name)[0] or 'application/octet-stream')
  if name.endswith(('.sqlite','.sqlite-shm','.sqlite-wal','.totkpack')):
   self.send_error(404);return None
  return super().send_head()
 def resource_reply(self,data,mime):
  self.send_response(200);self.send_header('Content-Type',mime);self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-cache');self.send_header('X-Content-Type-Options','nosniff');self.end_headers();return io.BytesIO(data)
 def json_reply(self,status,value):
  payload=json.dumps(value,ensure_ascii=False).encode();self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(payload)));self.end_headers();self.wfile.write(payload)
 def local_request(self):
  port=self.server.server_port;host=self.headers.get('Host','');origin=self.headers.get('Origin');hosts=['127.0.0.1','localhost']+getattr(self.server,'lan_hosts',[])
  if host not in [f'{h}:{port}' for h in hosts]:self.json_reply(403,{'error':'Invalid host'});return False
  if origin and origin!=f'http://{host}':self.json_reply(403,{'error':'Invalid origin'});return False
  return True
 def mcp_authorized(self):
  if not ipaddress.ip_address(self.client_address[0]).is_loopback:self.json_reply(403,{'error':'MCP is available only on this computer'});return False
  if not self.local_request():return False
  if not hmac.compare_digest(self.headers.get('Authorization',''),'Bearer '+self.server.mcp_token):self.json_reply(401,{'error':'MCP requires the client connection token'});return False
  return True
 def control_request(self):
  if not self.local_request():return False
  return True
 def do_POST(self):
  if urlsplit(self.path).path=='/api/amiibo':
   if not self.control_request():return
   from amiibo import execute
   from game_control import ControlError
   try:
    size=int(self.headers.get('Content-Length','0'))
    if not 0<size<=512 or 'application/json' not in self.headers.get('Content-Type',''):raise ValueError('请求必须是 JSON')
    self.json_reply(200,execute(json.loads(self.rfile.read(size))))
   except (ValueError,TypeError,UnicodeError) as exc:self.json_reply(400,{'error':str(exc)})
   except ControlError as exc:self.json_reply(exc.status,{'error':str(exc)})
   return
  if urlsplit(self.path).path in ('/api/game-control','/api/link-control'):
   if not self.control_request():return
   from game_control import ControlError
   from game_control_preferences import manager
   execute=manager().execute
   if urlsplit(self.path).path=='/api/link-control':
    from link_control import execute
   try:
    size=int(self.headers.get('Content-Length','0'))
    if not 0<size<=4096 or 'application/json' not in self.headers.get('Content-Type',''):raise ValueError('请求必须是 JSON')
    self.json_reply(200,execute(json.loads(self.rfile.read(size))))
   except (ValueError,TypeError,UnicodeError) as exc:self.json_reply(400,{'error':str(exc)})
   except ControlError as exc:self.json_reply(exc.status,{'error':str(exc)})
   return
  if urlsplit(self.path).path=='/api/mcp-tunnel':
   if not self.mcp_authorized():return
   try:
    size=int(self.headers.get('Content-Length','0'))
    if not 0<size<=8192 or 'application/json' not in self.headers.get('Content-Type',''):raise ValueError('Invalid tunnel request')
    message=json.loads(self.rfile.read(size))
    if not isinstance(message,dict):raise ValueError('Invalid tunnel request')
    action=message.get('action')
    if action=='start':result=self.server.tunnel.start(message.get('domain',''),message.get('authtoken',''))
    elif action=='stop':result=self.server.tunnel.stop()
    else:raise ValueError('Invalid tunnel action')
    self.json_reply(200,result)
   except (ValueError,TypeError,OSError) as exc:self.json_reply(400,{'error':str(exc)})
   return
  if urlsplit(self.path).path=='/api/position-calibration':
   if os.environ.get('TOTK_CLIENT_EDITION')=='native':self.json_reply(404,{'error':'原生游戏无需模拟器位置校准'});return
   if not self.local_request():return
   if not ipaddress.ip_address(self.client_address[0]).is_loopback:self.json_reply(403,{'error':'请在电脑本机校准位置'});return
   try:
    size=int(self.headers.get('Content-Length','0'))
    if not 0<size<=4096 or 'application/json' not in self.headers.get('Content-Type',''):raise ValueError('Invalid calibration request')
    data=json.loads(self.rfile.read(size))
    from position_calibration import start,verify
    action=data.get('action')
    if action not in ('scan','verify'):raise ValueError('Invalid calibration action')
    self.json_reply(200,(start if action=='scan' else verify)(data))
   except (ValueError,TypeError,KeyError,OSError) as exc:self.json_reply(400,{'error':str(exc)})
   return
  if urlsplit(self.path).path!='/mcp':self.json_reply(404,{'error':'Not found'});return
  if not self.mcp_authorized():return
  if self.headers.get('MCP-Protocol-Version','2025-03-26') not in ('2024-11-05','2025-03-26','2025-06-18','2025-11-25'):self.json_reply(400,{'error':'Unsupported protocol version'});return
  if 'application/json' not in self.headers.get('Content-Type',''):self.json_reply(415,{'error':'Content-Type must be application/json'});return
  try:
   size=int(self.headers.get('Content-Length','0'))
   if size<=0 or size>1024*1024:raise ValueError('Invalid body length')
   message=json.loads(self.rfile.read(size))
   if not isinstance(message,dict) or message.get('jsonrpc')!='2.0':raise ValueError('Invalid JSON-RPC message')
  except (ValueError,UnicodeError) as exc:self.json_reply(400,{'jsonrpc':'2.0','id':None,'error':{'code':-32700,'message':str(exc)}});return
  from mcp_protocol import dispatch
  response=dispatch(self.server.map_service,message)
  if response is None:self.send_response(202);self.send_header('Content-Length','0');self.end_headers()
  else:self.json_reply(200,response)
 def log_message(self,format,*args):
  args=tuple(str(a).split('?')[0]+' [private link]' if '/join?' in str(a) or '/api/media/' in str(a) else a for a in args)
  super().log_message(format,*args)
 def web_authorized(self):
  address=ipaddress.ip_address(self.client_address[0])
  if address.is_loopback:return True
  if not address.is_private:self.json_reply(403,{'error':'WebUI is available on the local network only'});return False
  cookie=SimpleCookie()
  try:cookie.load(self.headers.get('Cookie',''))
  except CookieError:cookie=SimpleCookie()
  supplied=cookie.get('totk_web');expected=getattr(self.server,'web_token','')
  if not expected or not supplied or not hmac.compare_digest(supplied.value,expected):
   self.json_reply(401,{'error':'请扫描客户端二维码访问'});return False
  return True
 def serve_media(self,head=False):
  from guide_media import MediaError
  import re
  parsed=urlsplit(self.path);match=re.fullmatch(r'/api/media/(media_[0-9a-f]{32})',parsed.path)
  try:
   if not match:raise MediaError(404,'media_not_found')
   public=getattr(self.server,'public_url',None);port=self.server.server_port
   hosts=[f'127.0.0.1:{port}',f'localhost:{port}']+[f'{h}:{port}' for h in getattr(self.server,'lan_hosts',[])]
   if public:hosts.extend([urlsplit(public).netloc,urlsplit(public).netloc+':443'])
   if self.headers.get('Host','') not in hosts:raise MediaError(403,'invalid_media_host')
   store=self.server.map_service.guide_media;mid=match[1];expires=store.authorize(mid,parsed.query);data,meta=store.read(mid)
   self.send_response(200);self.send_header('Content-Type',meta['mimeType']);self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control',f'private, max-age={max(0,min(3600,expires-int(time.time())))}');self.send_header('ETag','"'+meta['etag']+'"');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Access-Control-Allow-Origin','*');self.send_header('Referrer-Policy','no-referrer');self.end_headers()
   if not head:self.wfile.write(data)
  except MediaError as error:
   payload=json.dumps({'error':error.code}).encode();self.send_response(error.status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(payload)));self.send_header('Cache-Control','no-store');self.end_headers()
   if not head:self.wfile.write(payload)
 def do_HEAD(self):
  if urlsplit(self.path).path.startswith('/api/media/'):return self.serve_media(head=True)
  if not self.local_request() or not self.web_authorized():return
  return super().do_HEAD()
 def do_GET(self):
  if urlsplit(self.path).path.startswith('/api/media/'):return self.serve_media()
  path=urlsplit(self.path).path
  if path in ('/api/amiibo','/api/amiibo/catalog'):
   if not self.control_request():return
   from amiibo import execute,ITEMS
   from game_control import ControlError
   try:self.json_reply(200,{'items':ITEMS} if path.endswith('/catalog') else execute())
   except ControlError as exc:self.json_reply(exc.status,{'error':str(exc)})
   return
  if path=='/api/game-control/items':
   if not self.control_request():return
   from spawn_catalog import ITEMS,CATALOG_HASH
   self.json_reply(200,{'items':ITEMS,'catalogHash':CATALOG_HASH});return
  if path=='/api/game-control/preferences':
   if not self.control_request():return
   from game_control_preferences import manager
   self.json_reply(200,manager().info());return
  if path in ('/api/game-control','/api/link-control'):
   if not self.control_request():return
   from game_control import ControlError
   from game_control_preferences import manager
   try:self.json_reply(200,manager().execute({'action':'status'}))
   except ControlError as exc:self.json_reply(exc.status,{'error':str(exc)})
   return
  if path=='/api/mcp-tunnel':
   if self.mcp_authorized():self.json_reply(200,self.server.tunnel.status())
   return
  if not self.local_request():return
  if path=='/join':
   key=parse_qs(urlsplit(self.path).query).get('key',[''])[0]
   if not key or not hmac.compare_digest(key,getattr(self.server,'web_token','')):self.json_reply(401,{'error':'二维码链接已失效，请重新扫描'});return
   self.send_response(303);self.send_header('Location','/');self.send_header('Set-Cookie','totk_web='+key+'; HttpOnly; SameSite=Lax; Path=/');self.send_header('Referrer-Policy','no-referrer');self.send_header('Cache-Control','no-store');self.send_header('Content-Length','0');self.end_headers();return
  if path=='/mcp':
   if self.mcp_authorized():self.send_response(405);self.send_header('Allow','POST');self.send_header('Content-Length','0');self.end_headers()
   return
  if not self.web_authorized():return
  remote=not ipaddress.ip_address(self.client_address[0]).is_loopback
  if remote and path in ('/api/save','/api/status','/api/health','/api/client-info','/api/position-calibration'):self.json_reply(403,{'error':'仅电脑端可访问此接口'});return
  if path.startswith('/api/tiles/'):
   try:
    parts=path.split('/');layer=parts[3];zoom,x=int(parts[4]),int(parts[5]);y=int(parts[6].removesuffix('.png'))
    if len(parts)!=7:raise ValueError('Invalid tile path')
    from tile_cache import tile
    payload=tile(layer,zoom,x,y);self.send_response(200);self.send_header('Content-Type','image/png');self.send_header('Content-Length',str(len(payload)));self.send_header('Cache-Control','public, max-age=31536000, immutable');self.end_headers();self.wfile.write(payload)
   except (ValueError,IndexError):self.json_reply(400,{'error':'Invalid tile'})
   except Exception:self.json_reply(503,{'error':'离线地图缺少此瓦片，请完成地图下载'})
  elif path=='/api/data-packs':
   self.json_reply(200,pack_status())
  elif path in ('/api/health','/api/client-info'):
   self.json_reply(200,{'app':'totk-native-map' if os.environ.get('TOTK_CLIENT_EDITION')=='native' else 'totk-offline','edition':os.environ.get('TOTK_CLIENT_EDITION','legacy'),'pid':os.getpid(),'mcpURL':f'http://127.0.0.1:{self.server.server_port}/mcp','saveRoots':[str(r) for r in self.server.source.roots],'syncSeconds':.5,'dataPacks':pack_status()})
  elif path=='/api/position-calibration':
   if os.environ.get('TOTK_CLIENT_EDITION')=='native':self.json_reply(404,{'error':'原生游戏无需模拟器位置校准'});return
   from position_calibration import status
   self.json_reply(200,status())
  elif path=='/api/position':
   from mod_telemetry import position
   self.json_reply(200,position())
  elif path=='/api/progress':
   status=self.server.map_service.progress()
   if remote:status={k:v for k,v in status.items() if k not in ('path','roots','warnings')}
   self.json_reply(404 if 'error' in status else 200,status)
  elif path in ('/api/status','/api/save'):
   data,status=self.server.source.newest();raw=path=='/api/save';payload=data if raw and data else json.dumps(status,ensure_ascii=False).encode();self.send_response(200 if data else 404);self.send_header('Content-Type','application/octet-stream' if raw and data else 'application/json; charset=utf-8');self.send_header('Cache-Control','no-store')
   if data:self.send_header('X-Save-Version',status['version'])
   self.send_header('Content-Length',str(len(payload)));self.end_headers();self.wfile.write(payload)
  else:super().do_GET()
 def do_DELETE(self):
  if urlsplit(self.path).path=='/mcp' and self.mcp_authorized():self.send_response(405);self.send_header('Content-Length','0');self.end_headers()
  elif urlsplit(self.path).path!='/mcp':self.json_reply(404,{'error':'Not found'})
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--import-pack',type=Path);parser.add_argument('--reference-pack',action='store_true');parser.add_argument('--save-dir',action='append',type=Path);parser.add_argument('--port',type=int,default=8765);parser.add_argument('--fallback-port',action='store_true');parser.add_argument('--runtime-file',type=Path);parser.add_argument('--parent-pid',type=int);parser.add_argument('--lan',action='store_true');args=parser.parse_args();bind='0.0.0.0' if args.lan else '127.0.0.1'
 if args.import_pack:
  try:print(json.dumps(install_pack(args.import_pack,args.reference_pack),ensure_ascii=False));return
  except Exception as error:print(str(error),file=sys.stderr);raise SystemExit(1)
 try:server=ThreadingHTTPServer((bind,args.port),Handler)
 except OSError:
  if not args.fallback_port:raise
  server=ThreadingHTTPServer((bind,0),Handler)
 server.source=SaveSource(args.save_dir or default_save_roots());server.source.start();server.mcp_token=os.environ.get('TOTK_MCP_TOKEN') or secrets.token_urlsafe(32)
 server.lan_hosts=[h for h in os.environ.get('TOTK_LAN_HOSTS','').split(',') if h and ipaddress.ip_address(h).is_private] if args.lan else []
 server.web_token=os.environ.get('TOTK_WEB_TOKEN') or secrets.token_urlsafe(32)
 from map_service import MapService
 server.map_service=MapService(server.source)
 server.map_service.guide_media.secret=hmac.new(server.mcp_token.encode(),b'totk-guide-media-v1',hashlib.sha256).digest()
 from mcp_tunnel import Tunnel
 server.tunnel=Tunnel(server,Handler,ROOT/'tunnel-agent/ngrok')
 server.map_service.public_base=lambda: (server.tunnel.status().get('url') or '').removesuffix('/mcp') or None
 from mod_telemetry import telemetry
 telemetry.start()
 from game_control_preferences import manager
 manager().start()
 from offline_map import archive_info
 info={'dataPacks':pack_status(),'offlineMap':archive_info(),'url':f'http://127.0.0.1:{server.server_port}/','mcpURL':f'http://127.0.0.1:{server.server_port}/mcp','token':server.mcp_token,'pid':os.getpid(),'lanURLs':[f'http://{host}:{server.server_port}/join?key={server.web_token}' for host in server.lan_hosts]}
 if args.runtime_file:
  args.runtime_file.parent.mkdir(parents=True,exist_ok=True);temp=args.runtime_file.with_suffix('.tmp');temp.write_text(json.dumps(info));temp.chmod(0o600);temp.replace(args.runtime_file)
 else:print(json.dumps(info),flush=True)
 if args.parent_pid:
  def monitor():
   while True:
    time.sleep(2)
    try:os.kill(args.parent_pid,0)
    except OSError:server.shutdown();return
  threading.Thread(target=monitor,daemon=True).start()
 import signal
 def terminate(*unused):threading.Thread(target=server.shutdown,daemon=True).start()
 signal.signal(signal.SIGTERM,terminate)
 signal.signal(signal.SIGINT,terminate)
 try:server.serve_forever()
 finally:
  manager().stop();server.tunnel.stop();server.source.stop();server.server_close()
if __name__=='__main__':main()
