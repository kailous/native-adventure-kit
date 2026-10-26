"""Virtual amiibo API, separate from cheat preferences and inventory writes."""
import json,secrets,socket,struct
from amiibo_catalog import ITEMS,INDEX
from game_control import ControlError,MOD_ADDRESS,_lock
def encode(data,request_id):
 if data is None:return struct.pack('<4sBBBBQd',b'TKC1',1,29,0,0,request_id,0.)
 if not isinstance(data,dict) or set(data)!={'id'} or not isinstance(data['id'],str) or data['id'] not in INDEX:raise ValueError('请选择目录中的 amiibo')
 model=data['id'];uid='04'+model[:12]
 return struct.pack('<4sBBBBQd',b'TKC1',4,28,0,0,request_id,0.)+bytes.fromhex(model+uid)+b'\0'
def execute(data=None):
 request_id=secrets.randbits(64);packet=encode(data,request_id)
 with _lock,socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as connection:
  connection.settimeout(2);connection.connect(MOD_ADDRESS)
  try:
   connection.send(packet)
   for _ in range(8):
    raw=connection.recv(4096)
    try:result=json.loads(raw)
    except (ValueError,UnicodeError):continue
    if isinstance(result,dict) and result.get('protocol')=='totk-amiibo/1' and result.get('id')==f'{request_id:016x}':break
   else:raise ControlError('游戏未返回有效的 amiibo 响应')
  except (socket.timeout,OSError) as exc:raise ControlError('请启动支持虚拟 amiibo 的原生 1.4.3 游戏；超时后请先查看游戏画面，勿连续重试',504) from exc
 if result.get('runtime')!='native' or result.get('gameVersion')!='1.4.3':raise ControlError('当前运行时不支持虚拟 amiibo',501)
 code=result.get('code')
 if type(code) is not int or code not in range(9):raise ControlError('无效的 amiibo 响应')
 if code:raise ControlError({3:'扫描请求已过期，未执行',5:'当前扫描尚未结束，请先回到游戏完成或取消'}.get(code,'游戏拒绝此次虚拟扫描'),409)
 state=result.get('amiibo')
 if not isinstance(state,dict) or any(type(state.get(k)) is not bool for k in ('available','initialized','queued')) or type(state.get('deviceState')) is not int or not 0<=state['deviceState']<=5:raise ControlError('游戏返回无效的 amiibo 状态')
 if not state['available']:raise ControlError('当前游戏尚未提供虚拟 amiibo，请更新原生运行时',501)
 return {'state':state,'accepted':data is not None,'message':'扫描已发送，识别与奖励结果请查看游戏画面' if data else ''}
