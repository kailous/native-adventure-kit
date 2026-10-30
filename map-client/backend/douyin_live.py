"""Opt-in live interactions, serialized with bounded history and no shell rules."""
import atexit
import copy
import os
import tempfile
from douyin_commands import ACTIONS, defaults, validate_rules, preview, perform, movement_defaults
from collections import deque
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import threading
import time
from urllib.parse import urlsplit, urljoin, parse_qs


ALLOWED_SHARE_HOSTS = {'v.douyin.com', 'live.douyin.com', 'webcast.amemv.com', 'www.douyin.com', 'www.iesdouyin.com'}


def resolve_room(text, kind='live', get=None):
    """Resolve only known Douyin share hosts; never fetch arbitrary pasted URLs."""
    if not isinstance(text, str) or len(text) > 3000:
        raise ValueError('请粘贴不超过 3000 字的抖音直播分享文字')
    text = text.strip()
    if re.fullmatch(r'[0-9]{1,24}', text) and kind in ('room', 'live'):
        return dict(room=text, kind=kind)
    match = re.search(r'https?://[^\s<>"，。！；（）]+', text)
    if not match:
        raise ValueError('分享文字里未找到链接，请使用抖音直播间的「分享 → 复制链接」')
    url = match.group().rstrip(').,;!）')
    if get is None:
        import requests
        get = requests.get
    for _ in range(6):
        parsed = urlsplit(url)
        if parsed.scheme != 'https' or parsed.hostname not in ALLOWED_SHARE_HOSTS or parsed.username or parsed.password or parsed.port not in (None, 443):
            raise ValueError('只支持抖音官方 HTTPS 直播分享链接')
        room = re.fullmatch(r'/([0-9]{1,24})/?', parsed.path)
        if parsed.hostname == 'live.douyin.com' and room:
            return dict(room=room[1], kind='live')
        room = re.search(r'/webcast/reflow/([0-9]{1,24})(?:/|$)', parsed.path)
        if parsed.hostname == 'webcast.amemv.com' and room:
            return dict(room=room[1], kind='room')
        room = parse_qs(parsed.query).get('room_id', [''])[0]
        if parsed.hostname in ('webcast.amemv.com', 'www.iesdouyin.com') and re.fullmatch(r'[0-9]{1,24}', room):
            return dict(room=room, kind='room')
        try:
            response = get(url, allow_redirects=False, timeout=(4, 5), stream=True,
                           headers={'User-Agent': 'Mozilla/5.0'})
            try:
                if response.status_code not in (301, 302, 303, 307, 308) or not response.headers.get('Location'):
                    raise ValueError('链接未指向可识别的直播间，请重新复制直播分享链接')
                url = urljoin(url, response.headers['Location'])
            finally:
                response.close()
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError('分享链接解析失败，请检查网络后重试') from exc
    raise ValueError('分享链接跳转过多，请重新复制直播分享链接')


def config(value):
    if not isinstance(value, dict):
        raise ValueError('无效的直播设置')
    resolved = resolve_room(value.get('room', ''), value.get('kind', 'live'))
    room, kind = resolved['room'], resolved['kind']
    heal, damage = value.get('heal', '加血'), value.get('damage', '减血')
    if any(not isinstance(x, str) or not x.strip() or len(x) > 30 for x in (heal, damage)) or heal.strip() == damage.strip():
        raise ValueError('加血、减血关键词须不同，且为 1–30 个字符')
    step, cooldown = value.get('step', 1), value.get('cooldown', 2)
    if any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) for x in (step, cooldown)):
        raise ValueError('血量和冷却须为有限数字')
    if not .25 <= step <= 10 or step * 4 != round(step * 4) or not 1 <= cooldown <= 60:
        raise ValueError('血量须为 0.25–10 颗心（0.25 步长），冷却为 1–60 秒')
    rules = value.get('rules')
    if rules is None:
        rules = defaults()
        for row in rules:
            if row['action'] in ('heal','damage'):
                row.update(keywords=heal.strip() if row['action']=='heal' else damage.strip(),value=step)
    return dict(room=room, kind=kind, rules=validate_rules(rules), cooldown=cooldown)


class Live:
    def __init__(self, execute=None, clock=time.monotonic, rules_path=None, display=None):
        self.lock = threading.RLock()
        self.process = None
        self.thread = None
        self.execute = execute
        self.clock = clock
        self.settings = None
        self.state = 'stopped'
        self.connection_error = None
        self.events = deque(maxlen=50)
        self.seen = deque(maxlen=4096)
        self.last_action = -float('inf')
        self.ready_at = 0
        self.display = display
        self.commands_enabled = True
        self.rules_path = rules_path
        self.rules = defaults()
        self.cooldown = 2
        self.save_error = None
        if rules_path and rules_path.exists():
            try:
                stored = json.loads(rules_path.read_text())
                self.rules = validate_rules(stored['rules'])
                enabled=stored.get('commandsEnabled',True)
                if type(enabled) is not bool:raise ValueError('无效指令开关')
                self.commands_enabled=enabled
                cooldown = stored['cooldown']
                if isinstance(cooldown,bool) or not isinstance(cooldown,(int,float)) or not math.isfinite(cooldown) or not 1<=cooldown<=60:
                    raise ValueError('无效冷却')
                self.cooldown = cooldown
            except (OSError,ValueError,KeyError,TypeError):
                self.save_error = '保存的指令清单无效，已使用默认清单；原文件未改动'


    def status(self):
        with self.lock:
            state = 'connected' if self.state == 'warming' and self.clock() >= self.ready_at else self.state
            return copy.deepcopy(dict(state=state, settings=self.settings, events=list(self.events),
                                      rules=self.rules, cooldown=self.cooldown, actions=ACTIONS, connectionError=self.connection_error, saveError=self.save_error, commandsEnabled=self.commands_enabled, movementDefaults=movement_defaults(), display=self.display.info() if self.display else None))

    def save_rules(self, value):
        if not isinstance(value,dict):raise ValueError('无效指令设置')
        rules=validate_rules(value.get('rules'))
        enabled=value.get('commandsEnabled',self.commands_enabled)
        if type(enabled) is not bool:raise ValueError('指令开关须为布尔值')
        cooldown=value.get('cooldown',self.cooldown)
        if isinstance(cooldown,bool) or not isinstance(cooldown,(int,float)) or not math.isfinite(cooldown) or not 1<=cooldown<=60:
            raise ValueError('冷却须为 1–60 秒')
        with self.lock:
            if self.rules_path:
                self.rules_path.parent.mkdir(parents=True,exist_ok=True)
                fd,name=tempfile.mkstemp(prefix='.douyin-rules-',dir=self.rules_path.parent)
                try:
                    with os.fdopen(fd,'w') as stream:
                        json.dump(dict(schema=1,rules=rules,cooldown=cooldown,commandsEnabled=enabled),stream,ensure_ascii=False)
                        stream.flush();os.fsync(stream.fileno())
                    os.replace(name,self.rules_path)
                finally:
                    if os.path.exists(name):os.unlink(name)
            self.rules=rules;self.cooldown=cooldown;self.commands_enabled=enabled;self.save_error=None
            if self.settings:
                self.settings.update(rules=rules,cooldown=cooldown)
            return self.status()

    def preview(self, value):
        if not isinstance(value,dict):raise ValueError('无效试匹配请求')
        rules=validate_rules(value.get('rules',self.rules))
        return preview(value.get('text',''),rules)

    def start(self, value):
        if isinstance(value,dict):
            value={**value,'rules':value.get('rules',self.rules),'cooldown':value.get('cooldown',self.cooldown)}
        settings = config(value)
        with self.lock:
            if self.process is not None:
                raise ValueError('请先停止当前直播连接')
            self.save_rules({**settings,'commandsEnabled':value.get('commandsEnabled',self.commands_enabled)})
            command = ([sys.executable, '--douyin-worker'] if getattr(sys, 'frozen', False)
                       else [sys.executable, '-u', str(Path(__file__).with_name('douyin_worker.py'))])
            proc = subprocess.Popen(command + [settings['room'], settings['kind']],
                                    stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                    text=True, encoding='utf-8', bufsize=1)
            self.process = proc
            self.settings = settings
            self.state = 'connecting'
            self.events.clear()
            self.seen.clear()
            self.last_action = -float('inf')
            self.thread = threading.Thread(target=self._read, args=(proc,), daemon=True)
            self.thread.start()
            return self.status()

    def stop(self):
        with self.lock:
            proc, thread = self.process, self.thread
            self.process = None
            self.state = 'stopped'
        if proc:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=3)
        if thread and thread is not threading.current_thread():
            thread.join(timeout=3)
        return self.status()

    def _read(self, proc):
        try:
            while True:
                line = proc.stdout.readline(16385)
                if not line:
                    break
                if len(line) > 16384:
                    break
                try:
                    event = json.loads(line)
                except ValueError:
                    continue  # upstream diagnostic prints are not protocol events
                with self.lock:
                    if self.process is not proc:
                        break
                    self.receive(event)
        finally:
            proc.stdout.close()
            with self.lock:
                if self.process is proc:
                    self.state = 'error'
                    self.events.appendleft({'result': '接收器已退出，请检查依赖或直播连接后重新启动'})
                    self.process = None
            if proc.poll() is None:
                proc.terminate()
            proc.wait()

    def receive(self, event):
        # Called under lock by the one reader: read/modify/write never overlap.
        if not isinstance(event, dict):
            return
        now = self.clock()
        if event.get('type') == 'connection':
            self.state = event.get('state', 'error')
            if isinstance(event.get('error'),str):self.connection_error=event['error'][:200]
            if self.state in ('warming','connected'):self.connection_error=None
            if self.state == 'warming':
                self.ready_at = now + 20
            return
        if event.get('type') == 'live_end':
            self.state = 'ended'
            return
        if event.get('type') != 'chat' or not self.settings:
            return
        mid = str(event.get('id', ''))
        if not mid or mid == '0' or mid in self.seen:
            return
        self.seen.append(mid)
        text = str(event.get('text', ''))[:1000]
        row = dict(user=str(event.get('user', ''))[:100], text=text, result='未命中关键词')
        self.events.appendleft(row)
        if event.get('warming') or now < self.ready_at:
            row['result'] = '连接预热，跳过历史弹幕'
            return
        self.state = 'connected'
        settings = self.settings
        if self.display:self.display.chat(row['user'],text)
        if not self.commands_enabled:
            row['result']='观众指令已暂停'
            return
        match = preview(text, settings['rules'])
        if not match['matched']:
            row['result'] = match['reason']
            return
        row['command'] = match['label']
        if match['command']['action'] != 'link:stop' and now - self.last_action < settings['cooldown']:
            row['result'] = '冷却中，已跳过'
            return
        self.last_action = now
        try:
            execute = self.execute
            if execute is None:
                from game_console import execute
            row['result'] = perform(match['command'], execute)
        except Exception as exc:
            row['result'] = str(exc)[:200]


from paths import douyin_rules_path
from paths import danmaku_settings_path
from danmaku import Danmaku
display = Danmaku(danmaku_settings_path())
live = Live(rules_path=douyin_rules_path(),display=display)
atexit.register(live.stop)
