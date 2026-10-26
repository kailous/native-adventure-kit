"""Read-only LookAtCamera telemetry, calibrated to a single Ryujinx session.

No scanning during requests, game function calls, hooks or memory writes.
"""
import json,math,struct,time,subprocess
from pathlib import Path
from macos_position import Memory,process_identity
CONFIG=Path.home()/'Library/Application Support/TOTK Offline/camera-memory.json'
_identity_cache=None

def decode(raw,player,expected_vtable):
 if len(raw)!=144 or struct.unpack_from('<Q',raw)[0]!=expected_vtable:raise ValueError('camera object changed')
 pos=struct.unpack_from('<3d',raw,96);at=struct.unpack_from('<3d',raw,120)
 floats=struct.unpack_from('<6f',raw,56);up=struct.unpack_from('<3f',raw,80);matrix=struct.unpack_from('<12f',raw,8)
 if not all(math.isfinite(v) and abs(v)<20000 for v in (*pos,*at,*floats,*up,*matrix)):raise ValueError('invalid camera data')
 if max(abs(a-b) for a,b in zip((*pos,*at),floats))>.02:raise ValueError('inconsistent camera positions')
 if sum((at[i]-player[i])**2 for i in range(3))>2500:raise ValueError('camera is not near player')
 delta=[at[i]-pos[i] for i in range(3)];length=math.sqrt(sum(v*v for v in delta))
 if not .1<length<100 or math.hypot(delta[0],delta[2])<.01:raise ValueError('invalid look direction')
 rows=[matrix[i*4:i*4+3] for i in range(3)]
 if any(abs(sum(v*v for v in row)-1)>.03 for row in rows) or abs(sum(v*v for v in up)-1)>.03:raise ValueError('invalid camera basis')
 if any(abs(sum(a*b for a,b in zip(rows[i],rows[j])))>.03 for i in range(3) for j in range(i)):raise ValueError('nonorthogonal camera')
 if sum(-rows[2][i]*delta[i]/length for i in range(3))<.995:raise ValueError('view matrix disagrees with look direction')
 return {'available':True,'heading':math.degrees(math.atan2(delta[0],-delta[2]))%360,'position':list(pos),'target':list(at),'basisVerified':True,'fovVerified':False,'source':'Ryujinx read-only camera','sessionCalibration':True}

def position(player):
 # The archived Ryujinx calibration was for 1.0.0. Native 1.4.3 sends its own camera telemetry.
 return {'available':False,'heading':None,'basisVerified':False,'fovVerified':False}
