"""Local-only two-stage calibration; scans and reads, never writes game memory."""
import json,math,subprocess,threading,time
from pathlib import Path
import macos_position as live
from server import ROOT
lock=threading.RLock()
state={'phase':'idle'}
candidates=[]
def coordinates(data):
 values=[data[k] for k in ('x','north','height')]
 if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in values):raise ValueError('请输入三个有效坐标')
 if abs(values[0])>6000 or abs(values[1])>6000 or not -3000<values[2]<5000:raise ValueError('坐标超出游戏范围')
 return values
def detect():
 result=subprocess.run(['pgrep','-x','Ryujinx'],capture_output=True,text=True,timeout=2)
 processes=[]
 for value in result.stdout.split():
  try:
   pid=int(value);identity=live.process_identity(pid);processes.append({'pid':pid,'identity':identity})
  except ValueError:pass
 return processes
def status():
 with lock:result={k:v for k,v in state.items() if k not in ('identity','initial')}
 result['processes']=[{'pid':p['pid']} for p in detect()]
 return result
def start(data):
 global state,candidates
 values=coordinates(data);processes=detect()
 if len(processes)!=1:raise ValueError('请仅运行一个 Ryujinx，并进入游戏场景')
 process=processes[0];scanner=ROOT/'backend/position-scanner'
 if not scanner.exists():scanner=ROOT/'build/position-scanner'
 if not scanner.exists():raise ValueError('客户端缺少内存扫描器，请更新客户端')
 with lock:
  if state['phase']=='scanning':raise ValueError('扫描正在进行，请稍候')
  candidates=[];state={'phase':'scanning','pid':process['pid'],'identity':process['identity'],'initial':values,'startedAt':time.time()}
 def worker():
  global state,candidates
  try:
   result=subprocess.run([str(scanner),str(process['pid']),str(values[0]),str(values[2]),str(values[1])],capture_output=True,text=True,timeout=180)
   if result.returncode:raise ValueError('内存扫描失败，请确认游戏正在运行且允许读取进程')
   if live.process_identity(process['pid'])!=process['identity']:raise ValueError('扫描期间游戏进程发生变化，请重试')
   found=[]
   for line in result.stdout.splitlines():
    address,north,height=map(int,line.split());found.append({'address':address,'offsets':[0,north,height]})
   # Overlapping copies in the same structure share north/height fields.
   grouped={}
   for c in sorted(found,key=lambda c:max(c['offsets'])):
    key=(c['address']+c['offsets'][1],c['address']+c['offsets'][2]);grouped.setdefault(key,c)
   with lock:
    candidates=list(grouped.values());state.update(phase='verify' if candidates else 'error',candidateCount=len(candidates),message='请移动至少几步，停下后输入新坐标验证' if candidates else '未找到匹配数据，请确认坐标、停留在游戏场景后重新扫描')
  except (OSError,ValueError,subprocess.SubprocessError) as exc:
   with lock:state.update(phase='error',message=str(exc))
 threading.Thread(target=worker,daemon=True).start()
 return status()
def verify(data):
 global candidates
 values=coordinates(data)
 with lock:
  if state['phase']!='verify':raise ValueError('请先完成扫描')
  if math.hypot(values[0]-state['initial'][0],values[1]-state['initial'][1])<3:raise ValueError('请移动至少 3 个坐标单位后再验证')
  if live.process_identity(state['pid'])!=state['identity']:raise ValueError('游戏已重启，请重新扫描')
  found=[]
  with live.Memory(state['pid']) as memory:
   for c in candidates:
    try:
     import struct
     raw=memory.read(c['address'],max(c['offsets'])+4);actual=[struct.unpack_from('<f',raw,o)[0] for o in c['offsets']]
     if all(math.isfinite(a) and abs(a-v)<1.5 for a,v in zip(actual,values)):found.append(c)
    except ValueError:pass
  candidates=found
  if len(found)!=1:
   state.update(candidateCount=len(found),message='仍有多个候选，请再次移动并验证' if found else '候选地址均不匹配，请重新扫描')
   if not found:state['phase']='error'
   return status()
  config={**found[0],'pid':state['pid'],'identity':state['identity'],'verified':True}
  live.CONFIG.parent.mkdir(parents=True,exist_ok=True);temp=live.CONFIG.with_suffix('.tmp');temp.write_text(json.dumps(config));temp.chmod(0o600);temp.replace(live.CONFIG)
  state.update(phase='ready',message='校准成功，实时位置已启用')
 return status()
