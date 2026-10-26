/* Game-thread controls in the shared map drawer. Render only acknowledged state. */
(()=>{
 const opener=document.getElementById('gameControl');if(!opener)return;
 const art='branding/game-control/';
 const image=(name,extra='')=>`<img src="${art}${name}.svg" alt="" ${extra}>`;
 const weatherNames={clear:'晴天',cloudy:'阴天',rain:'小雨',heavy_rain:'大雨',thunder:'雷暴',thunder_rain:'雷雨',snow:'下雪'};
 const groupNames=[['Item_Fruit_','水果'],['Item_Mushroom_','蘑菇'],['Item_PlantGet_','植物'],['Item_Meat_','肉类'],['Item_FishGet_','鱼类'],['Item_Ore_','矿石'],['Item_Enemy_','怪物与特殊素材'],['Weapon_Sword_','单手武器'],['Weapon_Lsword_','双手武器'],['Weapon_Spear_','长柄武器'],['Weapon_Bow_','弓'],['Weapon_Shield_','盾']];
 let dispose=()=>{};
 opener.onclick=()=>{
  const panel=document.getElementById('right'),container=document.getElementById('rightContent');
  if(panel.dataset.navMode==='control'&&!panel.classList.contains('hidden')){document.getElementById('hideRight').click();return;}
  dispose();window.openGameControlDrawer();
  const range=(id,label,step,max,lock,description='')=>`<section class="gc-block"><div class="gc-heading"><label for="${id}">${label}</label><div><output id="${id}Value">— / —</output><span id="${lock}State" class="gc-state"></span></div></div>${description?`<p class="gc-description">${description}</p>`:''}<div class="gc-row"><div class="gc-range"><input id="${id}" type="range" min="${id==='controlHealthCap'?'.25':'0'}" max="${max}" step="${step}" disabled></div><button type="button" id="${lock}" class="gc-lock" aria-label="锁定${label}" aria-pressed="false" disabled>${image('lock-open')}</button></div></section>`;
  const number=(id,label,max,lock)=>`<section class="gc-block"><div class="gc-heading"><label for="${id}">${label}</label><span id="${lock}State" class="gc-state"></span></div><div class="gc-row"><input id="${id}" type="text" inputmode="numeric" pattern="[0-9]+" autocomplete="off" maxlength="${String(max).length}" data-maximum="${max}" placeholder="请输入数量" aria-label="${label}数量" disabled><button type="button" id="${lock}" class="gc-lock" aria-label="锁定${label}" aria-pressed="false" disabled>${image('lock-open')}</button></div></section>`;
  const separator=()=>`<div class="gc-divider" aria-hidden="true">${image('divider')}</div>`;
  container.innerHTML=`<section class="game-control-drawer" aria-label="游戏控制台"><header class="gc-header">${image('control-heading','class="gc-title"')}<button id="closeGameControl" aria-label="关闭游戏控制台">${image('close')}</button></header><div class="gc-body"><div id="controlHeartIndicator" class="gc-hearts" role="img" aria-label="血量未读取"></div>${range('controlHearts','心心','.25',40,'controlHealthLock')}${range('controlHealthCap','锁定心心上限','.25',40,'enableHealthCap','超过上限的心心会被扣掉，你不会自动补血，继续战损就好，不用仁慈一丝。')}${separator()}${range('controlStamina','体力','.1',3,'controlStaminaLock')}${number('controlRupees','卢比',99999999,'controlRupeesLock')}${number('controlArrows','箭矢',999,'controlArrowsLock')}${separator()}${['武器','弓','盾牌'].map((name,i)=>`<section class="gc-block gc-equipment"><div class="gc-heading"><span>${name}耐久</span><output id="durabilityValue${i}">等待读取</output></div><div class="gc-row"><div class="gc-segments" role="group" aria-label="${name}耐久模式">${[['normal','正常损耗'],['near_break','濒临损坏'],['infinite','永不损坏']].map(([mode,label])=>`<button data-target="${['weapon','bow','shield'][i]}" data-mode="${mode}" aria-pressed="false" disabled>${label}</button>`).join('')}</div><button class="gc-reset" data-reset="${i}" aria-label="初始化${name}耐久" title="初始化背包全部${name}耐久" disabled>${image('reset')}</button></div></section>`).join('')}${separator()}<section class="gc-block"><div class="gc-heading"><label for="controlItems99" title="素材、料理、左纳乌胶囊维持99；箭矢单独控制，关闭不还原数量">所有物品 99 不减</label><label class="gc-switch"><input id="controlItems99" type="checkbox" disabled><span></span></label></div></section>${separator()}<section class="gc-block"><div class="gc-heading"><label for="spawnSearch">向女神许愿</label><output id="spawnState" class="gc-spawn-state"></output></div><p class="gc-description">想要什么尽管向女神开口，反正她又不缺这点东西，千万别跟她客气。</p><input id="spawnSearch" type="search" placeholder="请输入物品名称" aria-label="搜索物品"><div class="gc-row gc-spawn"><div class="gc-item-picker"><select id="spawnItem" hidden aria-hidden="true" tabindex="-1" disabled></select><button id="spawnPicker" type="button" role="combobox" aria-label="选择物品" aria-haspopup="listbox" aria-expanded="false" aria-controls="spawnOptions" disabled><span id="spawnSelection">正在载入物品…</span></button><div id="spawnOptions" role="listbox" aria-label="物品列表" hidden></div></div><button id="spawnItemButton" class="gc-primary" disabled>快拿来吧你！</button></div></section>${separator()}<section class="gc-block"><div class="gc-heading"><span>气象控制台</span><output id="weatherState">等待读取</output></div><p class="gc-description">晴天、雨天还是雷暴？海拉鲁的天气由你决定，想怎么变就怎么变。</p><div class="gc-weather" role="group" aria-label="选择天气">${Object.entries(weatherNames).map(([value,label])=>`<button data-weather="${value}" aria-label="${label}" aria-pressed="false" disabled>${image('weather-'+value)}<span>${label}</span></button>`).join('')}</div><div class="gc-heading"><label for="controlWeatherLock">锁定天气</label><label class="gc-switch"><input id="controlWeatherLock" type="checkbox" disabled><span></span></label></div></section><button id="refreshControl" class="gc-refresh">刷新游戏数据</button><div class="gc-footer"><p id="controlMessage" role="status">正在读取游戏数值…</p><p id="controlPreferences"></p><p id="controlModVersion">游戏连接：等待读取</p></div></div></section>`;
  const content=container.querySelector('.game-control-drawer'),$=id=>content.querySelector('#'+id);
  let alive=true,busy=false,mutating=false,pendingCommand=null,state=null,catalog=null,maxStamina=null,selectedWeather='clear',poll,spawnChecks=0,editingRange=false;
  const active=()=>alive&&content.isConnected&&panel.dataset.navMode==='control'&&!panel.classList.contains('hidden');
  const observer=new MutationObserver(()=>{if(!active())dispose();});observer.observe(panel,{attributes:true,attributeFilter:['class','data-nav-mode']});observer.observe(container,{childList:true});
  dispose=()=>{alive=false;clearTimeout(poll);observer.disconnect();};
  $('closeGameControl').onclick=()=>document.getElementById('hideRight').click();
  function hearts(value,max){
   const indicator=$('controlHeartIndicator');
   if(!Number.isFinite(value)||!Number.isFinite(max)){indicator.setAttribute('aria-label','血量未读取');return;}
   const parts=['empty','quarter','half','three-quarter','full'];
   const count=Math.min(40,Math.ceil(max));
   while(indicator.children.length>count)indicator.lastElementChild.remove();
   for(let i=0;i<count;i++){let cell=indicator.children[i];if(!cell){cell=document.createElement('span');cell.className='gc-heart';const img=document.createElement('img');img.alt='';cell.append(img);indicator.append(cell);}const img=cell.firstElementChild,src=art+'heart-'+parts[Math.max(0,Math.min(4,Math.round((value-i)*4)))]+'.svg';if(img.getAttribute('src')!==src)img.src=src;}
   indicator.setAttribute('aria-label',`当前血量 ${value} / ${max} 颗心`);
  }
  const paintRange=input=>{const ratio=(Number(input.value)-Number(input.min))/(Number(input.max)-Number(input.min));input.parentElement.style.setProperty('--gc-fill',Math.max(0,Math.min(100,ratio*100))+'%');};
  function setRange(id,value,max){const el=$(id);if(document.activeElement!==el||!editingRange){el.value=value??el.min;paintRange(el);}$(id+'Value').textContent=value==null?'— / —':`${Number(value.toFixed(2))} / ${max??'—'}`;}
  function renderPreferences(prefs){if(!prefs)return;$('controlPreferences').textContent=prefs.error||((prefs.pending||[]).length?'设置已保存，等待游戏准备好后恢复。':'开关和上限自动保存；一次性操作不会重复执行。');}
  function enabled(){
   const available=state?.hearts!=null;
   for(const [id,key] of [['controlHearts','hearts'],['controlStamina','stamina'],['controlRupees','rupees'],['controlArrows','arrows']])$(id).disabled=mutating||state?.[key]==null;
   $('controlHealthCap').disabled=mutating||typeof state?.healthCapEnabled!=='boolean'||!available;
   for(const [id,key] of [['controlHealthLock','healthLocked'],['controlStaminaLock','staminaLocked'],['controlRupeesLock','rupeesLocked'],['controlArrowsLock','arrowsLocked'],['enableHealthCap','healthCapEnabled']])$(id).disabled=mutating||state?.capabilities?.playerValues===false||typeof state?.[key]!=='boolean';
   $('controlItems99').disabled=mutating||state?.capabilities?.itemQuantities99===false||typeof state?.items99Enabled!=='boolean';
   $('controlWeatherLock').disabled=mutating||typeof state?.weather?.locked!=='boolean'||(!state?.weather?.available&&!state?.weather?.locked);
   content.querySelectorAll('[data-weather]').forEach(b=>b.disabled=mutating||state?.weather?.available!==true);
   content.querySelectorAll('[data-mode],[data-reset]').forEach(b=>{const i=b.dataset.reset??['weapon','bow','shield'].indexOf(b.dataset.target);b.disabled=mutating||state?.durabilityScope!=='pouch'||!Number.isInteger(state?.durabilityCounts?.[i])||state.durabilityCounts[i]<0;});
   const canSpawn=state?.spawn?.available===true&&catalog&&state.spawn.catalogHash===catalog.catalogHash;
   $('spawnItem').disabled=mutating||!$('spawnItem').options.length;$('spawnItemButton').disabled=mutating||!canSpawn||!$('spawnItem').value;
   $('spawnPicker').disabled=$('spawnItem').disabled;if(mutating)closePicker();
   $('refreshControl').disabled=mutating;
  }
  function weatherButtons(){content.querySelectorAll('[data-weather]').forEach(b=>{const on=b.dataset.weather===selectedWeather;b.classList.toggle('selected',on);b.setAttribute('aria-pressed',String(on));b.querySelector('img').src=art+'weather-'+b.dataset.weather+(on&&b.dataset.weather==='clear'?'-active':'')+'.svg';});}
  function render(next){
   state=next;renderPreferences(next.preferences);
   $('controlHearts').max=next.maxHearts??40;
   $('controlHealthCap').max=next.maxHearts??40;
   setRange('controlHearts',next.hearts,next.maxHearts);setRange('controlHealthCap',next.healthCap,next.maxHearts);
   $('controlStamina').max=next.maxStamina??maxStamina??3;
   setRange('controlStamina',next.stamina,next.maxStamina??maxStamina);
   $('controlStaminaValue').title=next.maxStamina!=null?'游戏实时体力容量':maxStamina!=null?'体力容量来自最近同步存档；升级后请保存并刷新':'体力容量未读取；可调范围为0–3圈';
   hearts(next.hearts,next.maxHearts);
   for(const [id,key] of [['controlRupees','rupees'],['controlArrows','arrows']])if(document.activeElement!==$(id))$(id).value=next[key]??'';
   for(const [id,key] of [['controlHealthLock','healthLocked'],['controlStaminaLock','staminaLocked'],['controlRupeesLock','rupeesLocked'],['controlArrowsLock','arrowsLocked'],['enableHealthCap','healthCapEnabled']]){const b=$(id),on=next[key]===true;b.setAttribute('aria-pressed',String(on));b.querySelector('img').src=art+(on?'lock-closed':'lock-open')+'.svg';$(id+'State').textContent=typeof next[key]==='boolean'?(on?'已锁定':''):'未读取';}
   $('controlItems99').checked=next.items99Enabled===true;$('controlWeatherLock').checked=next.weather?.locked===true;
   if(next.weather?.lastRequested)selectedWeather=next.weather.lastRequested;weatherButtons();
   $('weatherState').textContent=next.weather?.available?(next.weather.lastRequested?'已请求'+weatherNames[next.weather.lastRequested]:'可以切换'):'暂不可用';
   $('weatherState').title='接口回报请求的天气，不代表已读取实际当前天气';
   $('spawnState').textContent=next.spawn?.created?'已创建':next.spawn?.available?'可以生成':'暂不可用';
   $('controlModVersion').textContent=(next.gameVersion?'游戏 '+next.gameVersion+' · ':'')+'运行时 '+(next.modVersion||'未提供')+(next.compatibility?.controlLayoutSupported===false?' · 此版本控制尚未适配':'');
   ['weapon','bow','shield'].forEach((target,i)=>{const count=next.durabilityCounts?.[i],mode=next.durabilityModes?.[i]===3?'infinite':'normal';$('durabilityValue'+i).textContent=Number.isInteger(count)&&count>=0?`背包 ${count} 件${mode==='infinite'?' · 已锁定':''}`:'背包未读取';content.querySelectorAll(`[data-target="${target}"]`).forEach(b=>{const on=b.dataset.mode===mode;b.classList.toggle('selected',on);b.setAttribute('aria-pressed',String(on));});});
   enabled();
  }
  async function capacity(){try{const r=await fetch('/api/progress',{cache:'no-store'});if(!r.ok)return;const data=await r.json();const v=data.playerStats?.maxStamina;maxStamina=Number.isFinite(v)&&v>=1&&v<=3?v:null;}catch{maxStamina=null;}}
  function schedule(){clearTimeout(poll);if(active())poll=setTimeout(()=>{if(!editingRange)request({action:'status'});else schedule();},500);}
  async function request(command){
   if(!active())return;
   if(busy){if(command.action!=='status'&&!mutating)pendingCommand=command;return;}
   busy=true;mutating=command.action!=='status';enabled();
   if(command.action!=='status')$('controlMessage').textContent='等待游戏确认…';
   try{
    if(command.action==='status')await capacity();
    const response=await fetch('/api/game-control',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(command)});
    const next=await response.json();if(!active())return;if(!response.ok)throw Error(next.error||'操作失败');render(next);
    if(command.action==='spawn_item')spawnChecks=next.spawn?.accepted?5:0;else if(spawnChecks)spawnChecks=next.spawn?.created?0:spawnChecks-1;
    $('controlMessage').textContent=command.action==='status'?'已读取游戏数据':command.action==='spawn_item'?'已提交生成请求，不会自动重试。':'游戏已确认修改';
   }catch(error){if(active()){$('controlMessage').textContent=error.message;if(state)render(state);}}
   finally{busy=false;mutating=false;if(active()){enabled();if(pendingCommand){const queued=pendingCommand;pendingCommand=null;request(queued);}else schedule();}}
  }
  function closePicker(){ $('spawnOptions').hidden=true;$('spawnPicker').setAttribute('aria-expanded','false'); }
  function itemContent(item){const row=document.createDocumentFragment(),img=document.createElement('img'),name=document.createElement('span');img.src='item-icons/'+encodeURIComponent(item.actor)+'.png';img.alt='';img.width=32;img.height=32;img.loading='lazy';name.textContent=item.name;row.append(img,name);return row;}
  function paintSelection(){const selected=catalog?.items.find(x=>x.actor===$('spawnItem').value);$('spawnSelection').replaceChildren(selected?itemContent(selected):document.createTextNode('没有匹配的物品'));for(const option of $('spawnOptions').querySelectorAll('[role=option]'))option.setAttribute('aria-selected',String(option.dataset.actor===$('spawnItem').value));}
  function chooseItem(actor){$('spawnItem').value=actor;paintSelection();closePicker();enabled();$('spawnPicker').focus();}
  $('spawnPicker').onclick=()=>{const open=$('spawnOptions').hidden;$('spawnOptions').hidden=!open;$('spawnPicker').setAttribute('aria-expanded',String(open));if(open){const option=$('spawnOptions').querySelector('[aria-selected=true]')||$('spawnOptions').querySelector('[role=option]');option?.focus();}};
  $('spawnPicker').onkeydown=e=>{if(['ArrowDown','ArrowUp'].includes(e.key)){e.preventDefault();$('spawnPicker').click();}};
  $('spawnOptions').onkeydown=e=>{const options=[...$('spawnOptions').querySelectorAll('[role=option]')],index=options.indexOf(document.activeElement);if(e.key==='Escape'){e.preventDefault();e.stopPropagation();closePicker();$('spawnPicker').focus();}else if(['ArrowDown','ArrowUp','Home','End'].includes(e.key)){e.preventDefault();options[e.key==='Home'?0:e.key==='End'?options.length-1:Math.max(0,Math.min(options.length-1,index+(e.key==='ArrowDown'?1:-1)))]?.focus();}else if(e.key==='Tab')closePicker();};
  content.addEventListener('focusout',e=>{if(!e.relatedTarget||!e.relatedTarget.closest('.gc-item-picker'))closePicker();});
  content.addEventListener('click',e=>{if(!e.target.closest('.gc-item-picker'))closePicker();});
  function fillItems(){
   const select=$('spawnItem'),previous=select.value,search=$('spawnSearch').value.trim().toLowerCase();select.replaceChildren();const groups=new Map(groupNames.map(([,label])=>[label,[]]));groups.set('其他',[]);
   for(const item of catalog?.items||[]){if(search&&!`${item.name} ${item.actor}`.toLowerCase().includes(search))continue;groups.get(groupNames.find(([prefix])=>item.actor.startsWith(prefix))?.[1]||'其他').push(item);}
   for(const[label,items]of groups){if(!items.length)continue;const group=document.createElement('optgroup');group.label=`—— ${label} ——`;for(const item of items){const option=document.createElement('option');option.value=item.actor;option.textContent=item.name;group.append(option);}select.append(group);}
   if([...select.options].some(o=>o.value===previous))select.value=previous;else if(!search)select.value='Item_Fruit_A';
   const list=$('spawnOptions');list.replaceChildren();for(const [label,items]of groups){if(!items.length)continue;const group=document.createElement('div');group.setAttribute('role','group');group.setAttribute('aria-label',label);const heading=document.createElement('div');heading.className='gc-item-group';heading.textContent=label;group.append(heading);for(const item of items){const option=document.createElement('button');option.type='button';option.setAttribute('role','option');option.tabIndex=-1;option.dataset.actor=item.actor;option.append(itemContent(item));option.onclick=()=>chooseItem(item.actor);group.append(option);}list.append(group);}paintSelection();closePicker();enabled();
  }
  $('spawnSearch').oninput=fillItems;$('spawnItemButton').onclick=()=>request({action:'spawn_item',actor:$('spawnItem').value});
  for(const[id,action]of [['controlHearts','set_health'],['controlStamina','set_stamina'],['controlHealthCap','set_health_cap']]){
   const input=$(id);input.onpointerdown=()=>editingRange=true;input.oninput=()=>{editingRange=true;paintRange(input);$(id+'Value').textContent=`${Number(input.value)} / ${id==='controlStamina'?(state?.maxStamina??maxStamina??'—'):(state?.maxHearts??'—')}`;if(id==='controlHearts')hearts(Number(input.value),state?.maxHearts);};
   input.onchange=()=>{editingRange=false;request({action,value:Number(input.value),...(action==='set_health_cap'?{enabled:true}:{})});};input.onblur=()=>{editingRange=false;};input.onpointerup=()=>editingRange=false;
  }
  for(const[id,action]of [['controlRupees','set_rupees'],['controlArrows','set_arrows']]){
   const input=$(id);input.onbeforeinput=e=>{if(e.data&&/[^0-9]/.test(e.data))e.preventDefault();};
   input.oninput=()=>{input.value=input.value.replace(/[^0-9]/g,'');input.setCustomValidity('');};
   const submit=()=>{if(!input.value)return;const value=Number(input.value);if(!/^\d+$/.test(input.value)||!Number.isInteger(value)||value>Number(input.dataset.maximum)){input.setCustomValidity('请输入范围内的非负整数');input.reportValidity();return;}input.setCustomValidity('');request({action,value});};
   input.onchange=submit;input.onkeydown=e=>{if(e.key==='Enter'){e.preventDefault();submit();}};
  }
  for(const[id,key,action]of [['controlHealthLock','healthLocked','set_health_lock'],['controlStaminaLock','staminaLocked','set_stamina_lock'],['controlRupeesLock','rupeesLocked','set_rupees_lock'],['controlArrowsLock','arrowsLocked','set_arrows_lock'],['enableHealthCap','healthCapEnabled','set_health_cap']])$(id).onclick=()=>request({action,enabled:!state?.[key],...(action==='set_health_cap'&&!state?.[key]?{value:Number($('controlHealthCap').value)}:{})});
  $('controlItems99').onchange=e=>{const enabled=e.target.checked;e.target.checked=!enabled;request({action:'set_items_99',enabled});};
  $('controlWeatherLock').onchange=e=>{const enabled=e.target.checked;e.target.checked=!enabled;request({action:'set_weather_lock',enabled,...(enabled?{weather:selectedWeather}:{})});};
  content.querySelectorAll('[data-weather]').forEach(b=>b.onclick=()=>request({action:'set_weather',weather:b.dataset.weather}));
  content.querySelectorAll('[data-mode]').forEach(b=>b.onclick=()=>request({action:'set_durability',target:b.dataset.target,mode:b.dataset.mode}));
  content.querySelectorAll('[data-reset]').forEach(b=>b.onclick=()=>request({action:'set_durability',target:['weapon','bow','shield'][Number(b.dataset.reset)],mode:'reset'}));
  $('refreshControl').onclick=()=>request({action:'status'});weatherButtons();
  fetch('/api/game-control/items').then(async r=>{if(!r.ok)throw Error('无法读取物品目录');return r.json();}).then(data=>{if(active()){catalog=data;fillItems();}}).catch(e=>{if(active())$('spawnState').textContent=e.message;});
  fetch('/api/game-control/preferences').then(async r=>{if(!r.ok)throw Error('无法读取已保存设置');return r.json();}).then(prefs=>{if(active())renderPreferences(prefs);}).catch(e=>{if(active())$('controlPreferences').textContent=e.message;}).finally(()=>{if(active())request({action:'status'});});
 };
})();
