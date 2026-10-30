"""Bounded loopback transport for the native game's passive chat view."""
import json
import math
import os
from pathlib import Path
import socket
import tempfile
import threading

DEFAULTS=dict(enabled=False,mode='scroll',position='top',fontSize=24,nickname=True,speed=120,duration=5)


def validate(value):
    if not isinstance(value,dict):raise ValueError('无效的弹幕显示设置')
    result={**DEFAULTS,**value}
    if set(result)!=set(DEFAULTS):raise ValueError('未知弹幕显示设置')
    if type(result['enabled']) is not bool or type(result['nickname']) is not bool:raise ValueError('显示开关必须是布尔值')
    if result['mode'] not in ('scroll','fade') or result['position'] not in ('top','middle','bottom'):raise ValueError('无效的弹幕显示方式或位置')
    for name,lo,hi in [('fontSize',12,48),('speed',40,320),('duration',2,15)]:
        x=result[name]
        if isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) or not lo<=x<=hi:raise ValueError(f'{name} 范围为 {lo}–{hi}')
    return result


class Danmaku:
    def __init__(self,path=None,address=('127.0.0.1',7076)):
        self.path=path;self.address=address;self.settings=dict(DEFAULTS);self.error=None
        self.lock=threading.RLock();self.stop_event=threading.Event();self.thread=None
        if path and path.exists():
            try:self.settings=validate(json.loads(path.read_text()))
            except (OSError,ValueError,TypeError):self.error='弹幕设置无法读取，暂用默认值'
    def info(self):
        with self.lock:return {'settings':dict(self.settings),'error':self.error}
    def send(self,kind,**data):
        # No acknowledgement: a sent packet is never represented as a rendered message.
        packet=json.dumps(dict(protocol='totk-danmaku/1',kind=kind,settings=self.settings,**data),ensure_ascii=False).encode()
        if len(packet)>8192:return
        try:
            with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sock:
                sock.setblocking(False);sock.sendto(packet,self.address)
        except OSError:pass
    def save(self,value):
        settings=validate(value)
        with self.lock:
            if self.path:
                self.path.parent.mkdir(parents=True,exist_ok=True)
                fd,name=tempfile.mkstemp(prefix='.danmaku-',dir=self.path.parent)
                try:
                    with os.fdopen(fd,'w') as stream:json.dump(settings,stream);stream.flush();os.fsync(stream.fileno())
                    os.replace(name,self.path)
                finally:
                    if os.path.exists(name):os.unlink(name)
            self.settings=settings;self.error=None;self.send('config');return self.info()
    def chat(self,user,text):
        with self.lock:
            if self.settings['enabled']:self.send('chat',user=str(user)[:48],text=str(text)[:160])
    def start(self):
        if self.thread:return
        def run():
            while not self.stop_event.is_set():
                with self.lock:self.send('config')
                self.stop_event.wait(2)
        self.thread=threading.Thread(target=run,name='danmaku-config',daemon=True);self.thread.start()
    def stop(self):
        self.stop_event.set()
        if self.thread:self.thread.join(timeout=3)
