"""Read-only adventure-log stage decoding. Missing/unrecognized values stay unknown."""
import json
from paths import WEBUI
class QuestProgress:
 def __init__(self,path=None):
  ref=json.loads((path or WEBUI/'quest-reference.json').read_text())
  self.quests=ref['quests'];self.point_quests=ref['pointQuests']
 def decode(self,flags):
  quests=[];byid={};categories={}
  for q in self.quests:
   value=flags.get(q['hash']);stage=q['steps'].get(str(value))
   status='unknown' if stage is None else 'completed' if value==q['complete'] else 'not_started' if stage in ('NotReady','Ready') else 'in_progress'
   row={k:q[k] for k in ('id','name','category')};row.update(status=status,stage=stage)
   quests.append(row);byid[q['id']]=row
   c=categories.setdefault(q['category'],dict(total=0,completed=0,inProgress=0,notStarted=0,unknown=0));c['total']+=1;c[{'completed':'completed','in_progress':'inProgress','not_started':'notStarted','unknown':'unknown'}[status]]+=1
  states={};details={}
  for pid,ids in self.point_quests.items():
   rows=[byid[qid] for qid in ids];details[pid]=rows
   if all(r['status']!='unknown' for r in rows):states[pid]=all(r['status']=='completed' for r in rows)
  return dict(quests=quests,questCategories=categories,questPoints=details),states
