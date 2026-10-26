(()=>{
 const opener=document.getElementById('amiiboMenu');if(!opener)return;
 let dispose=()=>{};
 const request=async(path,body)=>{const r=await fetch(path,{method:body?'POST':'GET',headers:body?{'Content-Type':'application/json'}:{},body:body?JSON.stringify(body):undefined,cache:'no-store'});const data=await r.json();if(!r.ok)throw new Error(data.error||'暂时无法连接游戏');return data;};
 opener.onclick=()=>{
  const panel=document.getElementById('right'),container=document.getElementById('rightContent');
  if(panel.dataset.navMode==='amiibo'&&!panel.classList.contains('hidden')){document.getElementById('hideRight').click();return;}
  dispose();window.openAmiiboDrawer();
  container.innerHTML='<section class="amiibo-drawer" aria-label="虚拟 amiibo"><header class="am-header"><h2>虚拟 amiibo</h2><button class="am-close" aria-label="关闭虚拟 amiibo">×</button></header><p class="am-intro">先在游戏选项中启用 amiibo，使用 amiibo 能力，将瞄点移到平地，再从这里扫描。</p><div class="am-field"><label for="amiiboSearch">搜索角色</label><input id="amiiboSearch" type="search" placeholder="林克、塞尔达…" autocomplete="off"></div><div class="am-field"><label for="amiiboModel">选择 amiibo</label><select id="amiiboModel" disabled><option>正在载入目录…</option></select><span id="amiiboCount" class="am-count"></span></div><figure class="am-preview"><img id="amiiboImage" width="240" height="180" alt="" hidden><figcaption id="amiiboImageCaption"></figcaption></figure><p class="am-status" role="status" aria-live="polite"><span class="am-dot" aria-hidden="true"></span><span id="amiiboConnection">正在连接游戏…</span></p><button id="amiiboScan" class="am-scan" disabled>扫描这个 amiibo</button><p id="amiiboMessage" class="am-message" role="status" aria-live="polite"></p><p class="am-note">将瞄点放在开阔平地，留出宝箱和素材掉落空间。奖励与每日次数由游戏决定。</p></section>';
  const content=container.firstElementChild,$=id=>content.querySelector('#'+id);
  let alive=true,timer,busy=false,state=null,items=[],generation=0,connectionError=false;
  const active=()=>alive&&content.isConnected&&panel.dataset.navMode==='amiibo'&&!panel.classList.contains('hidden');
  const observer=new MutationObserver(()=>{if(!active())dispose();});observer.observe(panel,{attributes:true,attributeFilter:['class','data-nav-mode']});observer.observe(container,{childList:true});
  dispose=()=>{alive=false;clearTimeout(timer);observer.disconnect();};
  const update=()=>{
   const chosen=items.find(x=>x.id===$('amiiboModel').value),picture=$('amiiboImage');
   picture.hidden=!chosen;content.querySelector('.am-preview').hidden=!chosen;if(chosen){const path='amiibo/'+chosen.id+'.webp';if(picture.getAttribute('src')!==path)picture.src=path;picture.alt=chosen.name+' amiibo 官方图片';$('amiiboImageCaption').textContent=chosen.name;}
   const ready=!!state?.available&&state.initialized;
   content.querySelector('.am-status').dataset.ready=String(ready);
   $('amiiboConnection').textContent=state?.queued?'已准备好，等待游戏扫描':ready?({0:'游戏已连接',1:'游戏正在等待 amiibo',2:'游戏已识别标签',3:'扫描已结束',4:'游戏正在读取标签',5:'读卡器暂不可用'}[state.deviceState]):'等待支持虚拟 amiibo 的原生游戏';
   $('amiiboScan').disabled=busy||!ready||state.queued||[2,4,5].includes(state.deviceState)||!$('amiiboModel').value;
   $('amiiboScan').textContent=busy?'正在发送…':'扫描这个 amiibo';
  };
  const filter=()=>{const selected=$('amiiboModel').value,q=$('amiiboSearch').value.trim().toLowerCase();const matches=items.filter(x=>(x.name+' '+x.nameEn).toLowerCase().includes(q));$('amiiboModel').replaceChildren(...matches.map(x=>{const o=document.createElement('option');o.value=x.id;o.textContent=x.name;return o;}));if(!matches.length){const empty=document.createElement('option');empty.value='';empty.textContent='没有匹配的 amiibo';$('amiiboModel').append(empty);}$('amiiboCount').textContent=q?`找到 ${matches.length} 个 amiibo`:`共 ${items.length} 个 amiibo`;if(matches.some(x=>x.id===selected))$('amiiboModel').value=selected;$('amiiboModel').disabled=!matches.length;update();};
  const poll=async()=>{if(!active())return;try{const g=generation;const data=await request('/api/amiibo');if(!active()||g!==generation||busy)return;state=data.state;if(connectionError){$('amiiboMessage').textContent='';connectionError=false;}update();}catch(e){if(active()&&!busy){state=null;connectionError=true;update();$('amiiboMessage').textContent=e.message;}}finally{if(active())timer=setTimeout(poll,2500);}};
  content.querySelector('.am-close').onclick=()=>document.getElementById('hideRight').click();
  $('amiiboSearch').oninput=filter;$('amiiboModel').onchange=update;
  $('amiiboScan').onclick=async()=>{if(busy||$('amiiboScan').disabled)return;busy=true;connectionError=false;generation++;update();$('amiiboMessage').textContent='';try{const data=await request('/api/amiibo',{id:$('amiiboModel').value});if(active()){state=data.state;$('amiiboMessage').textContent=data.message;}}catch(e){if(active())$('amiiboMessage').textContent=e.message;}finally{busy=false;if(active())update();}};
  request('/api/amiibo/catalog').then(data=>{if(active()){items=data.items;filter();}}).catch(e=>{if(active())$('amiiboMessage').textContent=e.message;});poll();
 };
})();
