"""Transport-independent MCP queries and bounded Link input actions."""
import json,base64,math
COMMON={'keyword':{'type':'string'},'category':{'type':'string'},'layer':{'type':'string','enum':['s','k','d']},'completion':{'type':'string','enum':['all','completed','missing','unknown']},'limit':{'type':'integer','minimum':1,'maximum':200}}
def tool(name,description,properties,required=[]):return {'name':name,'description':description,'inputSchema':{'type':'object','properties':properties,'required':required,'additionalProperties':False},'annotations':{'readOnlyHint':True,'destructiveHint':False,'openWorldHint':False}}
TOOLS=[tool('get_guide_image','Return one registered original cached guide image as native MCP image content. Use this when a get_point_guide image URL is blocked by a browser warning or cannot render. Use only mediaId supplied by get_point_guide; never substitute searched/generated pictures.',{'mediaId':{'type':'string'}},['mediaId']),tool('get_live_position','Read live player position and facing from the local telemetry mod, falling back to calibrated Ryujinx memory.',{}),tool('search_points','Search offline TOTK points by name, category, layer and latest save completion.',COMMON),tool('get_point_guide','Read the complete original walkthrough in ordered guide.blocks/steps and deduplicated media. Use returned original signed HTTPS image URLs in article order; never substitute keyword-search or generated pictures. If an image URL is blocked, call get_guide_image with the supplied mediaId to obtain the exact cached original as MCP image content. Refresh this tool if links expire. available/publicAvailable/errors describe cache and URL availability; HTTP success does not guarantee renderer support.',{'id':{'type':'integer'}},['id']),tool('get_save_progress','Read latest valid save, unlocked towers and mapped completion states.',{}),tool('nearby_points','Find nearest map points from game x,z coordinates.',{**COMMON,'x':{'type':'number'},'z':{'type':'number'}},['x','z'])]
LINK_ACTIONS={'get_link_control_status':'status','move_link':'move','turn_link':'turn','jump_link':'jump','attack_link':'attack','interact_link':'interact','stop_link':'stop'}
AXIS={'type':'number','minimum':-1,'maximum':1}
DURATION={'type':'integer','minimum':1,'maximum':5000}
for name,action in LINK_ACTIONS.items():
 properties={} if action in ('status','stop') else {'duration_ms':DURATION}
 required=[]
 if action in ('move','turn'):properties={**properties,'x':AXIS,'y':AXIS};required=['x','y']
 descriptions={
  'status':'Read Mod version and availability of Link input control.',
  'move':'Move Link with the left stick for a bounded duration (default 500 ms). x/y are -1 to 1, relative to the camera. Perform only when the user requests game movement.',
  'turn':'Turn the camera with the right stick for a bounded duration (default 500 ms). x/y are -1 to 1.',
  'jump':'Press X to make Link jump once (default 150 ms).',
  'attack':'Press Y to make Link attack once (default 150 ms). Perform only when the user requests an attack.',
  'interact':'Press A to interact with the current in-game prompt once (default 150 ms).',
  'stop':'Release virtual Link input immediately. Physical controller input is unaffected.'}
 definition=tool(name,descriptions[action],properties,required)
 definition['annotations']={'readOnlyHint':action=='status','destructiveHint':False,'idempotentHint':action in ('status','stop'),'openWorldHint':False}
 TOOLS.append(definition)

# Combination input is expressed in Nintendo button names, independently of
# physical Xbox/Switch labels. Existing native v2/v3 packet validation is reused.
from link_control import BUTTONS
STICK={'type':'object','properties':{'x':AXIS,'y':AXIS},'required':['x','y'],'additionalProperties':False}
INPUT={'buttons':{'type':'array','items':{'type':'string','enum':list(BUTTONS)},'maxItems':16},'left_stick':STICK,'right_stick':STICK,'duration_ms':DURATION}
for name,action,props,required,description in [
 ('input_link','input',INPUT,[],'Apply bounded simultaneous Nintendo buttons and both sticks (default 500 ms, maximum 5000 ms). ZL locks on/raises shield, ZR aims bow, Y attacks, X jumps, B sprints/cancels. Physical layout does not change these names. Call stop_link to release virtual input.'),
 ('sequence_link','sequence',{'steps':{'type':'array','minItems':1,'maxItems':8,'items':{'type':'object','properties':INPUT,'additionalProperties':False}}},['steps'],'Execute 1–8 bounded input steps, total at most 5000 ms. Only when the user requests movement or combat; do not retry mutations after a timeout. Use a short sequence then observe again.')]:
 LINK_ACTIONS[name]=action
 definition=tool(name,description,props,required)
 definition['annotations']={'readOnlyHint':False,'destructiveHint':False,'idempotentHint':False,'openWorldHint':False}
 TOOLS.append(definition)
TOOLS.append(tool('get_game_frame','Capture a fresh frame rendered by the native game as an MCP image, with capture timestamps and source dimensions. Never captures the desktop. Requires the native map client and a running native game. No cached-frame fallback.',{}))

TOOLS.append(tool('get_input_observation','Read game-only user keyboard actions, raw mouse/controller input, agent virtual input and bounded recent press/release events. Poll using nextSequence as after_sequence and the returned session; historyLost indicates overwritten events. A button press is intent, not proof an attack occurred. Requires a native game build with input observation.',{'after_sequence':{'type':'integer','minimum':0},'session':{'type':'string'},'limit':{'type':'integer','minimum':1,'maximum':256}}))


TOOLS.append(tool('export_input_trace','Freeze retained game-only input history (up to 20000 events / 10 minutes) as a local JSON export. Returns traceId, local path, gaps and eventCount. Read it with read_input_trace pages; no need to race live polling. Missing events cannot be recovered. Exports retain at most 16 files / 24 hours, cleaned on the next export.',{'after_sequence':{'type':'integer','minimum':0},'session':{'type':'string'}}))
TOOLS.append(tool('read_input_trace','Read an immutable exported input trace by trace_id. Follow nextOffset while hasMore. Raw controller south/east/west/north are physical positions, not proof of Nintendo button names or gameplay actions.',{'trace_id':{'type':'string'},'offset':{'type':'integer','minimum':0},'limit':{'type':'integer','minimum':1,'maximum':512}},['trace_id']))

from game_console import DEFINITIONS as CONSOLE_DEFINITIONS, NAMES as CONSOLE_NAMES
for name, description, properties, required, readonly in CONSOLE_DEFINITIONS:
 definition=tool(name,description,properties,required)
 definition['annotations']={'readOnlyHint':readonly,'destructiveHint':False,'idempotentHint':readonly,'openWorldHint':False}
 TOOLS.append(definition)

def validate(spec,value):
 typ=spec['type']
 if typ=='object':
  if not isinstance(value,dict) or any(k not in spec.get('properties',{}) for k in value) or any(k not in value for k in spec.get('required',[])):raise ValueError('Invalid arguments')
  for k,v in value.items():validate(spec['properties'][k],v)
 elif typ=='array':
  if not isinstance(value,list) or not spec.get('minItems',0)<=len(value)<=spec.get('maxItems',200):raise ValueError('Invalid array')
  for v in value:validate(spec['items'],v)
 else:
  ok=type(value) is bool if typ=='boolean' else isinstance(value,str) if typ=='string' else isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value) if typ=='number' else isinstance(value,int) and not isinstance(value,bool)
  if not ok or 'enum' in spec and value not in spec['enum'] or 'minimum' in spec and value<spec['minimum'] or 'maximum' in spec and value>spec['maximum']:raise ValueError('Invalid argument')

def dispatch(service,msg):
  rid=None
  try:
   rid=msg.get('id');method=msg.get('method');params=msg.get('params',{})
   if 'id' not in msg:return None
   if method=='initialize':
    requested=params.get('protocolVersion');version=requested if requested in ('2024-11-05','2025-03-26','2025-06-18','2025-11-25') else '2025-11-25'
    result={'protocolVersion':version,'capabilities':{'tools':{}},'serverInfo':{'name':'totk-offline','version':'1.0.0'}}
   elif method=='ping':result={}
   elif method=='tools/list':result={'tools':TOOLS}
   elif method=='tools/call':
    name=params.get('name');args=params.get('arguments',{});definition=next((t for t in TOOLS if t['name']==name),None)
    if definition is None:raise LookupError('Unknown tool')
    try:
     validate(definition['inputSchema'],args)
     if name in ('export_input_trace','read_input_trace'):
      from input_trace import export,read
      value=(export if name=='export_input_trace' else read)(**args)
      return {'jsonrpc':'2.0','id':rid,'result':{'content':[{'type':'text','text':json.dumps(value,ensure_ascii=False)}],'structuredContent':value,'isError':False}}
     if name=='get_input_observation':
      from input_observation import read
      value=read(**args)
      return {'jsonrpc':'2.0','id':rid,'result':{'content':[{'type':'text','text':json.dumps(value,ensure_ascii=False)}],'structuredContent':value,'isError':False}}
     if name=='get_game_frame':
      from game_capture import capture
      from game_control import ControlError
      try:data,value=capture()
      except ControlError as error:raise ValueError(str(error)) from error
      return {'jsonrpc':'2.0','id':rid,'result':{'content':[{'type':'text','text':json.dumps(value)},{'type':'image','mimeType':value['mimeType'],'data':base64.b64encode(data).decode()}],'structuredContent':value,'isError':False}}
     if name=='get_guide_image':
      from guide_media import MediaError
      try:data,meta=service.guide_media.read(args['mediaId'])
      except MediaError as error:raise ValueError(error.code)
      if len(data)>2*1024*1024:raise ValueError('media_exceeds_mcp_image_limit; use signed HTTPS URL')
      value={'mediaId':args['mediaId'],**meta,'source':'original-local-cache'}
      return {'jsonrpc':'2.0','id':rid,'result':{'content':[{'type':'text','text':json.dumps(value)},{'type':'image','mimeType':meta['mimeType'],'data':base64.b64encode(data).decode()}],'structuredContent':value,'isError':False}}
     if name in CONSOLE_NAMES:
      from game_console import execute
      from game_control import ControlError
      try:value=execute(name,args)
      except ControlError as error:raise ValueError(str(error)) from error
     elif name in LINK_ACTIONS:
      from link_control import execute
      from game_control import ControlError
      try:state=execute({'action':LINK_ACTIONS[name],**args})
      except ControlError as error:raise ValueError(str(error)) from error
      value={'action':LINK_ACTIONS[name],'modVersion':state.get('modVersion'),'link':state.get('link',{'available':False})}
     else:
      from mod_telemetry import position
      value=position() if name=='get_live_position' else service.progress() if name=='get_save_progress' else service.guide(**{'pid':args['id']}) if name=='get_point_guide' else service.search(**args)
     result={'content':[{'type':'text','text':json.dumps(value,ensure_ascii=False)}],'structuredContent':value,'isError':False}
    except (ValueError,TypeError) as e:result={'content':[{'type':'text','text':str(e)}],'isError':True}
   else:raise LookupError('Method not found')
   response={'jsonrpc':'2.0','id':rid,'result':result}
  except Exception as e:response={'jsonrpc':'2.0','id':rid,'error':{'code':-32700 if isinstance(e,json.JSONDecodeError) else -32601 if isinstance(e,LookupError) else -32603,'message':str(e)}}
  return response
