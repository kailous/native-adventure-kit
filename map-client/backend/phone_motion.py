"""Ephemeral phone IMU sessions and bounded native six-axis transport.

No sensor recordings, saved credentials, controller buttons or game memory.
The native frame producer rejects stale TPM1 packets and expires after 200ms.
"""
import hmac
import json
import math
import secrets
import socket
import struct
import threading
import time
import sys
import ctypes

# Older macOS Python versions subtract a process-local monotonic epoch.
# TPM1 must use the exact mach_absolute_time epoch used by the native runtime.
if sys.platform=='darwin':
    class _Timebase(ctypes.Structure):
        _fields_=[('numer',ctypes.c_uint32),('denom',ctypes.c_uint32)]
    _mach=ctypes.CDLL('/usr/lib/libSystem.B.dylib')
    _mach.mach_absolute_time.restype=ctypes.c_uint64
    _tb=_Timebase();_mach.mach_timebase_info(ctypes.byref(_tb))
    def native_now_ns():return _mach.mach_absolute_time()*_tb.numer//_tb.denom
else:
    native_now_ns=time.monotonic_ns

WIRE=struct.Struct('<4sBBHQQQ6f')
ADDRESS=('127.0.0.1',7077)

class MotionError(Exception):
    def __init__(self,message,status=409):
        super().__init__(message);self.status=status

class NativeMotion:
    def __init__(self,address=ADDRESS):
        self.address=address

    def send(self,op=0,session=0,sequence=None,acc=(0,0,0),gyro=(0,0,0)):
        sequence=secrets.randbits(32) if sequence is None else sequence
        packet=WIRE.pack(b'TPM1',1,op,0,session,sequence,native_now_ns(),*acc,*gyro)
        try:
            with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sock:
                sock.settimeout(.18);sock.connect(self.address);sock.send(packet)
                result=json.loads(sock.recv(1024))
        except (OSError,ValueError) as exc:
            raise MotionError('当前游戏未响应手机陀螺仪，请保存退出后启动配套新版游戏',503) from exc
        if (not isinstance(result,dict) or result.get('protocol')!='totk-phone-motion/1'
                or result.get('gameVersion')!='1.4.3' or result.get('sequence')!=sequence
                or type(result.get('code')) is not int
                or any(type(result.get(k)) is not bool for k in ('gyroEnabled','active','selected'))):
            raise MotionError('游戏返回了无效的陀螺仪状态',502)
        if result['code']:
            messages={2:'陀螺仪数据无效',3:'陀螺仪数据已过期',4:'游戏未启用六轴设备',5:'另一台手机正在使用陀螺仪'}
            raise MotionError(messages.get(result['code'],'游戏拒绝了陀螺仪数据'))
        return {k:result[k] for k in ('gameVersion','gyroEnabled','active','selected')}

class PhoneMotion:
    def __init__(self,native=None,clock=time.monotonic):
        self.native=native or NativeMotion();self.clock=clock;self.lock=threading.RLock()
        self.owner=None

    def _prune(self):
        now=self.clock()
        if self.owner and self.owner['until']<=now:self.owner=None

    def status(self):
        try:return {'available':True,**self.native.send()}
        except MotionError as error:return {'available':False,'error':str(error)}

    def _owner(self,data,client):
        self._prune();owner=self.owner
        token=data.get('token')
        if not owner or owner['client']!=client or not isinstance(token,str) or not hmac.compare_digest(token,owner['token']):
            raise MotionError('手机陀螺仪会话已停止，请重新启用',401)
        seq=data.get('sequence')
        if type(seq) is not int or not 0<seq<=2147483647 or seq<=owner['clientSequence']:
            raise MotionError('陀螺仪数据顺序无效')
        return owner,seq

    def execute(self,data,client):
        if not isinstance(data,dict):raise ValueError('陀螺仪请求必须是 JSON 对象')
        action=data.get('action')
        with self.lock:
            self._prune()
            if action=='start':
                if set(data)!={'action'}:raise ValueError('无效启用参数')
                if self.owner:raise MotionError('另一台手机已启用陀螺仪，请先停止或等待断流释放')
                native=self.native.send()
                if not native['gyroEnabled']:raise MotionError('游戏未启用六轴设备，请启用陀螺仪支持',503)
                token=secrets.token_urlsafe(32)
                self.owner={'token':token,'client':client,'session':secrets.randbits(64) or 1,
                            'wireSequence':0,'clientSequence':0,'until':self.clock()+3,'sampled':False}
                return {'token':token,'expiresMs':1000,'native':native}
            if action not in ('sample','calibrate','stop'):raise ValueError('未知陀螺仪操作')
            expected={'action','token','sequence'}|({'acc','gyro','ageMs'} if action=='sample' else set())
            if set(data)!=expected:raise ValueError('无效陀螺仪参数')
            owner,seq=self._owner(data,client)
            acc=gyro=(0,0,0)
            if action=='sample':
                for key,limit in [('acc',8),('gyro',35)]:
                    value=data[key]
                    if not isinstance(value,list) or len(value)!=3 or any(type(v) not in (float,int) or not math.isfinite(v) or abs(v)>limit for v in value):
                        raise ValueError('无效三轴数据：'+key)
                if type(data['ageMs']) not in (float,int) or not math.isfinite(data['ageMs']) or not 0<=data['ageMs']<=100:
                    raise MotionError('手机传感器数据已过期，请重新校准')
                acc,gyro=data['acc'],data['gyro']
            owner['clientSequence']=seq;owner['wireSequence']+=1
            try:
                if action=='calibrate' and not owner['sampled']:
                    native={'active':False,'selected':False}
                else:
                    native=self.native.send({'sample':1,'stop':2,'calibrate':3}[action],owner['session'],owner['wireSequence'],acc,gyro)
            except MotionError:
                self.owner=None;raise
            if action=='stop':self.owner=None
            else:
                owner['until']=self.clock()+(3 if action=='calibrate' else 1)
                if action=='sample':owner['sampled']=True
            return {'accepted':True,'native':native}

    def stop(self):
        with self.lock:
            if self.owner:
                owner=self.owner;self.owner=None
                try:self.native.send(2,owner['session'],owner['wireSequence']+1)
                except MotionError:pass # native expiry is the fallback; no retry
