"""Editable, typed live-chat commands. Templates never execute shell or regex input."""
from difflib import SequenceMatcher
import math
import re
import unicodedata

WEATHERS = {'clear':'晴天','cloudy':'阴天','rain':'小雨','heavy_rain':'大雨',
            'thunder':'雷暴','thunder_rain':'雷雨','snow':'下雪'}
MOVEMENTS = {'forward':('向前移动',0,1), 'back':('向后移动',0,-1),
             'left':('向左移动',-1,0), 'right':('向右移动',1,0),
             'run':('奔跑',0,1), 'jump':('跳跃',0,0), 'stop':('停止移动',0,0),
             'attack':('攻击',0,0), 'guard':('防御／锁定目标',0,0),
             'aim':('拉弓瞄准',0,0), 'interact':('互动',0,0),
             'throw':('投掷准备',0,0), 'crouch':('切换蹲下',0,0),
             'dodge_left':('左侧跳',-1,0), 'dodge_right':('右侧跳',1,0),
             'backflip':('后空翻',0,-1)}
MOVEMENT_BUTTONS = {'run':['b'], 'jump':['x'], 'attack':['y'], 'guard':['zl'],
                    'aim':['zr'], 'interact':['a'], 'throw':['r'], 'crouch':['l_stick'],
                    'dodge_left':['zl','x'], 'dodge_right':['zl','x'], 'backflip':['zl','x']}
SHORT_ACTIONS = {'jump','attack','interact','crouch','dodge_left','dodge_right','backflip'}
ACTIONS = {**{'link:'+key:value[0] for key,value in MOVEMENTS.items()},'spawn':'赠送物品（自动匹配）','heal':'加血','damage':'减血',
           'health_cap':'锁定最大血量','health_cap_off':'解除最大血量锁定',
           'stamina_lock':'锁定体力','stamina_unlock':'解除体力锁定',
           'rupees_zero':'卢比清零','rupees_add':'增加卢比',
           **{'weather:'+key:'天气：'+name for key,name in WEATHERS.items()}}


def movement_defaults():
    aliases={'forward':'移动|前进|向前移动','back':'后退|向后移动','left':'左移|向左移动',
             'right':'右移|向右移动','run':'奔跑|跑步','jump':'跳跃|跳一下','stop':'停止移动|停下|停止动作',
             'attack':'攻击|砍一下','guard':'防御|举盾|锁定目标','aim':'瞄准|拉弓',
             'interact':'互动|交互|拾取','throw':'准备投掷','crouch':'蹲下|切换蹲下',
             'dodge_left':'左侧跳','dodge_right':'右侧跳','backflip':'后空翻'}
    return [dict(action='link:'+key,keywords=aliases[key],enabled=True,
                 **({'duration_ms':150 if key in SHORT_ACTIONS else 1000} if key!='stop' else {})) for key in MOVEMENTS]


def defaults():
    rows = [('spawn','送{物品}',None),('heal','加血',1),('damage','减血',1),
            ('health_cap','锁定最大血量|锁定血量上限',40),
            ('health_cap_off','解除最大血量锁定|解除血量上限',None),
            ('stamina_lock','锁定体力',None),('stamina_unlock','解除体力锁定',None),
            ('rupees_zero','卢比清零|清空卢比',None),
            ('rupees_add','加卢比{数量}|加{数量}卢比|可以加{数量}卢比',None)]
    for key,name in WEATHERS.items():
        aliases={'clear':'晴天|天晴','cloudy':'阴天','rain':'小雨|下雨','heavy_rain':'大雨',
                 'thunder':'雷暴|打雷','thunder_rain':'雷雨','snow':'下雪|雪天'}
        rows.append(('weather:'+key,aliases[key],None))
    return [dict(action=action,keywords=words,enabled=True,**({'value':value} if value is not None else {}))
            for action,words,value in rows] + movement_defaults()


def normalize(text):
    return re.sub(r'\s+', '', unicodedata.normalize('NFKC',text)).strip('。！!，,；;')


def validate_rules(rows):
    if not isinstance(rows,list) or not 1 <= len(rows) <= 64:
        raise ValueError('指令清单须包含 1–64 条规则')
    result=[]
    for row in rows:
        if not isinstance(row,dict) or row.get('action') not in ACTIONS or type(row.get('enabled')) is not bool:
            raise ValueError('指令类型或启用状态无效')
        action=row['action'];words=row.get('keywords')
        if not isinstance(words,str) or not 1<=len(words)<=300:
            raise ValueError('关键词须为 1–300 个字符，多种写法用 | 分隔')
        aliases=words.split('|')
        if len(aliases)>12 or any(not normalize(alias) for alias in aliases):
            raise ValueError('每条指令最多 12 种写法，关键词不能为空')
        token='{物品}' if action=='spawn' else '{数量}' if action=='rupees_add' else None
        for alias in aliases:
            if token and alias.count(token)!=1:
                raise ValueError(f'{ACTIONS[action]}的每种写法必须包含一次 {token}')
            plain=alias.replace(token,'') if token else alias
            if '{' in plain or '}' in plain or (token and not normalize(plain)):
                raise ValueError('模板只支持对应的 {物品} 或 {数量}，并须带文字关键词')
        clean=dict(action=action,keywords=words.strip(),enabled=row['enabled'])
        if 'name' in row:
            name=row['name']
            if not isinstance(name,str) or not 1<=len(name.strip())<=40:raise ValueError('指令名称须为 1–40 个字符')
            clean['name']=name.strip()
        if action in ('heal','damage','health_cap'):
            value=row.get('value',1 if action!='health_cap' else 40)
            if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or not .25<=value<=40 or value*4!=round(value*4):
                raise ValueError('心心数量须为 0.25–40，步长为 0.25')
            clean['value']=value
        if action.startswith('link:') and action!='link:stop':
            duration=row.get('duration_ms',150 if action.split(':',1)[1] in SHORT_ACTIONS else 1000)
            if type(duration) is not int or not 50<=duration<=3000:
                raise ValueError('人物控制时长须为 50–3000 毫秒的整数')
            clean['duration_ms']=duration
        result.append(clean)
    return result


def match_command(text, rules):
    if not isinstance(text,str) or len(text)>1000:
        raise ValueError('试匹配弹幕最多 1000 字')
    text=normalize(text);matches=[]
    for row in rules:
        if not row['enabled']:continue
        action=row['action'];token='{物品}' if action=='spawn' else '{数量}' if action=='rupees_add' else None
        for alias in row['keywords'].split('|'):
            alias=normalize(alias)
            if token:
                before,after=alias.split(token)
                pattern=re.escape(before)+(r'(.{1,80}?)' if action=='spawn' else r'([0-9]{1,8})')+re.escape(after)
                found=re.fullmatch(pattern,text)
                if not found:continue
                arg=found[1]
                if action=='rupees_add' and not 1<=int(arg)<=99999999:
                    return {'matched':False,'reason':'增加卢比须为 1–99999999 的整数'}
            elif alias!=text:continue
            else:arg=None
            matches.append({**row,'argument':arg});break
    if len(matches)!=1:
        return {'matched':False,'reason':'同时命中多条规则，已跳过' if matches else '未命中关键词'}
    command=matches[0]
    return {'matched':True,'label':command.get('name') or ACTIONS[command['action']],'command':command}


def best_item(query, items=None):
    if items is None:
        from spawn_catalog import ITEMS
        items=ITEMS
    query=normalize(query).casefold()
    if not query:raise ValueError('请在「送」后填写物品名称')
    def rank(item):
        name=normalize(item['name']).casefold();actor=item['actor'].casefold()
        if query in (name,actor):score=1.
        elif query in name:score=.85+.1*len(query)/len(name)
        elif name in query:score=.8+.1*len(name)/len(query)
        else:score=SequenceMatcher(None,query,name).ratio()*.8
        return (-score,len(name),item['actor'])
    ranked=sorted(items,key=rank)
    if not ranked or -rank(ranked[0])[0]<.52:
        raise ValueError('未找到相近的可生成物品，请换个名称')
    item=ranked[0]
    return {**item,'matchScore':round(-rank(item)[0],3)}


def preview(text, rules):
    result=match_command(text,rules)
    if result['matched'] and result['command']['action']=='spawn':
        try:result['item']=best_item(result['command']['argument'])
        except ValueError as exc:return {'matched':False,'reason':str(exc)}
    return result


def perform(command, execute):
    action=command['action']
    if action.startswith('link:'):
        key=action.split(':',1)[1];label,x,y=MOVEMENTS[key]
        args={'action':'stop'} if key=='stop' else {'action':'input','buttons':MOVEMENT_BUTTONS.get(key,[]),'left_stick':{'x':x,'y':y},'duration_ms':command.get('duration_ms',150 if key in SHORT_ACTIONS else 1000)}
        execute('control_link',args)
        return '已请求'+label+('' if key=='stop' else f"（{args['duration_ms']} 毫秒），方向相对镜头")
    if action=='spawn':
        item=best_item(command['argument'])
        result=execute('spawn_game_item',{'actor':item['actor']})
        spawn=result.get('spawn',{})
        state='已创建' if spawn.get('created') else '已提交，等待游戏确认' if spawn.get('accepted') else '游戏未确认，不自动重试'
        return f"匹配 {item['name']}（{item['actor']}） · {state}"
    if action.startswith('weather:'):
        weather=action.split(':',1)[1]
        execute('set_game_weather',{'weather':weather})
        return '已请求'+WEATHERS[weather]+'，实际天气受地区与过渡影响'
    if action in ('stamina_lock','stamina_unlock'):
        enabled=action=='stamina_lock'
        result=execute('set_game_lock',{'target':'stamina','enabled':enabled})
        return ('体力已锁定' if enabled else '体力已解锁') if result.get('staminaLocked') is enabled else '游戏未确认体力锁定状态'
    if action=='health_cap_off':
        result=execute('set_health_cap',{'enabled':False})
        return '已解除心心上限锁定' if result.get('healthCapEnabled') is False else '游戏未确认心心上限状态'
    current=execute('get_game_console_status',{})
    if action.startswith('rupees_'):
        value=current.get('rupees')
        if type(value) is not int:raise ValueError('卢比不可用，请进入游戏存档')
        if current.get('rupeesLocked'):raise ValueError('请先关闭卢比锁定')
        target=0 if action=='rupees_zero' else min(99999999,value+int(command['argument']))
        result=execute('set_game_value',{'target':'rupees','value':target})
        return f"卢比 {value} → {target}" if result.get('rupees')==target else '游戏未确认目标卢比，不自动重试'
    hearts=current.get('hearts')
    if not isinstance(hearts,(int,float)) or not math.isfinite(hearts):
        raise ValueError('血量不可用，请进入游戏存档')
    maximum=min(40,current.get('maxHearts') or 40)
    if action=='health_cap':
        target=min(maximum,command['value'])
        result=execute('set_health_cap',{'enabled':True,'value':target})
        return f'心心上限已锁定为 {target}（仍会扣血）' if result.get('healthCapEnabled') is True and result.get('healthCap')==target else '游戏未确认心心上限状态'
    if current.get('healthLocked'):raise ValueError('请先关闭心心锁定')
    if current.get('healthCapEnabled'):maximum=min(maximum,current.get('healthCap') or maximum)
    target=round(max(.25,min(maximum,hearts+command['value']*(1 if action=='heal' else -1)))*4)/4
    result=execute('set_game_value',{'target':'health','value':target})
    return f"血量 {hearts} → {target}" if result.get('hearts')==target else '游戏未确认目标血量，不自动重试'
