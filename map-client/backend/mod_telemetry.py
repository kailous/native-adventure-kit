"""Loopback-only, receive-only game telemetry. No game control commands."""
import json,math,socket,threading,time,os
from macos_position import matrix_heading
PORT=7074
KNOWN_GAME_VERSIONS=frozenset(('1.4.3',))
class Telemetry:
 def __init__(self,port=PORT):
  from input_observation import InputHistory
  self.input_history=InputHistory()
  self.port=port
  self.lock=threading.Lock();self.latest=None;self.started=False;self.error=None;self.session=None;self.sequence=-1;self.last_received=0
 def ingest(self,payload):
  try:
   m=json.loads(payload)
   if m.get('protocol')!='totk-telemetry/1' or m.get('gameVersion') not in KNOWN_GAME_VERSIONS:return False
   from input_observation import validate as validate_inputs
   inputs=validate_inputs(m.get('inputs'))
   seq=m['sequence'];session=m['session']
   if not isinstance(session,str) or not 1<=len(session)<=64 or not isinstance(seq,int) or isinstance(seq,bool) or seq<0:return False
   if m.get('connected') is False:
    player=m.get('player')
    if m.get('position') is not None or m.get('rotation') is not None or not isinstance(player,dict) or player.get('available') is not False:return False
    value={'available':False,'connected':False,'modConnected':True,'headingAvailable':False,'player':{'available':False},'camera':{'available':False},'ui':{'available':False},'source':'TOTK telemetry mod','gameVersion':m['gameVersion'],'telemetryStatus':'no-player','error':'等待游戏场景中的玩家数据'}
    if m.get('adapterSupported') is False:
     value.update(telemetryStatus='unsupported-version',error=f"已连接原生游戏 {m['gameVersion']}，地图定位尚未适配此版本",adapterSupported=False)
    value['inputs']=inputs
    with self.lock:
     if session==self.session and seq<=self.sequence:return False
     self.session=session;self.sequence=seq;self.latest=value;self.last_received=time.monotonic()
     self.input_history.append(session,inputs,self.last_received)
    return True
   p=m['position'];r=m['rotation']
   if len(p)!=3 or len(r)!=9 or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in p+r):return False
   x,y,z=p;height=y-105.5
   if abs(x)>6000 or abs(z)>6000 or not -3000<height<5000:return False
   matrix_valid=matrix_heading(p+r,x,-z,height)
   if matrix_valid is None:return False
   player=m.get('player',{})
   if not isinstance(player,dict):return False
   # TOTK 1.0.0 Player local +Z was checked against forward walking on 2026-10-11.
   # Compass: north (-world Z)=0, east (+world X)=90.
   candidate=math.degrees(math.atan2(r[2],-r[8]))%360
   heading=candidate if math.hypot(r[2],r[8])>1e-4 else None
   if player.get('yawAvailable') is True:
    yaw=player.get('yaw')
    if isinstance(yaw,bool) or not isinstance(yaw,(int,float)) or not math.isfinite(yaw):return False
    if abs((yaw-candidate+180)%360-180)>1:return False
    heading=yaw%360
   raw_player={'position':{'x':x,'y':y,'z':z},'rotation':list(r),'forward':{'x':r[2],'y':r[5],'z':r[8]},'yawAvailable':heading is not None,'yaw':heading,'yawCandidate':candidate}
   ui={'available':False,'mode':'unknown','mapOpen':None,'mapLayer':None,'mapCursor':None}
   incoming_ui=m.get('ui',{})
   if not isinstance(incoming_ui,dict):return False
   if incoming_ui.get('available') is True:
    mode=incoming_ui.get('mode');opened=incoming_ui.get('mapOpen')
    if mode not in ('unknown','gameplay','map','inventory','quest','dialog','cutscene','loading') or not isinstance(opened,bool) or (mode=='map')!=opened:return False
    ui.update(available=True,mode=mode,mapOpen=opened)
    if opened:
     map_layer=incoming_ui.get('mapLayer');cursor=incoming_ui.get('mapCursor')
     if map_layer not in (None,'s','k','d'):return False
     ui['mapLayer']=map_layer
     if cursor is not None:
      if not isinstance(cursor,dict) or map_layer is None:return False
      cx,cz=cursor.get('x'),cursor.get('z')
      if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or abs(v)>8000 for v in (cx,cz)):return False
      ui['mapCursor']={'x':cx,'z':cz}
   camera={'available':False,'heading':None,'basisVerified':False,'fovVerified':False}
   view=m.get('camera',{})
   if isinstance(view,dict) and view.get('discovery') in ('vtable','object','unsupported'):camera['discovery']=view['discovery']
   if isinstance(view,dict) and view.get('available') is True:
    vx,vz=view.get('x'),view.get('z')
    if all(type(v) in (int,float) and math.isfinite(v) and abs(v)<=2 for v in (vx,vz)) and math.hypot(vx,vz)>.1:
     camera.update(available=True,heading=math.degrees(math.atan2(vx,-vz))%360,rawXZ=[vx,vz],basisVerified=view.get("basisVerified") is True and view.get("source")=="game-camera-readonly",source=view.get("source") if view.get("source")=="game-camera-readonly" else "game-camera")
   value={'available':True,'x':x,'z':z,'north':-z,'height':height,'layer':'d' if height<-300 else 'k' if height>750 else 's','heading':heading,'headingAvailable':heading is not None,'headingSource':'player-facing' if heading is not None else None,'sampledAt':time.time(),'connected':True,'player':raw_player,'camera':camera,'ui':ui,'timestamp':m.get('timestamp'),'modConnected':True,'source':'TOTK telemetry mod','sessionCalibration':False,'gameVersion':m['gameVersion']}
   value['inputs']=inputs
   with self.lock:
    if session==self.session and seq<=self.sequence:return False
    self.session=session;self.sequence=seq;self.latest=value;self.last_received=time.monotonic()
    self.input_history.append(session,inputs,self.last_received)
   return True
  except (ValueError,TypeError,KeyError,OverflowError):return False
 def start(self):
  with self.lock:
   if self.started:return
   self.started=True
  threading.Thread(target=self.run,name='totk-mod-telemetry',daemon=True).start()
 def run(self):
  try:
   with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:
    s.bind(('127.0.0.1',self.port))
    while True:
     packet,_=s.recvfrom(49153)
     if len(packet)<=49152:self.ingest(packet)
  except OSError as e:self.error=str(e)
 def position(self):
  self.start()
  with self.lock:
   if self.latest and time.monotonic()-self.last_received<=2:return dict(self.latest)
  return None
telemetry=Telemetry()
def position():
 value=telemetry.position()
 if value:return value
 if os.environ.get('TOTK_CLIENT_EDITION')=='native':
  return {'available':False,'modConnected':False,'source':'native-game','telemetryStatus':'error' if telemetry.error else 'waiting','error':('游戏连接端口不可用：'+telemetry.error+'；请关闭其他地图客户端后重新启动服务') if telemetry.error else '等待游戏启动；请进入游戏场景'}
 from macos_position import position as memory_position
 value=memory_position();value['modConnected']=False
 value['telemetryStatus']='error' if telemetry.error else 'disconnected' if telemetry.latest else 'waiting'
 if telemetry.error:value['telemetryError']=telemetry.error
 if not value.get('available'):value['error']='游戏连接已中断，等待游戏恢复' if telemetry.latest else '等待游戏启动；请进入游戏场景'
 return value
