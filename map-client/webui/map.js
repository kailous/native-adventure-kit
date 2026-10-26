'use strict';
const $=id=>document.getElementById(id), esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let wakeLock=null;async function requestWakeLock(){try{wakeLock=await navigator.wakeLock.request('screen')}catch{}}requestWakeLock();document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='visible')requestWakeLock()});
let compendium,itemLocations=[],regions,archive,catalogs,assets,layer='s',selected=new Set(['鸟望台']),filter='all',states={},current=null,scale=1.4,tx=0,ty=0,adding=false,search='',personal=null;
let questData={quests:[],questCategories:{},questPoints:{}};let questListCategory=null;
let records;try{records=JSON.parse(localStorage.getItem('totk-records'))||{done:{},favorites:[],notes:{},custom:[],route:[]};}catch{records={done:{},favorites:[],notes:{},custom:[],route:[]};}
try{const old=localStorage.getItem('totk-guide-bookmarks-migrated')?[]:JSON.parse(localStorage.getItem('totk-guide-bookmarks')||'[]');records.favorites=[...new Set([...records.favorites,...old])];localStorage.setItem('totk-records',JSON.stringify(records));localStorage.setItem('totk-guide-bookmarks-migrated','1');}catch{}
const mobileView=()=>matchMedia('(max-width:700px)').matches;
function closeMobilePanels(){if(!mobileView())return;for(const id of ['left','right'])$(id).classList.add('hidden');$('sheetBackdrop').hidden=true;}
function openMobilePanel(id){if(!mobileView()){if(innerWidth<=1050)for(const name of ['left','right'])$(name).classList.toggle('hidden',name!==id);return;}for(const name of ['left','right'])$(name).classList.toggle('hidden',name!==id);$('sheetBackdrop').hidden=false;}
function updateFollowButtons(){for(const id of ['fit']){$(id).classList.toggle('active',followingPlayer);$(id).setAttribute('aria-pressed',String(followingPlayer));}const label=language==='en'?'Follow Link':'跟随林克';$('fit').title=label;$('fit').setAttribute('aria-label',label);}
function stopFollowing(){followingPlayer=false;updateFollowButtons();}
let followErrorTimer=null;
function clearFollowError(){clearTimeout(followErrorTimer);$('fit').classList.remove('follow-error');}
function flashFollowError(){
 clearFollowError();stopFollowing();$('fit').classList.add('follow-error');
 $('fit').title=language==='en'?'Game not connected':'游戏未连接，请启动游戏';
 followErrorTimer=setTimeout(()=>{clearFollowError();updateFollowButtons();},480);
}
function toggleLinkFollow(){
 closeMobilePanels();
 if(followingPlayer){clearFollowError();stopFollowing();return;}
 if(!playerPosition?.available||Date.now()-lastPositionAt>1500||!trackingTarget(playerPosition)){flashFollowError();syncPlayer();return;}
 clearFollowError();followingPlayer=true;updateFollowButtons();syncPlayer();
}
const saveRecords=()=>localStorage.setItem('totk-records',JSON.stringify(records));
let language=localStorage.getItem('totk-language')||'zh';if(language==='zh-CN')language='zh';
const en={'鸟望台':'Skyview Towers','神庙':'Shrines','树根':'Lightroots','呀哈哈':'Koroks','呀哈哈*2':'Koroks ×2','宝箱':'Chests','主剧情挑战':'Main quests','情节挑战':'Side adventures','神庙挑战':'Shrine quests','迷你挑战':'Side quests','位置':'Locations','收集':'Collectibles','装备':'Equipment','地点':'Places','怪物':'Enemies','井':'Wells','洞穴入口':'Cave entrances','地洞入口':'Chasms','个人标点':'My markers'};
const displayName=s=>String(s).replace(/呀哈哈(?:\*2|_2)/g,'克洛洛果实 ×2').replace(/呀哈哈/g,'克洛洛果实').replace(/树根/g,'破魔之根');
const tr=s=>language==='en'?(en[s]||s):displayName(s);
function translate(){document.documentElement.lang=language==='en'?'en':'zh-CN';document.querySelectorAll('[data-en]').forEach(e=>{e.dataset.zh??=e.textContent;e.textContent=language==='en'?e.dataset.en:e.dataset.zh;});$('language').value=language;$('search').placeholder=language==='en'?'Search':'搜索';}
function allPoints(){return [...archive.points,...records.custom,...(personal==='item'?itemLocations.filter(p=>String(p.id).startsWith('item-')):[])];}
const placeOnlyTypes=new Set(['村庄','驿站','大妖精之泉','女神雕像','古代研究所','神殿','矿场','烹饪点','左纳乌制造机','特殊NPC','杂货店','旅馆','集市','珠宝店','防具店','怪物营地','人马（莱尼尔）','独眼巨人','独眼巨人（西诺克斯）','岩石巨人','方块魔像','莫尔德拉吉克','巨霸伽马','古栗欧克','八爪怪','龙','武器','盾牌','弓与箭','宝箱']);
const tracksCompletion=p=>!placeOnlyTypes.has(p.type);
function completed(p){if(!tracksCompletion(p))return null;return Object.hasOwn(states,p.id)?states[p.id]:p.type==='防具'?null:records.done[p.id]??null;}
function categoryFor(type){return (catalogs[layer]||[]).flatMap(g=>g.landmarkCatalogs).find(c=>c.name===type);}
function icon(p,active=true){const c=categoryFor(p.type)||Object.values(catalogs).flat(1).flatMap(g=>g.landmarkCatalogs).find(c=>c.name===p.type);return assets[active?c?.iconSelectedUrl:c?.iconUrl]||(String(p.id).startsWith('local-')?'icons/game/通用地点.svg':'icons/game/通用任务.svg');}
function gameIcon(url,type){const name=decodeURIComponent(url.split('/').pop().replace(/\.svg$/, ''));return '<i class="game-icon" data-icon="'+esc(name)+'" data-category="'+esc(type||name)+'" style="--icon-url:url(\''+esc(encodeURI(url))+'\')" aria-hidden="true"></i>';}
function visiblePoints(){return allPoints().filter(p=>p.L===layer&&(personal==='item'?itemLocations.some(i=>String(i.id)===String(p.id)):personal==='favorites'?records.favorites.includes(p.id):personal==='custom'?String(p.id).startsWith('local-'):selected.has(p.type))&&(filter==='all'||tracksCompletion(p)&&(filter==='completed'?completed(p)===true:completed(p)!==true))&&(!search||[p.n,p.type,displayName(p.n),displayName(p.type),p.description].join(' ').toLowerCase().includes(search)));}
function renderCategories(){document.querySelectorAll('[data-filter]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.filter===filter)));$('selectAll').checked=archive.categories.every(c=>selected.has(c));$('selectAll').indeterminate=selected.size>0&&!$('selectAll').checked;const container=$('categories');container.replaceChildren();for(const group of catalogs[layer]){const cats=group.landmarkCatalogs.filter(c=>c.name);if(!cats.length)continue;const el=document.createElement('div');el.className='group';el.innerHTML='<h3>'+esc(tr(group.groupName))+'</h3><div class="grid"></div>';for(const c of cats){const button=document.createElement('button');button.setAttribute('aria-pressed',String(selected.has(c.name)&&!personal));button.title=tr(c.name);button.className='category'+(selected.has(c.name)&&!personal?' active':'');button.innerHTML=gameIcon(assets[selected.has(c.name)?c.iconSelectedUrl:c.iconUrl]||'icons/game/通用任务.svg',c.name)+'<span>'+esc(tr(c.name))+'</span> <small>'+(!placeOnlyTypes.has(c.name)?archive.points.filter(p=>p.L===layer&&p.type===c.name&&completed(p)===true).length+' / ':'')+archive.points.filter(p=>p.L===layer&&p.type===c.name).length+'</small>';button.onclick=()=>{personal=null;selected.has(c.name)?selected.delete(c.name):selected.add(c.name);render();};el.querySelector('.grid').append(button);}container.append(el);}translate();}
let tileFrame=null;
function scheduleHD(){if(tileFrame!==null)return;tileFrame=requestAnimationFrame(()=>{tileFrame=null;renderHD();});}
function renderHD(){const container=$('hdtiles');if(!container)return;const z=Math.min(7,Math.max(3,Math.ceil(3+Math.log2(scale*(window.devicePixelRatio||1))))),wanted=new Set();for(const level of z>4?[4,z]:[z]){const factor=2**(level-3),size=256/factor,count=(layer==='s'?9:10)*factor;const minX=Math.max(0,Math.floor(-tx/scale/size)-1),maxX=Math.min(count-1,Math.floor(($('map').clientWidth-tx)/scale/size)+1),minY=Math.max(0,Math.floor(-ty/scale/size)-1),maxY=Math.min(count-1,Math.floor(($('map').clientHeight-ty)/scale/size)+1);for(let x=minX;x<=maxX;x++)for(let y=minY;y<=maxY;y++){const key=`${layer}-${level}-${x}-${y}`;wanted.add(key);if(container.querySelector(`[data-tile="${key}"]`))continue;const image=document.createElement('img');image.dataset.tile=key;image.dataset.zoom=level;image.style.cssText=`position:absolute;left:${x*size}px;top:${y*size}px;width:${size}px;height:${size}px;opacity:0;z-index:${level}`;image.draggable=false;image.onload=()=>{image.style.opacity='1';};image.onerror=()=>image.remove();image.src=`/api/tiles/${layer}/${level}/${x}/${y}.png`;container.append(image);}}for(const image of [...container.children])if(!wanted.has(image.dataset.tile))image.remove();}
function transform(){drawPlayer();scheduleHD();document.querySelectorAll('.region').forEach(e=>{e.style.display=e.dataset.zooms.split(',').includes(String(Math.max(0,Math.min(7,Math.round(3+Math.log2(scale))))))?'':'none';e.style.transform=`translate(-50%,-50%) scale(${1/scale})`;}); $('world').style.transform=`translate(${tx}px,${ty}px) scale(${scale})`;document.querySelectorAll('.pin').forEach(p=>p.style.transform=`translate(-50%,-50%) scale(${1/scale})`);}
const pixel=p=>[(p.x+6258.031892109519)/42.68482820452413*8,(p.z+7050.840756853006)/42.680788981275015*8];
function updateMap(){const count=layer==='s'?9:10;const image=$('mapimage');image.style.display='none';let tiles=$('tiles');if(!tiles){tiles=document.createElement('div');tiles.id='tiles';$('world').prepend(tiles);}tiles.replaceChildren();tiles.style.width=count*256+'px';tiles.style.height=count*256+'px';for(let x=0;x<count;x++)for(let y=0;y<count;y++){const img=document.createElement('img');img.src=`tiles/${layer}/${x}_${y}.png`;img.style.cssText=`position:absolute;left:${x*256}px;top:${y*256}px;width:256px;height:256px;`;img.draggable=false;tiles.append(img);}const hd=document.createElement('div');hd.id='hdtiles';hd.style.cssText='position:absolute;inset:0;pointer-events:none;z-index:0';tiles.append(hd);for(const region of regions[layer]){if(!region.name)continue;const label=document.createElement('span');label.className='region';label.dataset.zooms=region.visibleMapZoom||'3';label.style.fontSize=(region.nameFontSize||14)+'px';label.textContent=region.name;label.style.left=region.y*8+'px';label.style.top=-region.x*8+'px';tiles.append(label);}$('route').setAttribute('width',count*256);$('route').setAttribute('height',count*256);}
function renderPins(){const pins=$('pins');pins.replaceChildren();const points=visiblePoints();for(const p of points){const b=document.createElement('button'),[x,y]=pixel(p);b.className='pin'+(completed(p)===true?' done':'')+(current?.id===p.id?' selected':'')+((p.type==='依盖队设计图'||(p.type==='设计图石板'&&p.n.includes('依盖')))?' yiga-schematic':'');b.style.left=x+'px';b.style.top=y+'px';b.dataset.id=p.id;b.title=tr(p.n);b.setAttribute('aria-label',tr(p.n));b.setAttribute('aria-pressed',String(current?.id===p.id));b.innerHTML=gameIcon(icon(p),p.type)+($('labels').checked?'<span>'+esc(tr(p.n))+'</span>':'');pins.append(b);}const all=allPoints().filter(p=>p.L===layer&&selected.has(p.type)&&tracksCompletion(p));const count=all.filter(p=>completed(p)===true).length;$('counts').hidden=!all.length;$('counts').textContent=(language==='en'?'Collected ':'收集情况 ')+count+' / '+all.length;$('visible').textContent=(language==='en'?'Visible points: ':'当前显示 ')+points.length+(language==='en'?'':' 个点位');const route=records.route.map(id=>allPoints().find(p=>p.id===id)).filter(p=>p&&p.L===layer).map(pixel);document.querySelector('#route polyline').setAttribute('points',route.map(p=>p.join(',')).join(' '));transform();}
function render(){renderCategories();renderPins();refreshGuideHome();}
const sidebarCategories=[['鸟望台','tower'],['神庙','shrine'],['树根','lightroot'],['呀哈哈','korok'],['主剧情挑战','main-quest'],['情节挑战','adventure'],['迷你挑战','side-quest']];
let activeGuideCategory=null;
const sidebarImage=(name,className='',alt='')=>'<span class="sidebar-art '+className+'"><img src="branding/map-ui/'+name+'.svg" alt="'+esc(alt)+'"></span>';
function refreshGuideHome(){
 if(!$('guideHome'))return;
 for(const b of document.querySelectorAll('.guide-category')){
  const name=b.dataset.category,isStory=name==='主剧情挑战';
  const points=archive.points.filter(p=>name==='呀哈哈'?['呀哈哈','呀哈哈*2'].includes(p.type):p.type===name);
  const summary=questData.questCategories[name];
  const done=summary?summary.completed:points.filter(p=>completed(p)===true).length,total=summary?summary.total:points.length,known=summary?summary.unknown<summary.total:points.some(p=>completed(p)!==null);
  b.querySelector('.guide-progress-text').textContent=(known?done:'—')+' / '+total;
  b.querySelector('.guide-category-title').textContent=isStory?(language==='en'?'Main quests':'主线剧情'):tr(name);
  const types=name==='呀哈哈'?['呀哈哈','呀哈哈*2']:[name];const active=!personal&&types.length===selected.size&&types.every(t=>selected.has(t));b.classList.toggle('active',active);b.querySelector('.guide-category-main').setAttribute('aria-pressed',String(active));
  b.querySelector('.guide-arrow img').src='branding/map-ui/arrow.svg';
  b.querySelector('.guide-complete').hidden=!total||!known||done!==total;
  b.querySelector('.guide-category-main').setAttribute('aria-label','在地图筛选'+tr(name));b.querySelector('.guide-progress').setAttribute('aria-label','查看'+tr(name)+'进度与攻略 · '+(known?done:'—')+' / '+total);
 }
}
function showHome(){
 $('right').dataset.navMode='guide';
 questListCategory=null;current=null;$('rightContent').innerHTML='<div class="guide-home" id="guideHome"><div class="guide-brand">'+'<span class="title-art title-guide"><img src="branding/titles/guide.svg" alt="塞尔达 图文攻略" width="1734" height="355"></span>'+'</div><nav class="guide-category-list" aria-label="按类别探索"></nav></div>';
 for(const [name,art] of sidebarCategories){
  const b=document.createElement('div');b.className='guide-category';b.dataset.category=name;
  b.innerHTML=sidebarImage('complete','guide-complete')+'<button class="guide-category-main"><span class="guide-icon-ring">'+gameIcon(name==='主剧情挑战'?'icons/game/主线剧情.svg':icon({type:name}),name==='主剧情挑战'?'主线剧情':name)+'</span><span class="guide-category-title"></span></button><button class="guide-progress"><span class="guide-progress-text"></span>'+sidebarImage('arrow','guide-arrow')+'</button>';
  b.querySelector('.guide-category-main').onclick=()=>{
   activeGuideCategory=name;personal=null;selected=new Set(name==='呀哈哈'?['呀哈哈','呀哈哈*2']:[name]);search='';$('search').value='';$('clearSearch').hidden=true;filter='all';
   document.querySelectorAll('[data-filter]').forEach(x=>x.classList.toggle('active',x.dataset.filter==='all'));
   const points=archive.points.filter(p=>selected.has(p.type));
   const target=name==='树根'?'d':name==='鸟望台'?'s':points.some(p=>p.L===layer)?layer:points[0]?.L;
   if(target&&target!==layer){layer=target;setLayerButtons();updateMap();}
   render();closeMobilePanels();
  };
  b.querySelector('.guide-progress').onclick=()=>{
   if(['主剧情挑战','情节挑战','迷你挑战'].includes(name)){showQuestList(name);return;}
   const points=archive.points.filter(p=>name==='呀哈哈'?['呀哈哈','呀哈哈*2'].includes(p.type):p.type===name);
   showResults(points,{title:tr(name),mode:'guide'});$('right').dataset.navMode='guide';
   
  };
  document.querySelector('.guide-category-list').append(b);
 }
 refreshGuideHome();
}

const questStatusLabel=s=>({completed:'已完成',in_progress:'进行中',not_started:'未开始',unknown:'未知'})[s];
async function showQuestList(category){
 $('right').dataset.navMode='guide';
 questListCategory=category;current=null;$('right').classList.remove('hidden');openMobilePanel('right');
 const rows=questData.quests.filter(q=>q.category===category),summary=questData.questCategories[category];
 $('rightContent').innerHTML='<div class="point-head"><h2>'+esc(category==='主剧情挑战'?'主线剧情挑战':category)+'</h2></div><div class="panel-meta"><span>最新存档进度</span><strong>'+(summary?summary.completed+' / '+summary.total:'—')+'</strong></div><button class="guide-entry" id="chapterList">查看离线攻略</button><div class="quest-list"></div>';
 
 $('chapterList').onclick=()=>showStoryList(category);
 let links={};try{links=(await fetch('quest-guide-links.json').then(r=>r.json())).chapters||{};}catch{}
 if(questListCategory!==category)return;
 if(!rows.length)$('rightContent').querySelector('.quest-list').innerHTML='<div class="empty-state"><strong>暂无任务进度</strong><p>同步存档后显示完成情况；仍可查看上方离线攻略。</p></div>';
 for(const q of rows){const row=document.createElement('div');row.className='quest-row';row.innerHTML='<strong>'+esc(q.name)+'</strong><span class="quest-status" data-status="'+q.status+'">'+questStatusLabel(q.status)+'</span>';
 const pointId=Object.keys(questData.questPoints).find(pid=>questData.questPoints[pid].some(item=>item.id===q.id)),point=archive.points.find(p=>String(p.id)===pointId);
 const title=row.querySelector('strong');
 const button=document.createElement('button');button.className='quest-guide-link';button.textContent=q.name;
 button.onclick=()=>{if(links[q.id])openStoryGuide(links[q.id],category);else if(point)openPoint(point,true);else showQuestGuideSearch(q,category);};title.replaceChildren(button);row.onclick=e=>{if(!e.target.closest('button'))button.click();};
 $('rightContent').querySelector('.quest-list').append(row);
 }
}

const storyDataPromise=fetch('main-story.json').then(r=>{if(!r.ok)throw Error('主线攻略读取失败');return r.json();});
async function showStoryList(category='主剧情挑战'){
 questListCategory=null;current=null;$('right').dataset.navMode='guide';$('right').classList.remove('hidden');openMobilePanel('right');
 $('rightContent').innerHTML='<div class="point-head"><h2>离线流程攻略</h2></div><div id="storyList"></div>';
 const container=$('storyList');try{const story=await storyDataPromise;if(!container.isConnected)return;
 if(category!=='主剧情挑战'){container.textContent='请从任务列表选择对应任务，查看关联点位攻略。';return;}
 for(const p of story.chapters){const b=document.createElement('button');b.className='result';b.textContent=p.n;b.onclick=()=>openStoryGuide(p.id,category);container.append(b);}
 }catch(e){if(container.isConnected)container.textContent=e.message;}
}
async function openStoryGuide(id,category='主剧情挑战'){
 questListCategory=null;current=null;$('right').dataset.navMode='guide';$('right').classList.remove('hidden');openMobilePanel('right');
 $('rightContent').innerHTML='<div class="point-head"><h2>攻略</h2></div><div id="storyBody">正在读取离线攻略…</div>';
 const body=$('storyBody');try{const story=await storyDataPromise;if(!body.isConnected)return;const p=story.chapters.find(p=>p.id===id);if(!p)throw Error('此攻略暂未收录');
 $('rightContent').querySelector('.point-head h2').textContent=p.n;
 body.innerHTML='<p class="muted">离线流程摘要 · 不是任务完整图文攻略</p><div class="actions"><button id="storyFavorite"></button></div><div class="description" id="storySummary"></div><p class="muted">'+esc(p.credit)+'</p><h3>我的备注</h3><textarea class="note" id="storyNote" aria-label="我的攻略备注" placeholder="备注仅保存在本机"></textarea>';
 const favorite=$('storyFavorite');const update=()=>{favorite.textContent=records.favorites.includes(id)?'已收藏':'收藏';favorite.dataset.saved=String(records.favorites.includes(id));favorite.setAttribute('aria-pressed',String(records.favorites.includes(id)));};update();favorite.onclick=()=>{records.favorites=records.favorites.includes(id)?records.favorites.filter(x=>x!==id):[...records.favorites,id];saveRecords();update();};
 $('storySummary').textContent=p.text;renderStructuredSummary($('storySummary'),p,p.text);$('storyNote').value=records.notes[id]||'';$('storyNote').oninput=()=>{records.notes[id]=$('storyNote').value;saveRecords();};
 }catch(e){if(body.isConnected)body.textContent=e.message;}
}
function showQuestGuideSearch(q,category){
 const points=archive.points.filter(p=>p.type===category&&[p.n,p.description].join(' ').includes(q.name));
 showResults(points);$('right').dataset.navMode='guide';
 if(!points.length)$('results').innerHTML='<div class="empty-state"><strong>攻略暂未收录</strong><p>此任务还没有关联的离线攻略。</p></div>';
}

function showItemLocations(id){
 const e=compendium.entries.find(e=>e.id===id);if(!e)return;
 itemLocations=[...archive.points.filter(p=>e.pointIds.includes(p.id)),...e.locations.map((l,i)=>({id:'item-'+id+'-'+i,n:e.name+' · 获取宝箱',type:'宝箱',x:l.x,z:l.z,L:l.L,description:'物品：'+e.name+'\n来源：TOTK-compendium 宝箱数据。坐标不代表背包持有状态。',media:[],metas:[]}))];
 if(!itemLocations.length)return;personal='item';selected=new Set(itemLocations.map(p=>p.type));layer=itemLocations[0].L;setLayerButtons();updateMap();render();showResults(itemLocations);const link=document.createElement('a');link.href='compendium.html';link.textContent='返回图鉴';$('rightContent').prepend(link);
 const visible=itemLocations.filter(p=>p.L===layer).map(pixel),xs=visible.map(p=>p[0]),ys=visible.map(p=>p[1]),minX=Math.min(...xs),maxX=Math.max(...xs),minY=Math.min(...ys),maxY=Math.max(...ys);scale=Math.min(2,Math.max(.3,Math.min(($('map').clientWidth-100)/Math.max(100,maxX-minX),($('map').clientHeight-100)/Math.max(100,maxY-minY))));tx=$('map').clientWidth/2-(minX+maxX)/2*scale;ty=$('map').clientHeight/2-(minY+maxY)/2*scale;transform();
}
function showResults(points,options={}){
 $('right').dataset.navMode=options.mode||'guide';questListCategory=null;current=null;$('right').classList.remove('hidden');openMobilePanel('right');
 $('rightContent').innerHTML='<div class="point-head"><h2>'+esc(options.title||'搜索结果')+'</h2></div><div class="panel-meta"><span>'+esc(options.subtitle||'选择点位查看攻略与地图位置')+'</span><strong>'+points.length+' 项</strong></div><div id="results" data-kind="'+esc(options.mode||personal||'search')+'"></div>';
 
 const container=$('results');let offset=0;const more=document.createElement('button');more.className='guide-entry load-more';
 const appendPage=()=>{more.remove();for(const p of points.slice(offset,offset+200)){const b=document.createElement('button');b.className='result';b.innerHTML=esc(tr(p.n))+'<small>'+esc(tr(p.type))+' · '+esc({s:'地表',k:'天空',d:'地底'}[p.L])+'</small>';b.onclick=()=>openPoint(p,true);container.append(b);}offset=Math.min(points.length,offset+200);if(offset<points.length){more.textContent='继续加载 · 还有 '+(points.length-offset)+' 项';more.onclick=appendPage;container.append(more);}};appendPage();
 if(!points.length)$('results').innerHTML='<div class="empty-state"><strong>'+esc(options.emptyTitle||'没有找到匹配点位')+'</strong><p>'+esc(options.emptyHint||'试试其他名称，或返回攻略首页按类别查找。')+'</p></div>';

}
function openPoint(p,locate=false){$('right').dataset.navMode='guide';questListCategory=null;if(mobileView()){$('search').blur();$('searchPanel').hidden=false;$('searchMenu').setAttribute('aria-expanded','false');}if(current?.id!==p.id)stopFollowing();openMobilePanel('right');current=p;layer=p.L;selected.add(p.type);personal=String(p.id).startsWith('local-')?'custom':personal==='item'&&itemLocations.some(i=>String(i.id)===String(p.id))?'item':null;setLayerButtons();$('right').classList.remove('hidden');$('rightContent').innerHTML='<div class="point-head"><h2>'+esc(tr(p.n))+'</h2></div><div class="coords">'+esc(tr(p.type))+' · '+esc({s:'地上',k:'天空',d:'地下'}[p.L])+' · X '+p.x+' / Z '+p.z+'</div><div id="pointState"></div><div class="actions"><button id="markDone"></button><button id="favorite"></button><button id="addRoute">加入路书</button></div><div class="description" id="description"></div><div id="media"></div><h3>我的备注</h3><textarea class="note" id="note" aria-label="我的点位备注" placeholder="备注仅保存在本机"></textarea>';const state=completed(p);$('markDone').hidden=!tracksCompletion(p);$('pointState').hidden=!tracksCompletion(p);$('pointState').textContent=questData.questPoints[p.id]?questData.questPoints[p.id].map(q=>q.name+'：'+questStatusLabel(q.status)).join('；'):p.type==='防具'?(state===null?'背包持有情况未知':'存档背包：'+(state?'已持有（完成）':'未持有')):Object.hasOwn(states,p.id)?'存档同步：'+(state?'已完成':'未完成'):state===null?'完成情况：存档未提供此点位标记':'本机标记：'+(state?'已完成':'未完成');$('markDone').textContent=state?'取消完成':'标记完成';$('markDone').disabled=p.type==='防具'||Object.hasOwn(states,p.id);$('markDone').dataset.complete=String(state===true);$('markDone').setAttribute('aria-pressed',String(state===true));if($('markDone').disabled)$('markDone').textContent=state?'已完成':'未完成';$('markDone').title=$('markDone').disabled?'此点位以最新存档为准':'';$('markDone').onclick=()=>{records.done[p.id]=!completed(p);saveRecords();openPoint(p);};$('favorite').textContent=records.favorites.includes(p.id)?'已收藏':'收藏';$('favorite').dataset.saved=String(records.favorites.includes(p.id));$('favorite').setAttribute('aria-pressed',String(records.favorites.includes(p.id)));$('favorite').onclick=()=>{records.favorites=records.favorites.includes(p.id)?records.favorites.filter(id=>id!==p.id):[...records.favorites,p.id];saveRecords();openPoint(p);};$('addRoute').textContent=records.route.includes(p.id)?'已加入路书':'加入路书';$('addRoute').disabled=records.route.includes(p.id);$('addRoute').onclick=()=>{if(!records.route.includes(p.id))records.route.push(p.id);saveRecords();renderPins();$('addRoute').textContent='已加入路书';$('addRoute').disabled=true;};const parsed=new DOMParser().parseFromString(p.description||'','text/html');parsed.querySelectorAll('script,style').forEach(e=>e.remove());parsed.querySelectorAll('br').forEach(e=>e.replaceWith('\n'));parsed.querySelectorAll('p,div,li').forEach(e=>e.append('\n'));$('description').textContent=formatGuideSummary(parsed.body.textContent)||'该点位原数据暂无文字攻略。';renderStructuredSummary($('description'),p,$('description').textContent);appendOfflineGuides($('media'),p);$('note').value=records.notes[p.id]||'';$('note').oninput=()=>{records.notes[p.id]=$('note').value;saveRecords();};if(String(p.id).startsWith('local-')){const remove=document.createElement('button');remove.textContent='删除本机标点';remove.onclick=()=>{records.custom=records.custom.filter(o=>o.id!==p.id);records.favorites=records.favorites.filter(id=>id!==p.id);records.route=records.route.filter(id=>id!==p.id);saveRecords();showHome();renderPins();};document.querySelector('.actions').append(remove);}updateMap();render();if(locate){const [x,y]=pixel(p);scale=Math.max(scale,1);tx=$('map').clientWidth/2-x*scale;ty=$('map').clientHeight/2-y*scale;transform();}if(innerWidth<700)$('left').classList.add('hidden');}
function setLayerButtons(){document.querySelectorAll('[data-layer]').forEach(b=>{b.classList.toggle('active',b.dataset.layer===layer);b.setAttribute('aria-pressed',String(b.dataset.layer===layer));});}
function changeLayer(L){layer=L;if(!archive.points.some(p=>p.L===L&&selected.has(p.type))){selected=new Set([L==='d'?'树根':L==='k'?'神庙':'鸟望台']);}personal=null;setLayerButtons();updateMap();render();}
function zoom(factor,x=$('map').clientWidth/2,y=$('map').clientHeight/2){const next=Math.min(8,Math.max(.2,scale*factor));tx=x-(x-tx)*next/scale;ty=y-(y-ty)*next/scale;scale=next;transform();}
function center(){const size=layer==='s'?2304:2560;scale=Math.min($('map').clientWidth,$('map').clientHeight)/size;tx=($('map').clientWidth-size*scale)/2;ty=($('map').clientHeight-size*scale)/2;transform();}
function initialView(){scale=1;const [x,y]=pixel({x:-260,z:-890});tx=$('map').clientWidth/2-x;ty=$('map').clientHeight/2-y;transform();}
const touches=new Map();let drag=null,pinch=null,gestureMoved=false;
function pinchStart(){const [a,b]=[...touches.values()];pinch={distance:Math.hypot(a.x-b.x,a.y-b.y),scale,tx,ty,x:(a.x+b.x)/2,y:(a.y+b.y)/2};}
$('viewport').onpointerdown=e=>{if(e.button!==0)return;touches.set(e.pointerId,{x:e.clientX,y:e.clientY});$('viewport').setPointerCapture(e.pointerId);if(touches.size===1){gestureMoved=false;drag={x:e.clientX,y:e.clientY,tx,ty,pin:e.target.closest('.pin')?.dataset.id};}else if(touches.size===2){gestureMoved=true;drag=null;stopFollowing();pinchStart();}};
$('viewport').onpointermove=e=>{if(!touches.has(e.pointerId))return;touches.set(e.pointerId,{x:e.clientX,y:e.clientY});if(touches.size>=2&&pinch){const [a,b]=[...touches.values()],rect=$('viewport').getBoundingClientRect();const next=Math.min(8,Math.max(.2,pinch.scale*Math.hypot(a.x-b.x,a.y-b.y)/Math.max(1,pinch.distance)));tx=(a.x+b.x)/2-rect.left-(pinch.x-rect.left-pinch.tx)*next/pinch.scale;ty=(a.y+b.y)/2-rect.top-(pinch.y-rect.top-pinch.ty)*next/pinch.scale;scale=next;transform();}else if(drag){if(Math.hypot(e.clientX-drag.x,e.clientY-drag.y)>6){gestureMoved=true;stopFollowing();}if(gestureMoved){tx=drag.tx+e.clientX-drag.x;ty=drag.ty+e.clientY-drag.y;transform();}}};
function endPointer(e,cancelled=false){const d=drag;touches.delete(e.pointerId);pinch=null;drag=null;if(touches.size){const p=[...touches.values()][0];drag={x:p.x,y:p.y,tx,ty};return;}if(cancelled||gestureMoved||!d)return;if(d.pin){const p=allPoints().find(p=>String(p.id)===d.pin);if(p)openPoint(p);}else if(adding){const rect=$('viewport').getBoundingClientRect();newMarker((e.clientX-rect.left-tx)/scale/8*42.68482820452413-6258.031892109519,(e.clientY-rect.top-ty)/scale/8*42.680788981275015-7050.840756853006);}}
$('viewport').onpointerup=e=>endPointer(e);$('viewport').onpointercancel=e=>endPointer(e,true);$('viewport').addEventListener('wheel',e=>{e.preventDefault();stopFollowing();const rect=$('map').getBoundingClientRect();zoom(e.deltaY<0?1.15:1/1.15,e.clientX-rect.left,e.clientY-rect.top);},{passive:false});
function modal(html){$('dialogContent').innerHTML=html;const heading=$('dialogContent').querySelector('h2');if(heading){heading.id='dialogTitle';$('dialog').setAttribute('aria-labelledby','dialogTitle');}else $('dialog').removeAttribute('aria-labelledby');$('dialog').showModal();}$('closeDialog').onclick=()=>$('dialog').close();
function newMarker(x,z){adding=false;$('add').classList.remove('active');modal('<h2>新增标点</h2><form id="markerForm"><label>标点名称<input name="name" placeholder="例如：下次探索的位置" required maxlength="150"></label><label>说明（选填）<input name="description" placeholder="记录路线或探索线索"></label><p>X '+Math.round(x)+' / Z '+Math.round(z)+'</p><button>保存到本机</button></form>');$('markerForm').onsubmit=e=>{e.preventDefault();const fd=new FormData(e.target);const p={id:'local-'+Date.now(),n:fd.get('name'),description:fd.get('description'),type:'个人标点',L:layer,x:Math.round(x),z:Math.round(z),metas:[],media:[]};records.custom.push(p);saveRecords();$('dialog').close();openPoint(p);};}
let syncing=false,lastVersion=null;async function sync(){if(syncing)return;syncing=true;try{const response=await fetch('/api/progress',{cache:'no-store'}),data=await response.json();if(!response.ok)throw Error(data.error||'存档不可用');states=data.states;questData={quests:data.quests||[],questCategories:data.questCategories||{},questPoints:data.questPoints||{}};$('saveLabel').textContent=language==='en'?'Save synced':'存档已同步';$('saveDate').textContent=new Date(data.mtime).toLocaleDateString(language==='en'?'en-GB':'zh-CN',{month:'long',day:'numeric'});$('saveTime').textContent=new Date(data.mtime).toLocaleTimeString('en-GB',{hour12:false});$('status').textContent=data.completedPoints+' / '+data.matchedPoints;$('status').title='已完成点位 / 可匹配点位 · '+data.path;$('status').setAttribute('aria-label','存档已完成 '+data.completedPoints+' 个点位，可匹配 '+data.matchedPoints+' 个点位');if(lastVersion!==data.version){lastVersion=data.version;render();if(questListCategory){const closed=$('right').classList.contains('hidden');showQuestList(questListCategory);if(closed){$('right').classList.add('hidden');if(mobileView())closeMobilePanels();}}if(current){const closed=$('right').classList.contains('hidden');openPoint(current);if(closed)closeMobilePanels();}}}catch(e){$('saveLabel').textContent='存档未同步';$('status').textContent='—';$('status').title=e.message;}finally{syncing=false;}}
$('sync').onclick=sync;$('language').onchange=e=>{language=e.target.value;localStorage.setItem('totk-language',language);translate();render();};$('labels').onchange=renderPins;$('selectAll').onchange=()=>{personal=null;selected=$('selectAll').checked?new Set(archive.categories):new Set();render();};$('submitSearch').onclick=()=>{if($('search').value.trim()){$('search').oninput({target:$('search'),type:'searchsubmit'});if(mobileView())$('search').blur();}else $('search').focus();};$('search').onkeydown=e=>{if(e.key==='Enter')$('submitSearch').click();if(e.key==='Escape'){$('clearSearch').click();$('search').blur();}};document.querySelectorAll('[data-layer]').forEach(b=>b.onclick=()=>changeLayer(b.dataset.layer));document.querySelectorAll('[data-filter]').forEach(b=>b.onclick=()=>{filter=b.dataset.filter;document.querySelectorAll('[data-filter]').forEach(x=>{x.classList.toggle('active',x===b);x.setAttribute('aria-pressed',String(x===b));});renderPins();});$('all').onclick=()=>{personal=null;selected=new Set(archive.categories);render();};$('none').onclick=()=>{selected.clear();personal=null;render();};$('plus').onclick=()=>zoom(1.3);$('minus').onclick=()=>zoom(1/1.3);$('fit').onclick=()=>toggleLinkFollow();
$('search').oninput=async e=>{search=e.target.value.trim().toLowerCase();$('clearSearch').hidden=!search;if(mobileView()&&e.type==='input'){renderPins();return;}if(search){const points=allPoints().filter(p=>[p.n,p.type,displayName(p.n),displayName(p.type),p.description].join(' ').toLowerCase().includes(search));showResults(points);const container=$('results'),query=search;let total=points.length;try{const story=await storyDataPromise;if(container.isConnected&&search===query)for(const p of story.chapters.filter(p=>[p.n,p.text].join(' ').toLowerCase().includes(query))){const b=document.createElement('button');b.className='result';b.textContent=p.n;b.onclick=()=>openStoryGuide(p.id);container.querySelector('.empty-state')?.remove();container.append(b);const count=container.parentElement.querySelector('.panel-meta strong');if(count)count.textContent=(++total)+' 项';}}catch{}}else showHome();renderPins();};$('clearSearch').onclick=()=>{$('search').value='';search='';$('clearSearch').hidden=true;showHome();renderPins();};$('favorites').onclick=async()=>{personal='favorites';render();showResults(allPoints().filter(p=>records.favorites.includes(p.id)),{title:'我的收藏',emptyTitle:'还没有收藏',emptyHint:'在点位或攻略中点击收藏，便可在这里快速找到。'});const container=$('results');let story;try{story=await storyDataPromise;}catch{return;}if(!container.isConnected)return;for(const p of story.chapters.filter(p=>records.favorites.includes(p.id))){const b=document.createElement('button');b.className='result';b.textContent=p.n;b.onclick=()=>openStoryGuide(p.id);container.querySelector('.empty-state')?.remove();container.append(b);const count=container.parentElement.querySelector('.panel-meta strong');if(count)count.textContent=container.querySelectorAll('.result').length+' 项';}};$('custom').onclick=()=>{personal='custom';render();showResults(records.custom,{title:'个人标点',emptyTitle:'还没有个人标点',emptyHint:'点击新增标点，再在地图上选择位置。'});};$('add').onclick=()=>{closeMobilePanels();adding=!adding;$('add').classList.toggle('active',adding);$('visible').textContent=adding?'请点击地图选择新标点位置':'';};$('path').onclick=()=>{showResults(records.route.map(id=>allPoints().find(p=>p.id===id)).filter(Boolean),{title:'我的路书',mode:'route',emptyTitle:'下一站，去哪里？',emptyHint:'在点位详情点击加入路书，按添加顺序规划探索路线。'});$('right').dataset.navMode='route';const b=document.createElement('button');b.textContent='清空路书';b.className='guide-entry';b.disabled=!records.route.length;b.onclick=()=>{records.route=[];saveRecords();renderPins();$('path').click();};$('rightContent').append(b);};
$('export').onclick=()=>{const url=URL.createObjectURL(new Blob([JSON.stringify(records,null,2)],{type:'application/json'})),a=document.createElement('a');a.href=url;a.download='totk-records.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};$('import').onclick=()=>$('importFile').click();$('importFile').onchange=async e=>{try{const value=JSON.parse(await e.target.files[0].text());if(!value||typeof value.done!=='object'||typeof value.notes!=='object'||!Array.isArray(value.favorites)||!Array.isArray(value.route)||!Array.isArray(value.custom)||value.custom.some(p=>!String(p.id).startsWith('local-')||typeof p.n!=='string'||!Number.isFinite(p.x)||!Number.isFinite(p.z)||!['s','k','d'].includes(p.L)))throw Error('记录文件格式不正确');records=value;saveRecords();render();showHome();}catch(err){modal('<p>'+esc(err.message)+'</p>');}e.target.value='';};
$('mcp').onclick=()=>{if(window.webkit?.messageHandlers?.desktop){window.webkit.messageHandlers.desktop.postMessage({action:'mcp'});return;}modal('<h2>MCP · 离线地图工具</h2><p>提供点位搜索、离线攻略、最新存档进度、附近点位查询。</p><p>桌面客户端已提供 MCP 连接配置，请在服务控制台中复制。也可以在项目目录独立运行 stdio 服务：</p><pre>python3 backend/mcp_server.py</pre><p>工具：search_points / get_point_guide / get_save_progress / nearby_points</p>');};
Promise.all(['gamersky-archive.json','catalogs.json','ui-assets.json','regions.json','compendium.json'].map(url=>fetch(url).then(r=>{if(!r.ok)throw Error(url+'读取失败');return r.json();}))).then(([a,c,u,r,book])=>{compendium=book;archive=a;catalogs=c;assets=u;regions=r;if(innerWidth<700){$('left').classList.add('hidden');$('right').classList.add('hidden');}translate();updateMap();render();showHome();if(innerWidth>700&&innerWidth<=1050)$('left').classList.add('hidden');initialView();const params=new URLSearchParams(location.search);if(params.has('point')){const p=allPoints().find(p=>String(p.id)===params.get('point'));if(p)openPoint(p,true);}if(params.has('guide'))openStoryGuide(params.get('guide'));if(params.has('category')&&!params.has('guide'))showQuestList(params.get('category'));if(params.has('item'))showItemLocations(params.get('item'));sync();setInterval(sync,1000);}).catch(e=>{$('status').textContent=e.message;});

let playerPosition=null,followingPlayer=false,positionBusy=false,lastPositionAt=0;
function trackingTarget(p){if(p?.ui?.available&&p.ui.mapOpen){const cursor=p.ui.mapCursor;return cursor&&p.ui.mapLayer?{x:cursor.x,z:cursor.z,layer:p.ui.mapLayer,mapCursor:true}:null;}return p;}
function drawPlayer(){let marker=$('playerPosition');if(!marker){marker=document.createElement('div');marker.id='playerPosition';marker.style.cssText='position:absolute;z-index:20;pointer-events:none;color:#ffed68;text-shadow:0 0 3px #000,0 0 6px #000;font-size:25px;';$('world').append(marker);}const target=trackingTarget(playerPosition);marker.hidden=!target||target.layer!==layer;if(!marker.hidden){const [x,y]=pixel(target);marker.style.left=x+'px';marker.style.top=y+'px';marker.classList.toggle('map-cursor',!!target.mapCursor);const mode=target.mapCursor?'cursor':playerPosition.headingAvailable?'facing':'position';if(marker.dataset.mode!==mode){marker.dataset.mode=mode;marker.replaceChildren();if(mode==='facing'){const image=document.createElement('img');image.src='branding/map-ui/player-facing.svg';image.alt='';image.width=24;image.height=27;marker.append(image);}else if(mode==='position')marker.textContent='●';}marker.classList.toggle('facing',mode==='facing');let view=marker.querySelector('.camera-view');const camera=playerPosition.camera;if(mode==='facing'&&camera?.available&&Number.isFinite(camera.heading)){if(!view){view=document.createElement('span');view.className='camera-view';marker.prepend(view);}view.style.transform=`translate(-50%,-100%) rotate(${camera.heading-playerPosition.heading}deg)`;view.title='镜头方向；扇形角度为示意';}else view?.remove();marker.style.transform=`translate(-50%,-50%) scale(${1/scale}) rotate(${!target.mapCursor&&playerPosition.headingAvailable?playerPosition.heading:0}deg)`;marker.title=target.mapCursor?'游戏地图光标':playerPosition.headingAvailable?'林克朝向 '+Math.round(playerPosition.heading)+'°':'林克位置，朝向不可用';}}
async function syncPlayer(){if(positionBusy)return;positionBusy=true;try{const r=await fetch('/api/position',{cache:'no-store'});if(!r.ok)throw Error('位置服务不可用');const p=await r.json();if(!p.available){const e=Error(p.error||'位置未连接');e.nativeGame=p.source==='native-game';if(p.modConnected&&p.telemetryStatus==='unsupported-version'){e.unsupportedVersion=true;e.gameVersion=p.gameVersion;}throw e;}playerPosition=p;lastPositionAt=Date.now();$('connectionBanner').classList.toggle('connected',!!p.modConnected);$('connectionLabel').textContent=p.modConnected?'连接成功':'内存备用采集';$('positionStatus').classList.toggle('connected',!!p.modConnected);$('positionStatus').textContent=`${p.modConnected?'':'内存 · '}${Math.trunc(p.x)} ${Math.trunc(p.north)} ${Math.trunc(p.height)}${p.headingAvailable?' · '+Math.round(p.heading)+'°':''}`;$('positionStatus').title=(p.modConnected?'实时读取游戏 Player Actor，无需坐标校准':'内存备用采集，需要本次游戏校准')+'；图层按高度估计'+(p.headingAvailable?'':'；角色朝向未验证');$('calibratePosition').hidden=p.modConnected||!['127.0.0.1','localhost'].includes(location.hostname);const target=trackingTarget(p);if(target?.mapCursor){$('positionStatus').textContent=`地图光标 · ${Math.trunc(target.x)} ${Math.trunc(-target.z)}`;}else if(p.ui?.mapOpen){$('positionStatus').textContent='地图光标坐标未获取';}if(followingPlayer&&archive&&target){if(layer!==target.layer)changeLayer(target.layer);const [x,y]=pixel(target);tx=$('map').clientWidth/2-x*scale;ty=$('map').clientHeight/2-y*scale;transform();}drawPlayer();}catch(e){playerPosition=null;if(followingPlayer)stopFollowing();$('connectionBanner').classList.toggle('connected',!!e.unsupportedVersion);$('connectionLabel').textContent=e.unsupportedVersion?'已连接游戏 '+e.gameVersion:'等待游戏启动';$('positionStatus').classList.remove('connected');$('positionStatus').textContent=e.unsupportedVersion?(language==='en'?'Position unavailable for this version':'此版本定位尚未适配'):(language==='en'?'Start the game to connect':'启动游戏后自动连接');$('positionStatus').title=e.message;$('calibratePosition').hidden=!!e.nativeGame||!!e.unsupportedVersion||!['127.0.0.1','localhost'].includes(location.hostname);drawPlayer();}finally{positionBusy=false;}}
$('filterMenu').onclick=()=>{openMobilePanel('left');$('left').classList.remove('hidden');if(!mobileView())transform();};
$('guideMenu').onclick=()=>{showHome();openMobilePanel('right');$('right').classList.remove('hidden');if(!mobileView())transform();};
$('searchMenu').onclick=()=>{openMobilePanel('left');$('left').classList.remove('hidden');$('left').scrollTop=0;$('searchPanel').hidden=false;$('search').focus();};
$('closeSearch').onclick=()=>{$('searchPanel').hidden=false;$('searchMenu').setAttribute('aria-expanded','false');$('search').blur();};
$('language').addEventListener('change',updateFollowButtons);
setInterval(()=>{if(archive)syncPlayer();},200);
let calibrationTimer=null;
$('calibratePosition').onclick=async()=>{
 clearTimeout(calibrationTimer);
 modal('<h2>实时位置校准</h2><p>只读扫描本机 Ryujinx 内存。先进入可操作的游戏场景并站着不动，按小地图显示顺序输入坐标。</p><form id="calibrationForm"><label>第一项（东西）<input name="x" type="number" step="1" required placeholder="例如 4618"></label><label>第二项（南北，保留负号）<input name="north" type="number" step="1" required placeholder="例如 -3711"></label><label>第三项（高度）<input name="height" type="number" step="1" required placeholder="例如 -506"></label><p id="calibrationState">正在检测 Ryujinx…</p><button id="scanPosition" type="button">扫描当前坐标</button> <button id="verifyPosition" type="button" disabled>验证移动后的坐标</button></form>');
 const statusText=$('calibrationState'),scan=$('scanPosition'),verify=$('verifyPosition');
 const update=s=>{scan.disabled=s.phase==='scanning';verify.disabled=s.phase!=='verify';statusText.textContent=(s.processes?.length?'检测到 Ryujinx 进程 '+s.processes.map(p=>p.pid).join('、')+'。':'未检测到 Ryujinx。')+(s.phase==='scanning'?'正在扫描，通常需要几十秒，请保持站立…':s.message||'请输入当前坐标开始扫描。');if(s.phase==='ready')syncPlayer();};
 const poll=async()=>{if(!$('dialog').open||!document.contains(statusText))return;try{const r=await fetch('/api/position-calibration',{cache:'no-store'}),s=await r.json();if(!r.ok)throw Error(s.error);update(s);if(s.phase==='scanning')calibrationTimer=setTimeout(poll,1500);}catch(e){statusText.textContent=e.message;}};
 const submit=async action=>{try{const f=new FormData($('calibrationForm'));if(!$('calibrationForm').reportValidity())return;scan.disabled=true;verify.disabled=true;const r=await fetch('/api/position-calibration',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action,x:Number(f.get('x')),north:Number(f.get('north')),height:Number(f.get('height'))})}),s=await r.json();if(!r.ok)throw Error(s.error);update(s);if(s.phase==='scanning')calibrationTimer=setTimeout(poll,1500);}catch(e){statusText.textContent=e.message;await poll();statusText.textContent=e.message;}};
 scan.onclick=()=>submit('scan');verify.onclick=()=>submit('verify');$('calibrationForm').onsubmit=e=>{e.preventDefault();};await poll();
};
if(!['127.0.0.1','localhost'].includes(location.hostname))$('calibratePosition').hidden=true;

for(const id of ['closeFilters','closeDetails','sheetBackdrop'])$(id).onclick=closeMobilePanels;
for(const [handle,panel] of [['expandFilters','left'],['expandDetails','right']]){
 $(handle).onclick=()=>$(panel).classList.toggle('expanded');let startY;
 $(handle).onpointerdown=e=>{startY=e.clientY;$(handle).setPointerCapture(e.pointerId);};
 $(handle).onpointerup=e=>{const delta=e.clientY-startY;if(delta>65)closeMobilePanels();else if(delta < -40)$(panel).classList.add('expanded');};
}
window.addEventListener('resize',()=>{if(!mobileView()){$('sheetBackdrop').hidden=true;if(innerWidth<=1050&&!$('left').classList.contains('hidden')&&!$('right').classList.contains('hidden'))$('left').classList.add('hidden');}});
document.addEventListener('keydown',e=>{if(e.key!=='Escape'||$('dialog').open)return;if(mobileView())closeMobilePanels();else $('hideRight').click();});

$('hideLeft').onclick=()=>{$('left').classList.add('hidden');transform();};
$('hideRight').onclick=()=>{$('right').classList.add('hidden');if(mobileView())closeMobilePanels();transform();};

const sidebarObserver=new ResizeObserver(entries=>{for(const e of entries)$('right').style.setProperty('--design-scale',e.contentRect.width/792);});sidebarObserver.observe($('right'));

// Navigation selected state describes the visible panel, independently of hover.
function updateNavigation(){
 const visible=!$('right').classList.contains('hidden');
 const title=document.querySelector('#right .desktop-panel-head>span');const mode=['control','amiibo'].includes($('right').dataset.navMode)?$('right').dataset.navMode:$('right').dataset.navMode==='route'?'route':'guide';
 if(mode==='control'||mode==='amiibo'){title.dataset.title=mode;title.className='';title.replaceChildren();}
 else if(title.dataset.title!==mode||!title.querySelector('img')){title.dataset.title=mode;title.className='title-art title-'+mode;title.innerHTML='<img src="branding/titles/'+mode+'.svg" alt="'+(mode==='route'?'塞尔达 路书':'塞尔达 图文攻略')+'" width="'+(mode==='route'?1288:1734)+'" height="355">';}
 for(const [id,mode] of [['navGuide','guide'],['navRoute','route'],['gameControl','control'],['amiiboMenu','amiibo']]){
  const active=visible&&$('right').dataset.navMode===mode;
  $(id).classList.toggle('active',active);$(id).setAttribute('aria-pressed',String(active));
 }
}
for(const [id,mode,action] of [['navGuide','guide','guideMenu'],['navRoute','route','path']]){
 $(id).onclick=()=>{
  if(!mobileView()&&!$('right').classList.contains('hidden')&&$('right').dataset.navMode===mode)$('hideRight').click();
  else $(action).click();
  updateNavigation();
 };
}
new MutationObserver(updateNavigation).observe($('right'),{attributes:true,attributeFilter:['class','data-nav-mode']});
updateNavigation();

// Keyboard activation does not generate the pointer sequence used by map pins.
$('pins').addEventListener('click',e=>{if(e.detail!==0)return;const pin=e.target.closest('.pin');const p=pin&&allPoints().find(p=>String(p.id)===pin.dataset.id);if(p)openPoint(p);});
$('showFilters').onclick=()=>{openMobilePanel('left');$('left').classList.remove('hidden');transform();$('search').focus({preventScroll:true});};

// Offline preview has its own SVG group; saved itinerary lines remain independent.

// Shared drawer opening clears point/quest state so save polling cannot replace controls.
window.openGameControlDrawer=()=>{questListCategory=null;current=null;$('right').dataset.navMode='control';$('right').classList.remove('hidden');openMobilePanel('right');$('right').scrollTop=0;updateNavigation();};

window.openAmiiboDrawer=()=>{questListCategory=null;current=null;$('right').dataset.navMode='amiibo';$('right').classList.remove('hidden');openMobilePanel('right');$('right').scrollTop=0;updateNavigation();};
