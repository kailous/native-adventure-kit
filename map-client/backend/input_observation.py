"""Read-only game input snapshots with bounded event cursors, not a keylogger."""
import math
from collections import deque
import copy
import time
SOURCES=('keyboard','mouse','controller','agent','synthetic-keyboard')
KEYBOARD=('a','b','x','y','lstick','rstick','l','r','zl','zr','plus','minus','left','up','right','down','move_left','move_right','move_up','move_down','look_left','look_right','look_up','look_down','mouse_toggle')
NAMES={'keyboard':KEYBOARD,'synthetic-keyboard':KEYBOARD,'mouse':('left','right','middle','mouse4','mouse5'),'controller':('south','east','west','north','l3','r3','l1','r1','l2','r2','menu','view','left','up','right','down','touchpad'),'agent':KEYBOARD[:16]}

def validate(value):
    if value is None:return {'available':False,'reason':'requires-input-observation-game-build'}
    if not isinstance(value,dict) or value.get('available') is not True:raise ValueError('invalid input observation')
    if value.get('clock')!='host-monotonic':raise ValueError('invalid input clock')
    for k in ('sequence','oldestSequence'):
        if type(value.get(k)) is not int or value[k]<0:raise ValueError('invalid input cursor')
    seq,old=value['sequence'],value['oldestSequence']
    capacity=value.get('historyCapacity',32)
    if type(capacity) is not int or capacity not in (32,128):raise ValueError('invalid history capacity')
    if old!=(max(1,seq-capacity+1) if seq else 0):raise ValueError('invalid input window')
    for k in ('sampledAt','lastUserAt'):
        if type(value.get(k)) not in (int,float) or not math.isfinite(value[k]) or not 0<=value[k]<=1e12:raise ValueError('invalid input time')
    if value['lastUserAt']>value['sampledAt']:raise ValueError('invalid user time')
    states,events=value.get('sources'),value.get('events')
    if not isinstance(states,list) or len(states)!=5 or not isinstance(events,list) or len(events)!=min(capacity,seq):raise ValueError('invalid input history')
    def state(e,event=False):
        if not isinstance(e,dict) or e.get('source') not in SOURCES:raise ValueError('invalid input source')
        maximum=(1<<len(NAMES[e['source']]))-1
        for k in (('buttons','pressed','released') if event else ('buttons',)):
            if type(e.get(k)) is not int or not 0<=e[k]<=maximum:raise ValueError('invalid input buttons')
        axes=e.get('axes')
        if not isinstance(axes,list) or len(axes)!=4 or any(type(v) is not int or not -32767<=v<=32767 for v in axes):raise ValueError('invalid input axes')
        t=e.get('at' if event else 'changedAt')
        if type(t) not in (int,float) or not math.isfinite(t) or not 0<=t<=value['sampledAt']:raise ValueError('invalid event time')
    for e in states:state(e)
    if {e['source'] for e in states}!=set(SOURCES):raise ValueError('duplicate input source')
    for i,e in enumerate(events):
        state(e,True)
        if e.get('sequence')!=old+i:raise ValueError('input event gap')
    return value

class InputHistory:
    """Called only under Telemetry.lock; bounded independently of agent polling."""
    def __init__(self):
        self.session=None;self.events=deque(maxlen=20000);self.gaps=deque(maxlen=64)
        self.last=0;self.gap_records_lost=False
    def append(self,session,inputs,received):
        if not inputs.get('available'):return
        if session!=self.session:
            self.__init__();self.session=session
        for event in inputs['events']:
            seq=event['sequence']
            if seq<=self.last:continue
            if seq>self.last+1:
                if len(self.gaps)==self.gaps.maxlen:self.gap_records_lost=True
                self.gaps.append({'from':self.last+1,'to':seq-1})
            self.events.append((received,dict(event)));self.last=seq
        while self.events and received-self.events[0][0]>600:self.events.popleft()
    def snapshot(self,inputs):
        events=[e for _,e in self.events]
        return {**inputs,'events':events,'oldestSequence':events[0]['sequence'] if events else 0,
                'captureGaps':list(self.gaps),'gapRecordsLost':self.gap_records_lost,
                'retention':{'maxEvents':20000,'maxSeconds':600,'scope':'map-backend-session'}}

def read(after_sequence=0,session=None,limit=32):
    from mod_telemetry import telemetry
    telemetry.start()
    with telemetry.lock:
        value=telemetry.latest;active_session=telemetry.session;age=time.monotonic()-telemetry.last_received
        inputs=value.get('inputs') if value else None
        if inputs and inputs.get('available') and telemetry.input_history.session==active_session:
            inputs=telemetry.input_history.snapshot(inputs)
    if not inputs or not inputs.get('available') or age>2:
        return {'available':False,'reason':'stale-or-disconnected' if age>2 else (inputs or {}).get('reason','waiting-for-game'), 'requiresGameBuild':bool(inputs and inputs.get('reason')=='requires-input-observation-game-build')}
    reset=session is not None and session!=active_session
    cursor=0 if reset else after_sequence
    events=[e for e in inputs['events'] if e['sequence']>cursor][:limit]
    def named(e):
        out=dict(e);names=NAMES[e['source']]
        for key in ('buttons','pressed','released'):
            if key in e:out[key+'Names']=[n for bit,n in enumerate(names) if e[key]&(1<<bit)]
        return out
    presses={}
    durations={}
    for event in inputs['events']:
        source=event['source'];result={}
        for bit,name in enumerate(NAMES[source]):
            key=(source,bit)
            if event['pressed']&(1<<bit):presses[key]=event['at']
            if event['released']&(1<<bit):
                started=presses.pop(key,None)
                result[name]=max(0,round((event['at']-started)*1000)) if started is not None else None
        durations[event['sequence']]=result
    def event_named(e):
        return {**named(e),'releasedDurationsMs':durations[e['sequence']]}
    states=[named(e) for e in inputs['sources']]
    user_active=any(e['buttons'] or (e['source']=='controller' and any(abs(v)>4096 for v in e['axes'])) for e in states if e['source'] in ('keyboard','controller')) or (inputs['lastUserAt']>0 and inputs['sampledAt']-inputs['lastUserAt']<0.5)
    return {**inputs,'session':active_session,'sessionReset':reset,'receivedAgeSeconds':max(0,age),'userActive':bool(user_active),'events':[event_named(e) for e in events],'sources':states,'historyLost':cursor<inputs['oldestSequence']-1 or any(g['to']>cursor and g['from']<=inputs['sequence'] for g in inputs.get('captureGaps',[])),'cursorAhead':cursor>inputs['sequence'],'nextSequence':events[-1]['sequence'] if events else inputs['sequence'],'axisUnits':{'controller':'signed-32767, left x/y then right x/y','agent':'signed-32767, left x/y then right x/y','mouse':'last motion delta in host pixels; not a held stick'},'meaning':'input intent; not confirmation that a gameplay action succeeded'}
