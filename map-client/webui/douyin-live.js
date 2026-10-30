/* Figma stream framework: separate connection, list, editor, display and records. */
window.mountDouyinControl=(host,options={})=>{
 const copy=x=>JSON.parse(JSON.stringify(x));
 const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const switcher=(id,label,on)=>`<div class="sd-switch"><label for="${id}">${esc(label)}</label><label class="gc-switch"><input id="${id}" type="checkbox" aria-label="${esc(label)}" ${on?'checked':''}><span></span></label></div>`;
 const field=(id,label,value='',extra='')=>`<label class="sd-field" for="${id}">${esc(label)}<input id="${id}" value="${esc(value)}" ${extra}></label>`;
 const button=(id,label,primary=false)=>`<button type="button" id="${id}" ${primary?'class="gc-primary"':''}>${esc(label)}</button>`;
 const hint=text=>`<p class="sd-note">${esc(text)}</p>`;
 const $=id=>host.querySelector('#'+id);
 let generation=0;
 let alive=true,timer,mutating=false,state=null,view='main',draft=[],dirty=false,room='',kind='live',parsed=null,editing=null,editIndex=-1,displayDraft=null,group=null;
 const titles={main:'直播互动',rules:'指令清单',edit:'编辑指令',display:'弹幕显示设置',records:'触发记录'};
 const statusNames={stopped:'未连接',connecting:'正在连接',warming:'预热中',connected:'已连接',reconnecting:'正在重连',ended:'直播已结束',error:'连接异常'};
 const running=()=>state&&!['stopped','error'].includes(state.state);
 const name=r=>r.name||state.actions[r.action]||r.action;
 function error(message){const el=$('streamMessage');if(el)el.textContent=message;}
 async function api(body){
  const response=await fetch('/api/douyin',body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:{cache:'no-store'});
  const data=await response.json();if(!response.ok)throw Error(data.error||'直播服务暂不可用');return data;
 }
 async function mutate(body,after){
  if(mutating)return;generation++;if(view==='edit')editing=readEditing();mutating=true;host.querySelectorAll('button,input,select,textarea').forEach(el=>el.disabled=true);
  try{
   const data=await api(body);if(!alive)return;
   if(data.state){state=data;}
   else if(body.action==='display'){state.display=data;}
   if(after)await after(data);else render();
  }catch(e){if(alive){render();error(e.message);}}
  finally{mutating=false;if(alive&&view==='main')paint();}
 }
 function go(next){view=next;render();options.view?.(next);}
 function header(){
  return `<header class="sd-title"><h2>${view==='main'?'<img src="branding/navigation/stream-active.svg" width="24" height="24" alt="">':''}${titles[view]}</h2><button type="button" id="closeStreamView" aria-label="关闭直播互动"><img src="branding/game-control/close.svg" width="18" height="18" alt=""></button></header>`;
 }
 function render(){
  if(!alive)return;
  if(!state){host.innerHTML='<p class="sd-note" role="status">正在读取直播设置…</p>';return;}
  host.innerHTML=`${view!=='main'?'<button type="button" class="sd-back" id="streamBack">← 返回'+(view==='edit'?'指令清单':'直播互动')+'</button>':''}<section class="sd-card">${header()}<div id="streamViewBody" class="sd-body"></div><p id="streamMessage" class="sd-message" role="status"></p></section>`;
  $('closeStreamView').onclick=()=>options.close?.();
  if($('streamBack'))$('streamBack').onclick=()=>go(view==='edit'?'rules':'main');
  if(view==='main')renderMain();else if(view==='rules')renderRules();else if(view==='edit')renderEditor();else if(view==='display')renderDisplay();else renderRecords();
 }
 function eventsHTML(rows){return rows.length?rows.map(row=>`<li><strong>${esc([row.user,row.text].filter(Boolean).join(' · '))}</strong><span>${esc(row.result)}</span></li>`).join(''):'<li class="sd-note">暂未收到新的弹幕</li>';}
 function renderMain(){
  $('streamViewBody').innerHTML=`<strong class="sd-label">直播间连接</strong><output id="streamConnection" class="sd-note"></output>${field('streamRoom','直播码 / 分享口令',room,'maxlength="3000" placeholder="粘贴抖音分享文字或短链接"')}${button('resolveStream','解析直播码')}<p id="streamRoomResult" class="sd-note">${parsed?esc('已识别'+(parsed.kind==='room'?'房间 ID':'直播间编号')+'：'+parsed.room):'解析后显示直播间编号'}</p><details class="sd-advanced" id="streamNumericOptions" ${/^\d+$/.test(room)?'':'hidden'}><summary>直接使用数字编号</summary><label class="sd-field">编号类型<select id="streamKind"><option value="live">直播间编号</option><option value="room">分享链接中的房间 ID</option></select></label></details><div class="sd-actions">${button('connectStream','连接直播间',true)}${button('disconnectStream','断开连接')}</div>${switcher('streamCommands','执行观众指令',state.commandsEnabled)}${switcher('streamDisplay','游戏内弹幕',state.display?.settings.enabled)}${hint('连接、弹幕显示、指令执行分别控制；只看弹幕时可关闭观众指令。')}${field('streamCooldown','全局冷却（秒）',state.cooldown,'type="number" min="1" max="60"')}${button('openStreamRules','管理指令清单 →')}${button('exportStreamRules','导出指令清单')}${button('openStreamDisplay','弹幕显示设置 →')}`;
  host.insertAdjacentHTML('beforeend',`<section class="sd-card sd-record-card"><div class="sd-record-head"><h3>触发记录</h3><button id="openStreamRecords" type="button">查看全部 →</button></div><ul id="streamRecent" class="sd-records"></ul></section>`);
  $('streamRoom').oninput=()=>{room=$('streamRoom').value;parsed=null;$('streamRoomResult').textContent='解析后显示直播间编号';$('streamNumericOptions').hidden=!/^\d+$/.test(room.trim());};
  $('streamKind').value=kind;$('streamKind').onchange=()=>{kind=$('streamKind').value;parsed=null;};
  $('resolveStream').onclick=()=>mutate({action:'resolve',room,kind},data=>{parsed=data;render();});
  $('connectStream').onclick=()=>mutate({action:'start',room:parsed?.room||room,kind:parsed?.kind||kind});
  $('disconnectStream').onclick=()=>mutate({action:'stop'});
  $('streamCommands').onchange=()=>mutate({action:'commands',commandsEnabled:$('streamCommands').checked});
  $('streamDisplay').onchange=()=>mutate({action:'display',settings:{...state.display.settings,enabled:$('streamDisplay').checked}});
  $('streamCooldown').onchange=()=>mutate({action:'save',rules:state.rules,cooldown:Number($('streamCooldown').value)});
  $('exportStreamRules').onclick=exportRules;
  $('openStreamRules').onclick=()=>{group=null;go('rules');};
  $('openStreamDisplay').onclick=()=>{displayDraft=copy(state.display.settings);go('display');};
  $('openStreamRecords').onclick=()=>go('records');paint();
 }
 function paint(){
  if(view!=='main'||!$('streamConnection'))return;
  $('streamConnection').textContent=(statusNames[state.state]||state.state)+(state.connectionError?' · '+state.connectionError:'');
  $('streamRoom').disabled=mutating||running();$('streamKind').disabled=mutating||running();
  $('resolveStream').disabled=mutating||running();$('connectStream').disabled=mutating||running();$('disconnectStream').disabled=mutating||state.state==='stopped';
  $('streamCommands').checked=state.commandsEnabled;$('streamDisplay').checked=!!state.display?.settings.enabled;
  $('streamRecent').innerHTML=eventsHTML((state.events||[]).slice(0,3));
 }
 function groups(){
  const buckets=new Map();draft.forEach((rule,index)=>{
   const key=rule.action.startsWith('link:')?'link':rule.action.startsWith('weather:')?'weather':rule.action.startsWith('health_cap')?'cap':rule.action.startsWith('stamina_')?'stamina':'rule:'+index;
   if(!buckets.has(key))buckets.set(key,[]);buckets.get(key).push(index);
  });return [...buckets].map(([key,indices])=>({key,indices,title:key==='link'?'人物控制':key==='weather'?'天气控制':key==='cap'?'心心上限':key==='stamina'?'体力锁定':draft[indices[0]].action==='spawn'&&!draft[indices[0]].name?'赠送物品':name(draft[indices[0]])})).sort((a,b)=>{const rank=g=>g.key==='weather'?1:g.key==='cap'?4:g.key==='stamina'?5:({spawn:0,heal:2,damage:3,rupees_zero:6,rupees_add:7}[draft[g.indices[0]].action]??8);return rank(a)-rank(b);});
 }
 function exportRules(){
   const rules=dirty?draft:state.rules;
   if(!rules.length){error('当前清单没有可导出的指令。');return;}
   const cell=value=>String(value??'').replaceAll('\\','\\\\').replaceAll('|','\\|').replace(/[\r\n]+/g,' ');
   const lines=['# 直播全部指令清单','',dirty?'来源：当前编辑清单（含未保存修改）。':'来源：当前指令清单。','',`全局冷却：${state.cooldown} 秒；停止动作不受冷却限制。`,'','| 指令名称 | 执行效果 | 弹幕关键词 | 启用状态 | 参数 |','| --- | --- | --- | --- | --- |',...rules.map(r=>`| ${cell(name(r))} | ${cell(state.actions[r.action]||r.action)} | ${cell(r.keywords.split('|').join('、'))} | ${r.enabled?'启用':'停用'} | ${r.action==='link:stop'?'立即':r.action.startsWith('link:')?(r.duration_ms??150)+' 毫秒':['heal','damage','health_cap'].includes(r.action)?r.value+' 颗心':r.action==='spawn'?'每次一件，{物品} 自动匹配':r.action==='rupees_add'?'{数量} 为增加的卢比数':r.action==='rupees_zero'?'卢比设为 0':'—'} |`),'','匹配说明：整条弹幕匹配，忽略空格、全角数字与末尾常见标点；{物品} 表示物品名称，{数量} 表示正整数卢比数。多条规则同时命中时跳过；连接预热期间跳过历史弹幕。血量、卢比修改遵守当前锁定状态；天气受地区和过渡影响。','','人物动作说明：移动方向相对镜头。侧跳、后空翻受装备和姿态影响；互动执行当前游戏提示。瞄准、投掷准备松开后可能射箭或投出武器。持续时间结束自动释放按键；停止动作释放虚拟输入，不影响实体手柄。',''];
   const url=URL.createObjectURL(new Blob(['\uFEFF'+lines.join('\n')],{type:'text/markdown;charset=utf-8'}));
   const a=document.createElement('a');a.href=url;a.download='TOTK-直播指令清单.md';document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
   error('已导出 '+rules.length+' 条指令'+(dirty?'（含未保存修改）':'')+'。');
   }
 function renderRules(){
  $('streamViewBody').innerHTML=`${hint(draft.length+' 条指令 · 开关控制是否响应')}${field('streamRuleSearch','搜索指令','','type="search" placeholder="搜索关键词或功能"')}<div id="streamRuleList" class="sd-rule-list"></div><div class="sd-actions">${button('addStreamRule','新增指令')}${button('addStreamMovement','添加人物控制')}${button('saveStreamList','保存清单',true)}</div><p id="streamDraftState" class="sd-note">${dirty?'清单有未保存的修改':'可修改关键词、启用状态与数值；每次只执行一条明确匹配的指令。'}</p>`;
  $('addStreamRule').onclick=()=>{if(draft.length>=64){error('最多 64 条规则');return;}editIndex=-1;editing={action:'spawn',keywords:'送{物品}',name:'赠送物品',enabled:false};go('edit');};
  $('addStreamMovement').onclick=()=>{const extra=(state.movementDefaults||[]).filter(r=>!draft.some(d=>d.action===r.action));if(draft.length+extra.length>64){error('最多 64 条规则');return;}draft.push(...copy(extra));dirty=true;group=null;renderRules();};

  $('saveStreamList').onclick=()=>saveList();
  const populate=()=>{
   const query=$('streamRuleSearch').value.trim().toLowerCase();let items=groups();
   if(group){items=items.filter(x=>x.key===group).flatMap(g=>g.indices.map(index=>({key:'rule:'+index,indices:[index],title:name(draft[index])})));}
   items=items.filter(g=>[g.title,...g.indices.map(i=>draft[i].keywords)].join(' ').toLowerCase().includes(query));
   $('streamRuleList').replaceChildren(...items.map(g=>{
    const row=document.createElement('section');row.className='sd-rule-row';
    const all=g.indices.every(i=>draft[i].enabled),some=g.indices.some(i=>draft[i].enabled);
    const first=draft[g.indices[0]],caption=g.key==='weather'?g.indices.map(i=>state.actions[draft[i].action].split('：').pop()).join(' / '):first.action==='spawn'?first.keywords.replaceAll('|',' / ')+' · 自动匹配最合适的物品':['heal','damage'].includes(first.action)?first.keywords.replaceAll('|',' / ')+' · 每次 '+first.value+' 颗心':g.indices.map(i=>draft[i].keywords.replaceAll('|',' / ')).join(' / ');
    row.innerHTML=`<div class="sd-rule-top"><strong>${esc(g.title)}${g.indices.length>1?' · '+g.indices.length+'条':''}</strong><label class="gc-switch"><input type="checkbox" aria-label="启用${esc(g.title)}" ${all?'checked':''}><span></span></label><button type="button" aria-label="编辑${esc(g.title)}">编辑</button></div><p class="sd-rule-caption">${esc(caption)}${some&&!all?' · 部分启用':''}</p>`;
    const checkbox=row.querySelector('input');checkbox.indeterminate=some&&!all;
    checkbox.onchange=()=>{g.indices.forEach(i=>draft[i].enabled=checkbox.checked);dirty=true;$('streamDraftState').textContent='清单有未保存的修改';};
    row.querySelector('button').onclick=()=>{if(g.indices.length>1){group=g.key;populate();}else{editIndex=g.indices[0];editing=copy(draft[editIndex]);go('edit');}};return row;
   }));
   if(!items.length)$('streamRuleList').innerHTML='<p class="sd-note">没有匹配的指令</p>';
   if(group){const back=document.createElement('button');back.type='button';back.textContent='← 全部指令';back.onclick=()=>{group=null;populate();};$('streamRuleList').prepend(back);}
  };
  $('streamRuleSearch').oninput=populate;populate();
 }
 async function saveList(nextView='rules',rules=draft){
  await mutate({action:'save',rules,cooldown:state.cooldown},()=>{draft=copy(state.rules);dirty=false;go(nextView);error('清单已保存，已立即应用。');});
 }
 function readEditing(){
  const words=[$('editTemplate').value,...$('editAliases').value.split(/\n|\|/)].map(x=>x.trim()).filter(Boolean);
  const action=$('editAction').value;
  return {name:$('editName').value,action,keywords:words.join('|'),enabled:$('editEnabled').checked,...(action.startsWith('link:')&&action!=='link:stop'?{duration_ms:Number($('editDuration').value)}:{}),...(['heal','damage','health_cap'].includes(action)?{value:Number($('editValue').value)}:{})};
 }
 function renderEditor(){
  const aliases=editing.keywords.split('|');
  $('streamViewBody').innerHTML=`${hint('把“说什么”和“执行什么”分开设置')}${field('editName','指令名称',editing.name||(editing.action==='spawn'?'赠送物品':name(editing)),'maxlength="40"')}${switcher('editEnabled','启用这条指令',editing.enabled)}${field('editTemplate','弹幕匹配模板',aliases.shift(),'maxlength="300"')}${hint('{物品} 为物品名称，{数量} 为卢比数量；其他指令直接填写关键词。')}<label class="sd-field">别名 / 其他写法<textarea id="editAliases" rows="2" maxlength="300" placeholder="每行一种写法"></textarea></label><label class="sd-field">执行效果<select id="editAction"></select></label>${field('editValue','心心数量',editing.value??1,'type="number" min="0.25" max="40" step="0.25"')}${field('editDuration','持续时间（毫秒）',editing.duration_ms??1000,'type="number" min="50" max="3000" step="50"')}<p id="editEffectHint" class="sd-note"></p>${field('editTest','输入弹幕试匹配','','placeholder="例如：送大师剑" maxlength="1000"')}${button('previewStreamRule','试匹配（不操作游戏）')}<div id="editMatch" class="sd-match" role="status"></div><div class="sd-actions">${button('cancelStreamRule','取消')}${button('saveStreamRule','保存指令',true)}</div>${hint('保存指令会同时保存清单中的其他未保存修改。')}${editIndex>=0?button('removeStreamRule','移除规则'):''}`;
  $('editAliases').value=aliases.join('\n');$('editAction').replaceChildren(...Object.entries(state.actions).map(([value,label])=>{const o=document.createElement('option');o.value=value;o.textContent=label;return o;}));$('editAction').value=editing.action;
  const effect=()=>{const action=$('editAction').value;$('editDuration').parentElement.hidden=!action.startsWith('link:')||action==='link:stop';$('editValue').parentElement.hidden=!['heal','damage','health_cap'].includes(action);$('editEffectHint').textContent=action.startsWith('link:')?'移动方向相对镜头。防御为 ZL，瞄准为 ZR，攻击为 Y；投掷准备为 R，松开可能投出武器。侧跳与后空翻需要持武器或盾；蹲下为切换。时长结束释放按键，停止动作不受冷却限制。':action==='spawn'?'优先同名物品，再匹配近似名称；没有相近结果时跳过。每条弹幕赠送一件。':action==='health_cap'?'锁定心心上限，仍然会扣血。':action==='rupees_add'?'每种写法需包含 {数量}，只接受正整数。':action.startsWith('weather:')?'天气效果受地区和场景过渡影响。':'';};
  $('editAction').onchange=effect;effect();
  const proposed=()=>{const rows=copy(draft);const row=readEditing();if(editIndex<0)rows.push(row);else rows[editIndex]=row;return rows;};
  $('previewStreamRule').onclick=()=>mutate({action:'preview',rules:proposed(),text:$('editTest').value},data=>{
   $('editMatch').replaceChildren();const label=document.createElement('strong');label.textContent=data.matched?(data.item?.name||data.label):data.reason;$('editMatch').append(label);
   if(data.matched){const p=document.createElement('p');p.className='sd-note';p.textContent=data.item?'将赠送一件 · 当前仅预览，不执行':data.command.argument?'数量：'+data.command.argument+' · 当前仅预览，不执行':'当前仅预览，不执行';$('editMatch').append(p);}
   host.querySelectorAll('button,input,select,textarea').forEach(el=>el.disabled=false);
  });
  $('cancelStreamRule').onclick=()=>go('rules');$('saveStreamRule').onclick=()=>saveList('rules',proposed());
  if($('removeStreamRule'))$('removeStreamRule').onclick=()=>{draft.splice(editIndex,1);dirty=true;go('rules');};
 }
 function renderDisplay(){
  const d=displayDraft;
  const segments=(key,label,values)=>`<div class="sd-field"><strong>${label}</strong><div class="sd-segments" role="group" aria-label="${label}">${values.map(([value,text])=>`<button type="button" data-display-key="${key}" data-display-value="${value}" aria-pressed="${d[key]===value}">${text}</button>`).join('')}</div></div>`;
  $('streamViewBody').innerHTML=`${switcher('displayEnabled','显示游戏内弹幕',d.enabled)}${segments('mode','显示方式',[['scroll','横向滚动'],['fade','淡出']])}${segments('position','显示位置',[['top','上方'],['middle','中间'],['bottom','下方']])}${field('displayFont','字号（12–48）',d.fontSize,'type="number" min="12" max="48"')}${switcher('displayNickname','显示昵称',d.nickname)}${field('displaySpeed','滚动速度（40–320 像素/秒）',d.speed,'type="number" min="40" max="320"')}${field('displayDuration','淡出停留时间（2–15 秒）',d.duration,'type="number" min="2" max="15"')}${hint('滚动模式使用速度；淡出模式使用停留时间。切换方式时保留各自设置。')}<div class="sd-field"><strong>位置与显示效果预览</strong><div id="displayPreview" class="sd-display-preview"><span></span></div></div>${hint('布局预览，不操作游戏。实际弹幕需要配套的弹幕版游戏。')}${button('saveStreamDisplay','保存显示设置',true)}`;
  const read=()=>{d.enabled=$('displayEnabled').checked;d.nickname=$('displayNickname').checked;d.fontSize=Number($('displayFont').value);d.speed=Number($('displaySpeed').value);d.duration=Number($('displayDuration').value);};
  const preview=()=>{const stage=$('displayPreview'),sample=stage.querySelector('span');stage.dataset.position=d.position;stage.dataset.mode=d.mode;sample.textContent=(d.nickname?'观众小林：':'')+'你好，海拉鲁！';sample.style.fontSize=Math.min(30,Math.max(9,d.fontSize*.65))+'px';sample.style.animationDuration=(d.mode==='scroll'?Math.max(2,550/d.speed):d.duration)+'s';};
  host.querySelectorAll('[data-display-key]').forEach(btn=>btn.onclick=()=>{read();d[btn.dataset.displayKey]=btn.dataset.displayValue;renderDisplay();});
  for(const id of ['displayEnabled','displayNickname','displayFont','displaySpeed','displayDuration'])$(id).oninput=()=>{read();preview();};
  $('saveStreamDisplay').onclick=()=>{read();mutate({action:'display',settings:d},()=>{render();error('显示设置已保存；配套游戏接收后生效。');});};preview();
 }
 function renderRecords(){
  $('streamViewBody').innerHTML=`${hint('最近 '+(state.events||[]).length+' 条弹幕及触发结果')}${field('recordSearch','搜索记录','','type="search" placeholder="搜索昵称、弹幕或结果"')}<ul id="streamAllRecords" class="sd-records"></ul>`;
  const fill=()=>{const q=$('recordSearch').value.trim().toLowerCase();$('streamAllRecords').innerHTML=eventsHTML((state.events||[]).filter(row=>[row.user,row.text,row.result].join(' ').toLowerCase().includes(q)));};$('recordSearch').oninput=fill;fill();
 }
 async function poll(){
  try{if(!mutating){const readGeneration=generation;const data=await api();if(!alive||readGeneration!==generation)return;const initial=!state;state=data;if(initial){draft=copy(data.rules);room=data.settings?.room||'';kind=data.settings?.kind||'live';render();}else {paint();if(view==='records'&&$('streamAllRecords')){const q=$('recordSearch').value.trim().toLowerCase();$('streamAllRecords').innerHTML=eventsHTML((state.events||[]).filter(row=>[row.user,row.text,row.result].join(' ').toLowerCase().includes(q)));}}}}
  catch(e){if(alive){if(!state)host.innerHTML='<p class="sd-message" role="status">'+esc(e.message)+'</p>';else error(e.message);}}
  finally{if(alive)timer=setTimeout(poll,1500);}
 }
 poll();return ()=>{alive=false;clearTimeout(timer);};
};
