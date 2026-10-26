"""Read-only Ryujinx position probe. Calibration is tied to one process session."""
import ctypes,json,math,struct,subprocess,sys,time
from pathlib import Path
CONFIG=Path.home()/'Library/Application Support/TOTK Offline/position-memory.json'
def process_identity(pid):
 result=subprocess.run(['ps','-p',str(pid),'-o','lstart=','-o','comm='],capture_output=True,text=True,timeout=2)
 value=result.stdout.strip()
 if result.returncode or '/Ryujinx.app/Contents/MacOS/Ryujinx' not in value:raise ValueError('Ryujinx 未运行，需重新校准实时位置')
 return value
class Memory:
 def __init__(self,pid):
  if sys.platform!='darwin':raise ValueError('当前实时位置采集仅支持 macOS Ryujinx')
  self.lib=ctypes.CDLL('/usr/lib/libSystem.B.dylib');self.lib.mach_task_self.restype=ctypes.c_uint
  self.lib.mach_vm_read_overwrite.argtypes=[ctypes.c_uint,ctypes.c_uint64,ctypes.c_uint64,ctypes.c_uint64,ctypes.POINTER(ctypes.c_uint64)]
  self.port=ctypes.c_uint();result=self.lib.task_for_pid(self.lib.mach_task_self(),pid,ctypes.byref(self.port))
  if result:raise ValueError('无法读取 Ryujinx 内存，错误码 '+str(result))
 def read(self,address,size):
  if not 0<size<=4096:raise ValueError('Invalid read size')
  buffer=ctypes.create_string_buffer(size);actual=ctypes.c_uint64()
  result=self.lib.mach_vm_read_overwrite(self.port,address,size,ctypes.addressof(buffer),ctypes.byref(actual))
  if result or actual.value!=size:raise ValueError('位置地址已失效，请重新校准')
  return buffer.raw
 def close(self):
  if self.port.value:self.lib.mach_port_deallocate(self.lib.mach_task_self(),self.port);self.port.value=0
 def __enter__(self):return self
 def __exit__(self,*args):self.close()
def matrix_heading(values,x,north,height):
 if len(values)!=12 or not all(math.isfinite(v) for v in values):return None
 if max(abs(values[0]-x),abs(values[1]-height-105.5),abs(values[2]+north))>2:return None
 r=values[3:]
 for i in range(3):
  if abs(sum(r[i*3+j]**2 for j in range(3))-1)>.05:return None
  for k in range(i):
   if abs(sum(r[i*3+j]*r[k*3+j] for j in range(3)))>.05:return None
 determinant=r[0]*(r[4]*r[8]-r[5]*r[7])-r[1]*(r[3]*r[8]-r[5]*r[6])+r[2]*(r[3]*r[7]-r[4]*r[6])
 if abs(determinant-1)>.1 or math.hypot(r[6],r[8])<.05:return None
 return math.degrees(math.atan2(r[6],-r[8]))%360
def position():
 try:
  c=json.loads(CONFIG.read_text());pid=c['pid']
  if c.get('gameVersion') != '1.4.3':raise ValueError('仅支持 1.4.3，请使用原生游戏遥测')
  if not c.get('verified'):raise ValueError('实时位置尚未完成移动验证')
  if process_identity(pid)!=c['identity']:raise ValueError('游戏进程已重启，请重新校准位置')
  rotation=None
  with Memory(pid) as memory:
   data=memory.read(c['address'],max(c['offsets'])+4)
   if c.get('headingVerified') and c.get('headingMatrixAddress'):
    try:rotation=struct.unpack('<12f',memory.read(c['headingMatrixAddress'],48))
    except ValueError:pass
  x,north,height=[struct.unpack_from('<f',data,o)[0] for o in c['offsets']]
  if not all(math.isfinite(v) for v in (x,north,height)) or abs(x)>6000 or abs(north)>6000 or not -3000<height<5000:raise ValueError('位置数据失效，请重新校准')
  heading=matrix_heading(rotation,x,north,height) if rotation else None
  return {'headingAvailable':heading is not None,'heading':heading,'headingSource':'player-facing' if heading is not None else None,'available':True,'x':x,'z':-north,'north':north,'height':height,'layer':'d' if height < -300 else 'k' if height > 750 else 's','sampledAt':time.time(),'source':'Ryujinx memory','sessionCalibration':True}
 except (OSError,ValueError,KeyError,TypeError,subprocess.SubprocessError) as exc:return {'available':False,'error':str(exc) if CONFIG.exists() else '实时位置尚未校准'}
if __name__=='__main__':print(json.dumps(position(),ensure_ascii=False))
