"""Persist acknowledged cheat choices; restore switches without replaying actions."""
import copy,json,math,os,threading
from pathlib import Path
import game_control

from data_packs import support_root
DEFAULT_PATH=support_root()/'game-control.json'
FLAGS={'set_health_lock':'healthLocked','set_stamina_lock':'staminaLocked',
 'set_rupees_lock':'rupeesLocked','set_arrows_lock':'arrowsLocked','set_items_99':'items99Enabled'}
VALUES={'set_health':'controlHearts','set_stamina':'controlStamina','set_rupees':'controlRupees','set_arrows':'controlArrows','set_health_cap':'controlHealthCap'}
TARGETS=('weapon','bow','shield')

def persistent_command(data):
 action=data.get('action')
 if action=='set_weather_lock':return action,{'action':action,'enabled':data['enabled'],**({'weather':data['weather']} if data['enabled'] else {})}
 if action in FLAGS:return action,{'action':action,'enabled':data['enabled']}
 if action=='set_health_cap':
  command={'action':action,'enabled':data['enabled']}
  if data['enabled']:command['value']=data['value']
  return action,command
 if action=='set_durability' and data.get('mode') in ('normal','infinite'):
  return 'durability:'+data['target'],{'action':action,'target':data['target'],'mode':data['mode']}
 return None

def matches(command,state):
 action=command['action']
 if action=='set_weather_lock':return state.get('weather',{}).get('locked') is command['enabled'] and (not command['enabled'] or state.get('weather',{}).get('lastRequested')==command['weather'])
 if action in FLAGS:return state.get(FLAGS[action]) is command['enabled']
 if action=='set_health_cap':
  return state.get('healthCapEnabled') is command['enabled'] and (not command['enabled'] or state.get('healthCap')==command['value'])
 modes=state.get('durabilityModes',[]);index=TARGETS.index(command['target'])
 return state.get('durabilityScope')=='pouch' and len(modes)>index and modes[index]==(3 if command['mode']=='infinite' else 0)

def ready(command,state):
 if state.get('compatibility',{}).get('controlLayoutSupported') is False:return False
 action=command['action']
 if action=='set_weather_lock':return type(state.get('weather',{}).get('locked')) is bool and (not command['enabled'] or state['weather'].get('available') is True)
 if action in FLAGS and type(state.get(FLAGS[action])) is not bool:return False
 if action=='set_health_cap' and type(state.get('healthCapEnabled')) is not bool:return False
 if command.get('enabled') is False:return True
 if state.get('hearts') is None or state['hearts']<=0:return False
 if action=='set_stamina_lock':return state.get('stamina') is not None
 if action=='set_rupees_lock':return state.get('rupees') is not None
 if action=='set_arrows_lock':return state.get('arrows') is not None
 if action=='set_durability':
  index=TARGETS.index(command['target']);values=state.get('durabilityCounts',[])
  return state.get('durabilityScope')=='pouch' and len(values)>index and values[index]>=0
 return True

class Manager:
 def __init__(self,path=DEFAULT_PATH):
  self.path=Path(path);self.lock=threading.RLock();self.stop_event=threading.Event();self.thread=None
  self.controls={};self.values={};self.error=None;self.latest={}
  try:
   if self.path.exists():
    if self.path.stat().st_size>32768:raise ValueError('设置文件过大')
    data=json.loads(self.path.read_text())
    if not isinstance(data,dict) or data.get('schema')!=1 or not isinstance(data.get('controls'),dict) or not isinstance(data.get('values'),dict):raise ValueError('无效的设置文件')
    for key,command in data['controls'].items():
     if not isinstance(command,dict):raise ValueError('无效的已保存开关')
     game_control.encode(command,0)
     saved=persistent_command(command)
     if saved is None or saved!=(key,command):raise ValueError('设置文件包含不支持的自动操作')
    for key,value in data['values'].items():
     action=next((a for a,k in VALUES.items() if k==key),None)
     if action is None:raise ValueError('无效的已保存数值')
     game_control.encode({'action':action,'value':value,**({'enabled':True} if action=='set_health_cap' else {})},0)
    self.controls=data['controls'];self.values=data['values']
  except (OSError,ValueError,TypeError,KeyError,OverflowError,game_control.ControlError):self.error='已保存设置无法读取，未自动应用'
 def info(self):
  with self.lock:
   pending=[key for key,command in self.controls.items() if not matches(command,self.latest)]
   return {'controls':copy.deepcopy(self.controls),'values':dict(self.values),'pending':pending,'error':self.error}
 def save(self):
  temporary=self.path.with_suffix('.tmp')
  try:
   self.path.parent.mkdir(parents=True,exist_ok=True)
   with temporary.open('w') as output:
    os.chmod(temporary,0o600)
    json.dump({'schema':1,'controls':self.controls,'values':self.values},output,ensure_ascii=False)
    output.flush();os.fsync(output.fileno())
   os.replace(temporary,self.path);self.error=None
  except OSError:self.error='游戏操作已执行，但设置保存失败；重启后可能丢失'
 def execute(self,data):
  with self.lock:
   state=game_control.execute(data);self.latest=state
   command=persistent_command(data)
   changed=False
   if command:
    key,value=command
    # Store only a confirmed switch state, never an unknown timeout result.
    if matches(value,state):self.controls[key]=value;changed=True
   action=data.get('action')
   if action=='set_weather' and state.get('weather',{}).get('locked') and 'set_weather_lock' in self.controls:
    self.controls['set_weather_lock']={'action':'set_weather_lock','enabled':True,'weather':data['weather']};changed=True
   # Near-break also ends infinite durability in the Mod. Persist that resulting
   # normal mode, not the one-shot near-break operation.
   if action=='set_durability' and data.get('mode')=='near_break':
    key='durability:'+data['target']
    normal={'action':'set_durability','target':data['target'],'mode':'normal'}
    if key in self.controls and matches(normal,state):self.controls[key]=normal;changed=True
   if action in VALUES and 'value' in data:
    self.values[VALUES[action]]=data['value'];changed=True
   # Setting health to zero explicitly releases a live health lock in the Mod.
   if action=='set_health' and data.get('value')==0 and 'set_health_lock' in self.controls:
    self.controls['set_health_lock']={'action':'set_health_lock','enabled':False};changed=True
   if changed:self.save()
   state['preferences']=self.info();return state
 def restore_once(self):
  with self.lock:
   if not self.controls:return
   try:
    state=game_control.execute({'action':'status'});self.latest=state
    # Apply the cap before capturing a health lock; bound each restoration pass.
    keys=sorted(self.controls,key=lambda key:0 if key=='set_health_cap' else 1)
    attempts=0
    for key in keys:
     command=self.controls[key]
     if matches(command,state) or not ready(command,state):continue
     if attempts>=3:break
     attempts+=1
     try:state=game_control.execute(command);self.latest=state
     except game_control.ControlError:continue
   except game_control.ControlError:self.latest={}
 def start(self):
  if self.thread is not None:return
  def run():
   while not self.stop_event.is_set():
    self.restore_once();self.stop_event.wait(2)
  self.thread=threading.Thread(target=run,name='totk-cheat-restore',daemon=True);self.thread.start()
 def stop(self):
  self.stop_event.set()
  if self.thread:self.thread.join(timeout=3)

_manager=None
_manager_lock=threading.Lock()
def manager():
 global _manager
 with _manager_lock:
  if _manager is None:_manager=Manager()
  return _manager
