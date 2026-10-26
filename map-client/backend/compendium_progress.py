"""Read-only picture-book registration and current armor pouch decoding."""
import json,re,struct
from paths import WEBUI
class CompendiumProgress:
 def __init__(self,path=None):
  self.ref=json.loads((path or WEBUI/'compendium-save-reference.json').read_text())
 def decode(self,data,flags):
  ref=self.ref;states={};counts=dict(registered=0,bookTotal=len(ref['books']),bookUnknown=0,owned=0,armorTotal=len(ref['armor']),armorUnknown=0)
  methods={ref['enums']['Unopened']:'unregistered',ref['enums']['TakePhoto']:'photo',ref['enums']['Buy']:'purchased'}
  for key,row in ref['books'].items():
   method=methods.get(flags.get(row['hash']),'unknown');states[key]={'status':method}
   counts['bookUnknown']+=method=='unknown';counts['registered']+=method in ('photo','purchased')
  owned=None
  try:
   pointer=flags[ref['armorNamesHash']]
   # Pointer arrays must follow the hash table, whose sentinel stores its end.
   end=flags.get(0xa3db7114,0x28+8*len(flags))
   if not data or pointer<end:raise ValueError('invalid pointer')
   count=struct.unpack_from('<I',data,pointer)[0]
   if not 0<count<=1000 or pointer+4+count*64>len(data):raise ValueError('invalid array')
   owned={}
   for i in range(count):
    raw=data[pointer+4+i*64:pointer+4+(i+1)*64]
    if b'\0' not in raw:raise ValueError('unterminated name')
    name=raw.split(b'\0',1)[0].decode('ascii')
    if not name:continue
    if not re.fullmatch(r'Armor_\d+_(Head|Upper|Lower)',name):raise ValueError('invalid armor')
    variant=ref['variants'].get(name)
    if variant:owned.setdefault(variant['base'],[]).append({'actor':name,'level':variant['level']})
  except (KeyError,ValueError,UnicodeError,struct.error,IndexError):owned=None
  for key in ref['armor']:
   status='unknown' if owned is None else 'owned' if key in owned else 'not_owned'
   states[key]={'status':status,'variants':[] if owned is None else owned.get(key,[])}
   counts['owned']+=status=='owned';counts['armorUnknown']+=status=='unknown'
  materials=None
  try:
   names=flags[ref['materialNamesHash']];stock=flags[ref['materialStockHash']]
   end=0x28+8*len(flags)
   if not data or min(names,stock)<end:raise ValueError('invalid material pointer')
   length=struct.unpack_from('<I',data,names)[0]
   if not 0<length<=1000 or struct.unpack_from('<I',data,stock)[0]!=length or names+4+length*64>len(data) or stock+4+length*4>len(data):raise ValueError('invalid material array')
   materials={}
   for i in range(length):
    raw=data[names+4+i*64:names+4+(i+1)*64]
    if b'\0' not in raw:raise ValueError('unterminated material name')
    actor=raw.split(b'\0',1)[0].decode('ascii')
    if not actor:continue
    if not re.fullmatch(r'[A-Za-z0-9_]+',actor):raise ValueError('invalid material actor')
    quantity=struct.unpack_from('<i',data,stock+4+i*4)[0]
    if not 0<=quantity<=999999:raise ValueError('invalid material quantity')
    materials[actor]=materials.get(actor,0)+quantity
  except (KeyError,ValueError,UnicodeError,struct.error,IndexError):materials=None
  for key,actor in ref['materials'].items():
   states[key]['quantity']=None if materials is None else materials.get(actor,0)
  counts['materialKindsOwned']=None if materials is None else sum(materials.get(a,0)>0 for a in ref['materials'].values())
  counts['materialTotal']=len(ref['materials'])
  return {'states':states,**counts}

 def point_states(self,progress):
  result={}
  for pid,ids in self.ref['pointArmor'].items():
   rows=[('owned' if key=='Armor_001_Head' and progress['states']['Armor_1152_Head']['status']=='owned' else progress['states'][key]['status']) for key in ids]
   if all(status in ('owned','not_owned') for status in rows):result[pid]=all(status=='owned' for status in rows)
  return result
