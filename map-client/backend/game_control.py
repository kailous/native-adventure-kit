"""Local request/reply adapter for verified native TOTK 1.4.3 control."""
import json,math,secrets,socket,struct,threading,os
_lock=threading.Lock()
WEATHER_TYPES={'clear':0,'cloudy':1,'rain':2,'heavy_rain':3,'thunder':6,'thunder_rain':7,'snow':10}
MOD_ADDRESS=('127.0.0.1',7075)
MOD_ERRORS={7:'生成间隔至少一秒',8:'游戏拒绝物品生成请求',1:'游戏数值暂不可用，请进入存档并确认背包数据可读取',2:'数值超出范围',3:'命令已过期，未执行',4:'此功能尚未支持',5:'玩家输入暂忙，请稍后查询状态',6:'林克输入暂不可用，请进入存档并加载新版 Mod'}
class ControlError(Exception):
 def __init__(self,message,status=503):
  if os.environ.get('TOTK_CLIENT_EDITION')=='native':
   message=message.replace('加载新版 Mod','使用新版游戏').replace('新版 Mod','新版游戏').replace('控制 Mod','游戏').replace('Mod','游戏')
  super().__init__(message);self.status=status

def encode(data,request_id):
 if not isinstance(data,dict):raise ValueError('请求必须是 JSON 对象')
 if data.get('action')=='menu_input':
  from link_control import payload
  values=payload({**data,'action':'input'})
  if values[0] not in (1,1<<13,1<<15) or values[1]>250 or any(values[2:]):raise ValueError('菜单接口仅允许限时确认、上、下按键')
  return struct.pack('<4sBBBBQdIIiiii',b'TKC1',2,22,0,0,request_id,0.,*values)
 if data.get('action')=='link_sequence':
  from link_control import sequence_payload
  steps=sequence_payload(data)
  return struct.pack('<4sBBBBQd',b'TKC1',3,23,len(steps),0,request_id,0.)+b''.join(struct.pack('<IIiiii',*step) for step in steps)
 action=data.get('action','status');op={'status':0,'set_health':1,'set_stamina':2,'set_rupees':3,'set_durability':4,'set_items_infinite':5,'set_health_lock':6,'set_stamina_lock':7,'set_rupees_lock':8,'set_health_cap':9,'set_items_99':10,'set_arrows':11,'set_arrows_lock':12,'link_move':13,'link_turn':13,'link_jump':13,'link_attack':13,'link_interact':13,'link_input':13,'link_stop':14,'set_weather':24,'set_weather_lock':25,'spawn_item':26}.get(action)
 if op is None:raise ValueError('未知游戏控制操作')
 target=mode=0;value=0.
 if op in (1,2,3,11):
  value=data.get('value')
  if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):raise ValueError('请输入有限数值')
  maximum={1:40,2:3,3:99999999,11:999}[op]
  if not 0<=value<=maximum:raise ValueError(f'数值范围为 0–{maximum}')
  if op==1 and value*4!=int(value*4):raise ValueError('血量以四分之一颗心为单位')
  if op in (3,11) and value!=int(value):raise ValueError('数量必须是整数')
 if op==26:
  from spawn_catalog import INDEX
  actor=data.get('actor')
  if not isinstance(actor,str) or actor not in INDEX:raise ValueError('请选择支持生成的物品')
  if set(data)-{'action','actor'}:raise ValueError('每次生成一件，仅接受 actor 参数')
  value=INDEX[actor]
 if op==25:
  if type(data.get('enabled')) is not bool:raise ValueError('enabled 必须是布尔值')
  mode=int(data['enabled'])
  if mode:
   weather=data.get('weather')
   if not isinstance(weather,str) or weather not in WEATHER_TYPES:raise ValueError('无效的天气类型')
   target=WEATHER_TYPES[weather]
 if op==24:
  weather=data.get('weather')
  if not isinstance(weather,str) or weather not in WEATHER_TYPES:raise ValueError('无效的天气类型')
  if 'enabled' in data or 'locked' in data:raise ValueError('天气接口仅支持一次性切换')
  target=WEATHER_TYPES[weather];mode=1
 if op==4:
  targets={'weapon':0,'bow':1,'shield':2};modes={'normal':0,'near_break':1,'reset':2,'infinite':3}
  if data.get('target') not in targets or data.get('mode') not in modes:raise ValueError('无效的装备或耐久模式')
  target=targets[data['target']];mode=modes[data['mode']]
 if op in (6,7,8,10,12):
  if type(data.get('enabled')) is not bool:raise ValueError('enabled 必须是布尔值')
  mode=int(data['enabled'])
 if op==9:
  if type(data.get('enabled')) is not bool:raise ValueError('enabled 必须是布尔值')
  mode=int(data['enabled'])
  if mode:
   value=data.get('value')
   if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or not 0.25<=value<=40 or value*4!=int(value*4):raise ValueError('血量上限为 0.25–40 颗心，步长 0.25')
 if op==5:
  if type(data.get('enabled')) is not bool:raise ValueError('enabled 必须是布尔值')
  raise ControlError('物品不减尚未支持：现有金手指是固定数量，仍需验证消耗接口',501)
 if op==13:
  from link_control import payload
  return struct.pack('<4sBBBBQdIIiiii',b'TKC1',2,op,0,0,request_id,0.,*payload(data))
 return struct.pack('<4sBBBBQd',b'TKC1',1,op,target,mode,request_id,float(value))

def execute(data):
 if isinstance(data,dict) and data.get('action')=='spawn_item':
  from spawn_catalog import CATALOG_HASH
  encode(data,0)
  state=execute({'action':'status'})
  if state.get('spawn',{}).get('catalogHash')!=CATALOG_HASH:raise ControlError('请安装物品目录一致的新版 Mod',501)
  if not state['spawn'].get('available'):raise ControlError('物品生成暂不可用，请进入存档',409)
 # Older adapters only affect equipped actors; never silently accept that scope.
 if isinstance(data,dict) and data.get('action')=='set_durability':
  encode(data,0)
  if execute({'action':'status'}).get('durabilityScope')!='pouch':raise ControlError('请安装 1.28.6 或更新的 Mod，以控制背包全部装备',501)
 request_id=secrets.randbits(64);packet=encode(data,request_id)
 with _lock, socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as connection:
  connection.settimeout(2);connection.connect(MOD_ADDRESS)
  try:
   connection.send(packet)
   # Never retry a mutation: a timeout does not establish whether it executed.
   for _ in range(8):
    raw=connection.recv(2048)
    try:result=json.loads(raw)
    except (ValueError,UnicodeError):continue
    if isinstance(result,dict) and result.get('protocol')=='totk-control/1' and result.get('id')==f'{request_id:016x}':break
   else:raise ControlError('Mod 返回了无效响应')
  except socket.timeout as exc:raise ControlError('Mod 未回应；请确认已加载新版 Mod。修改结果未知，请刷新数值确认',504) from exc
  except OSError as exc:raise ControlError('无法连接控制 Mod，请启动游戏并加载新版 Mod') from exc
 if type(result.get('code')) is not int or result['code'] not in range(9):raise ControlError('Mod 返回了无效状态')
 if result['code']==4 and result.get('compatibility',{}).get('controlLayoutSupported') is False:raise ControlError(f"游戏 {result.get('gameVersion','未知')} 的原生控制尚未适配，已阻止使用旧版本地址",501)
 if result['code']:raise ControlError(MOD_ERRORS[result['code']],501 if result['code']==4 else 409)
 for key in ('hearts','maxHearts','stamina','rupees','arrows'):
  val=result.get(key,-1) if key=='arrows' else result.get(key)
  if isinstance(val,bool) or not isinstance(val,(int,float)) or not math.isfinite(val):raise ControlError('Mod 返回了无效数值')
  if val<0:result[key]=None
 for flag,key in (('healthLocked','lockedHearts'),('staminaLocked','lockedStamina'),('rupeesLocked','lockedRupees'),('healthCapEnabled','healthCap'),('arrowsLocked','lockedArrows')):
  if flag in result and type(result[flag]) is not bool:raise ControlError('Mod 返回了无效锁定状态')
  val=result.get(key,-1)
  if isinstance(val,bool) or not isinstance(val,(int,float)) or not math.isfinite(val):raise ControlError('Mod 返回了无效锁定数值')
  result[key]=None if val<0 else val
 if 'items99Enabled' in result and type(result['items99Enabled']) is not bool:raise ControlError('Mod 返回了无效物品开关状态')
 if 'link' in result:
  link=result['link']
  if not isinstance(link,dict) or any(type(link.get(key)) is not bool for key in ('available','active')) or any(type(link.get(key)) is not int for key in ('remainingMs','buttons')) or not 0<=link['remainingMs']<=5000 or not 0<=link['buttons']<=65535:raise ControlError('Mod 返回了无效玩家输入状态')
  for key in ('leftStick','rightStick'):
   stick=link.get(key)
   if not isinstance(stick,dict) or any(isinstance(stick.get(axis),bool) or not isinstance(stick.get(axis),(int,float)) or not math.isfinite(stick[axis]) or not -1<=stick[axis]<=1 for axis in ('x','y')):raise ControlError('Mod 返回了无效摇杆状态')
 elif str(data.get('action','')).startswith('link_'):raise ControlError('请安装支持林克控制的新版 Mod',501)
 if 'durabilityScope' in result:
  counts=result.get('durabilityCounts')
  if result['durabilityScope']!='pouch' or not isinstance(counts,list) or len(counts)!=3 or any(type(n) is not int or not -1<=n<=128 for n in counts):raise ControlError('Mod 返回了无效背包状态')
 if 'weather' in result:
  weather=result['weather']
  if not isinstance(weather,dict) or type(weather.get('available')) is not bool or type(weather.get('lastRequestedId')) is not int or weather['lastRequestedId'] not in (-1,*WEATHER_TYPES.values()):raise ControlError('Mod 返回了无效天气状态')
  if 'locked' in weather and type(weather['locked']) is not bool:raise ControlError('Mod 返回了无效天气锁定状态')
  if weather.get('locked') and weather['lastRequestedId']==-1:raise ControlError('Mod 返回了无效天气锁定类型')
  weather['lastRequested']=next((key for key,value in WEATHER_TYPES.items() if value==weather['lastRequestedId']),None)
 elif data.get('action') in ('set_weather','set_weather_lock'):raise ControlError('请安装支持天气控制的新版 Mod',501)
 if data.get('action')=='set_weather_lock' and 'locked' not in result.get('weather',{}):raise ControlError('请安装支持天气锁定的新版 Mod',501)
 if 'spawn' in result:
  from spawn_catalog import ITEMS,INDEX,CATALOG_HASH
  spawn=result['spawn']
  if not isinstance(spawn,dict) or any(type(spawn.get(k)) is not bool for k in ('available','accepted')) or type(spawn.get('itemId')) is not int or not -1<=spawn['itemId']<len(ITEMS) or type(spawn.get('engineResult')) is not int or not -1<=spawn['engineResult']<=8 or spawn.get('catalogHash')!=CATALOG_HASH:raise ControlError('Mod 返回无效生成状态')
  if 'created' in spawn and type(spawn['created']) is not bool:raise ControlError('Mod 返回无效创建结果')
  position=spawn.get('position')
  if not isinstance(position,list) or len(position)!=3 or any(isinstance(n,bool) or not isinstance(n,(int,float)) or not math.isfinite(n) or abs(n)>20000 for n in position):raise ControlError('Mod 返回无效生成位置')
  if data.get('action')=='spawn_item' and (not spawn['accepted'] or spawn['itemId']!=INDEX[data['actor']]):raise ControlError('Mod 未确认指定物品生成请求')
  spawn['item']=ITEMS[spawn['itemId']] if spawn['itemId']>=0 else None
 result['experimental']=True
 return result
