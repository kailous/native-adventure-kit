"""Shared offline map data and read-only save progress."""
import json, math, struct, re
from server import ROOT, SaveSource
from data_packs import read_json, read_resource
from quest_progress import QuestProgress
from compendium_progress import CompendiumProgress
TYPE_KEYS={'神庙':['shrines'],'树根':['lightroots'],'鸟望台':['towers'],'呀哈哈':['hidden_koroks'],'呀哈哈*2':['carry_koroks'],'魔犹伊遗失物':['bubbuls'],'洞穴入口':['caves'],'井':['wells'],'地洞入口':['chasms'],'残旧的地图':['old_maps'],'贤者的遗志':['sages_wills'],'卡邦达立牌':['addison_signposts'],'设计图石板':['schema_stones','yiga_schematics']}
class MapService:
 def __init__(self,source):
  self.structured=read_json('structured-guides.json',{});self.compendium_progress=CompendiumProgress();self.quest_progress=QuestProgress();self.source=source
  self.points=read_json('gamersky-archive.json',{'points':[]})['points'];self.index=read_json('offline/index.json',{})
  ref=json.loads((ROOT/'webui/save-reference.json').read_text());ref['objs']['towers']=json.loads((ROOT/'webui/towers.json').read_text());self.matches={};rules={c['k']:c['r'] for c in ref['cats']};rules['towers']='tower'
  for p in self.points:
   candidates=[(math.hypot(o['x']-p['x'],o['z']-p['z']),o,rules[k]) for k in TYPE_KEYS.get(p['type'],[]) for o in ref['objs'][k] if o['L']==p['L']]
   candidates.sort(key=lambda a:a[0])
   if candidates and candidates[0][0]<35 and (len(candidates)==1 or candidates[1][0]-candidates[0][0]>3):self.matches[p['id']]=candidates[0][1:]
  from guide_media import GuideMedia
  self.guide_media=GuideMedia(ROOT/'webui',self.index,reader=read_resource);self.public_base=lambda:None
 def progress(self):
  data,status=self.source.newest()
  if data is None:
   quests,_=self.quest_progress.decode({});return {**status,**quests,'compendium':self.compendium_progress.decode(None,{}),'states':{}}
  from server import parse_flags
  flags=parse_flags(data);go=None
  from player_stats import player_stats
  stats=player_stats(flags)
  for off in range(0x28,len(data)-7,8):
   key,value=struct.unpack_from('<II',data,off)
   if key==0xa3db7114:go=value;break
  guids=set()
  if go is not None:
   for off in range(go,len(data)-7,8):
    value=struct.unpack_from('<Q',data,off)[0]
    if not value:break
    guids.add(str(value))
  states={}
  for pid,(o,rule) in self.matches.items():
   v=flags.get(o.get('h'),0);states[str(pid)]=o['g'] in guids if rule=='guid' else v==1654019904 if rule=='clear' else v==404286466 if rule=='open' else v==1 if rule=='tower' else v!=0
  quests,quest_states=self.quest_progress.decode(flags);states.update(quest_states)
  compendium=self.compendium_progress.decode(data,flags);states.update(self.compendium_progress.point_states(compendium))
  return {**status,**quests,'compendium':compendium,'playerStats':stats,'states':states,'matchedPoints':len(states),'completedPoints':sum(states.values())}
 def search(self,keyword='',category=None,layer=None,completion='all',limit=50,x=None,z=None):
  if layer not in (None,'s','k','d'):raise ValueError('layer must be s, k or d')
  if completion not in ('all','completed','missing','unknown'):raise ValueError('invalid completion')
  states=self.progress()['states'] if completion!='all' else {};items=[]
  for p in self.points:
   if keyword.lower() not in (p['n']+' '+p['type']+' '+p['description']).lower() or category and p['type']!=category or layer and p['L']!=layer:continue
   state=states.get(str(p['id']))
   if completion=='completed' and state is not True or completion=='missing' and state is not False or completion=='unknown' and state is not None:continue
   row={k:p[k] for k in ('id','n','type','x','z','L')}
   if completion!='all':row['completed']=state
   if x is not None and z is not None:row['distance']=round(math.hypot(p['x']-x,p['z']-z),1)
   items.append(row)
  if x is not None:items.sort(key=lambda p:p['distance'])
  return {'total':len(items),'points':items[:max(1,min(int(limit),200))]}
 def guide(self,pid):
  p=next((p for p in self.points if p['id']==int(pid)),None)
  if p is None:raise ValueError('point not found')
  attachments=[];urls=list(p.get('media',[]))
  for m in p.get('metas',[]):urls.extend(m.get(k) for k in ('imageUrl','videoUrl','contentUrl') if m.get(k))
  for url in dict.fromkeys(urls):
   item=self.index.get('https:'+url if url.startswith('//') else url)
   if item:
    entry={'kind':item['kind'],'path':item['path'],'sourceUrl':url}
    if item['kind']=='article':entry['article']=read_json(item['path'],{})
    attachments.append(entry)
  from guide_media import adapt_guide
  return adapt_guide({**{k:p[k] for k in ('id','n','type','x','z','L')},'description':re.sub('<[^>]+>','',p['description']),'attachments':attachments,'structured':self.structured.get('points',{}).get(str(p['id'])),'articles':{a['articleId']:self.structured.get('articles',{}).get(a['articleId']) for a in self.structured.get('points',{}).get(str(p['id']),{}).get('attachments',[]) if a.get('articleId')}},self.guide_media,self.public_base())
