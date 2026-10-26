"""Local Link controller API, using the game-thread input adapter."""
import math

BUTTONS={name:1<<bit for bit,name in enumerate(
 ('a','b','x','y','l_stick','r_stick','l','r','zl','zr','plus','minus','left','up','right','down'))}
ACTIONS={'move','turn','jump','attack','interact','input','sequence','stop','status'}

def _axis(value):
 if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or not -1<=value<=1:
  raise ValueError('摇杆范围为 -1–1')
 return round(value*32767)

def payload(data):
 """Return buttons, duration, L x/y, R x/y for TKC1 version 2."""
 action=data['action'].removeprefix('link_')
 allowed={'action','duration_ms'}
 if action in ('move','turn'):allowed|={'x','y'}
 if action=='input':allowed|={'buttons','left_stick','right_stick'}
 if set(data)-allowed:raise ValueError('无效的林克控制参数')
 duration=data.get('duration_ms',150 if action in ('jump','attack','interact') else 500)
 if type(duration) is not int or not 1<=duration<=5000:raise ValueError('duration_ms 必须是 1–5000 的整数')
 lx=ly=rx=ry=buttons=0
 if action in ('move','turn'):
  if 'x' not in data or 'y' not in data:raise ValueError('移动和转向需要 x、y 摇杆参数')
  x,y=_axis(data['x']),_axis(data['y'])
  if action=='move':lx,ly=x,y
  else:rx,ry=x,y
 elif action=='input':
  names=data.get('buttons',[])
  if not isinstance(names,list) or len(names)>16 or any(not isinstance(name,str) or name not in BUTTONS for name in names):
   raise ValueError('buttons 必须是受支持的按键名称数组')
  for name in names:buttons|=BUTTONS[name]
  sticks=[]
  for key in ('left_stick','right_stick'):
   stick=data.get(key,{'x':0,'y':0})
   if not isinstance(stick,dict) or set(stick)!={'x','y'}:raise ValueError(key+' 必须包含 x、y')
   sticks.extend((_axis(stick['x']),_axis(stick['y'])))
  lx,ly,rx,ry=sticks
 else:buttons=BUTTONS[{'jump':'x','attack':'y','interact':'a'}[action]]
 return buttons,duration,lx,ly,rx,ry

def sequence_payload(data):
 if set(data)!={'action','steps'}:raise ValueError('按键序列需要 steps')
 steps=data['steps']
 if not isinstance(steps,list) or not 1<=len(steps)<=8:raise ValueError('按键序列包含 1–8 段')
 result=[]
 for step in steps:
  if not isinstance(step,dict) or set(step)-{'buttons','left_stick','right_stick','duration_ms'}:raise ValueError('无效按键序列段')
  result.append(payload({'action':'input',**step}))
 if sum(p[1] for p in result)>5000:raise ValueError('按键序列总时间不得超过 5000 毫秒')
 return result

def execute(data, *, navigation=False):
 if not isinstance(data,dict):raise ValueError('请求必须是 JSON 对象')
 action=data.get('action','status')
 if not isinstance(action,str) or action not in ACTIONS:raise ValueError('未知林克控制操作')
 if action in ('stop','status') and set(data)-{'action'}:raise ValueError('无效的林克控制参数')
 if action=='sequence':sequence_payload(data)
 elif action not in ('stop','status'):payload(data)
 from game_control import execute as game_execute
 return game_execute({**data,'action':'status' if action=='status' else 'link_'+action})
