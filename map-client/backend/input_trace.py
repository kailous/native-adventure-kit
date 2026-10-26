"""Freeze bounded game-only input history for reliable paged MCP review."""
import json
import os
from pathlib import Path
import re
import time
import uuid
from data_packs import support_root

def trace_root():
 return support_root()/'InputTraces'

def export(after_sequence=0,session=None):
 from mod_telemetry import telemetry
 telemetry.start()
 with telemetry.lock:
  if session is not None and session!=telemetry.session:raise ValueError('游戏会话已变化；请先读取当前输入状态')
  value=telemetry.latest
  inputs=value.get('inputs') if value else None
  if not inputs or not inputs.get('available'):raise ValueError('暂无可导出的输入记录；需要操作观察版游戏及运行中的地图后台')
  snapshot=telemetry.input_history.snapshot(inputs)
  active_session=telemetry.session
  age=max(0,time.monotonic()-telemetry.last_received)
 events=[e for e in snapshot.pop('events') if e['sequence']>after_sequence]
 oldest=snapshot['oldestSequence']
 lost=after_sequence<oldest-1 or any(g['to']>after_sequence for g in snapshot['captureGaps'])
 metadata={**snapshot,'schema':'totk-input-trace/1','session':active_session,
  'exportedAt':time.time(),'receivedAgeSeconds':age,'afterSequence':after_sequence,
  'eventCount':len(events),'historyLost':lost,'cursorAhead':after_sequence>snapshot['sequence'],
  'meaning':'game-only input intent; raw controller positions are not remapped Nintendo labels'}
 root=trace_root();root.mkdir(parents=True,exist_ok=True)
 # Only our UUID-named exports: retain at most 16, for at most 24 hours.
 previous=sorted((p for p in root.glob('*.json') if re.fullmatch(r'[0-9a-f]{32}',p.stem)),key=lambda p:p.stat().st_mtime)
 for p in previous:
  if time.time()-p.stat().st_mtime>86400 or len(previous)>15:
   p.unlink();previous=previous[1:]
 trace_id=uuid.uuid4().hex;path=root/(trace_id+'.json')
 data=json.dumps({'metadata':metadata,'events':events},ensure_ascii=False).encode()
 if len(data)>16*1024*1024:raise ValueError('轨迹过大，未导出')
 fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 with os.fdopen(fd,'wb') as output:output.write(data)
 return {'traceId':trace_id,'path':str(path),'metadata':metadata,
         'readTool':'read_input_trace','nextOffset':0,'expiresAfterHours':24}

def read(trace_id,offset=0,limit=256):
 if not re.fullmatch(r'[0-9a-f]{32}',trace_id):raise ValueError('无效的轨迹 ID')
 path=trace_root()/(trace_id+'.json')
 try:
  fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
  with os.fdopen(fd,'rb') as source:
   data=source.read(16*1024*1024+1)
  if len(data)>16*1024*1024:raise ValueError('轨迹文件过大')
  value=json.loads(data)
 except OSError as error:raise ValueError('轨迹不存在或已清理，请重新导出') from error
 events=value['events'];page=events[offset:offset+limit];next_offset=min(len(events),offset+len(page))
 return {'traceId':trace_id,'metadata':value['metadata'],'events':page,
         'nextOffset':next_offset,'hasMore':next_offset<len(events)}
