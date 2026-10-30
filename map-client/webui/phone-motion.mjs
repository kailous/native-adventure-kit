/* WebKit iOS forwards CoreMotion x/y/z as alpha/beta/gamma and gravity
   unchanged. Other browsers use beta/gamma/alpha and opposite gravity.
   Normalize the sensor frame before screen rotation; never swap aim axes.
   References and platform scope: docs/phone-motion.md. */
export function motionVector(event,angle=0,bias=[0,0,0],platform='standard'){
 const a=event.accelerationIncludingGravity,r=event.rotationRate;
 const ios=platform==='ios',rates=ios?[r?.alpha,r?.beta,r?.gamma]:[r?.beta,r?.gamma,r?.alpha];
 const values=[a?.x,a?.y,a?.z,...rates];
 if(values.some(v=>typeof v!=='number'||!Number.isFinite(v)))return null;
 const rad=Math.PI/180,c=Math.cos(angle*rad),s=Math.sin(angle*rad);
 const rotate=v=>[c*v[0]-s*v[1],s*v[0]+c*v[1],v[2]];
 const bodyGyro=rates.map(v=>v*rad),gyro=bodyGyro.map((v,i)=>v-bias[i]);
 const acc=[a.x,a.y,a.z].map(v=>(ios?1:-1)*v/9.80665);
 if(acc.some(v=>Math.abs(v)>8)||gyro.some(v=>Math.abs(v)>35))return null;
 return {acc:rotate(acc),gyro:rotate(gyro),bodyGyro};
}
export function sensorPlatform(nav){
 return /iPhone|iPad|iPod/.test(nav.userAgent||'')||(nav.platform==='MacIntel'&&nav.maxTouchPoints>1)?'ios':'standard';
}
export class PhoneSensor {
 constructor({request,now=()=>performance.now(),notify=()=>{},platform='standard'}){this.platform=platform;this.request=request;this.now=now;this.notify=notify;this.token=null;this.sequence=0;this.generation=0;this.busy=false;this.bias=[0,0,0];this.last=null;}
 async start(){
  const generation=++this.generation;this.notify('连接游戏…');
  const result=await this.request({action:'start'});
  if(generation!==this.generation){this.request({action:'stop',token:result.token,sequence:1},true).catch(()=>{});return;}
  this.token=result.token;this.sequence=0;this.calibrate();
 }
 calibrate(){this.last=null;this.bias=[0,0,0];this.calibration={started:this.now(),since:null,sum:[0,0,0],count:0};this.notify('请保持手机静止，正在校准…');}
 sample(event,angle){
  if(!this.token)return;const now=this.now(),value=motionVector(event,angle,this.bias,this.platform);if(!value)return;
  const cal=this.calibration;
  if(cal){
   if(now-cal.started>3000){this.stop('未能校准，请保持静止后重新启用');return;}
   const gravity=Math.hypot(...value.acc),rate=Math.hypot(...value.bodyGyro);
   if(rate>.08||gravity<.85||gravity>1.15){cal.since=null;cal.count=0;cal.sum=[0,0,0];return;}
   if(cal.since===null)cal.since=now;
   cal.count++;value.bodyGyro.forEach((v,i)=>cal.sum[i]+=v);
   if(now-cal.since<600||cal.count<12)return;
   this.bias=cal.sum.map(v=>v/cal.count);this.calibration=null;this.notify('校准完成，手机已连接');
  }
  this.last={...motionVector(event,angle,this.bias,this.platform),at:now};
 }
 async tick(){
  if(!this.token||this.busy)return;
  if(this.needsRecenter){await this.recenter();return;}
  if(this.calibration)return;
  if(!this.last||this.now()-this.last.at>200){this.stop('传感器断流，已停止');return;}
  const token=this.token,generation=this.generation,data=this.last;this.busy=true;
  try{
   const result=await this.request({action:'sample',token,sequence:++this.sequence,acc:data.acc,gyro:data.gyro,ageMs:Math.max(0,this.now()-data.at)});
   if(this.token===token&&generation===this.generation)this.notify(result.native.selected?'手机陀螺仪已连接':'手机已连接，鼠标模式优先');
  }catch(error){if(this.token===token)this.stop(error.message||'连接中断，已停止');}
  finally{this.busy=false;}
 }
 async recenter(){
  if(!this.token)return;
  // Wait for an outstanding sample so reset and sample sequences cannot race.
  if(this.busy){this.needsRecenter=true;this.last=null;return;}
  this.needsRecenter=false;this.busy=true;
  const token=this.token;
  try{await this.request({action:'calibrate',token,sequence:++this.sequence});if(this.token===token)this.calibrate();}
  catch(error){this.stop(error.message);}
  finally{this.busy=false;}
 }
 stop(message='已停止'){
  ++this.generation;const token=this.token;this.token=null;this.last=null;this.calibration=null;this.needsRecenter=false;
  if(token)this.request({action:'stop',token,sequence:++this.sequence},true).catch(()=>{});
  this.notify(message);
 }
}
if(typeof document!=='undefined'){
 const button=document.createElement('button');button.id='phoneMotionButton';button.textContent='陀螺仪';button.hidden=true;button.setAttribute('aria-haspopup','dialog');button.setAttribute('aria-pressed','false');document.body.append(button);
 const panel=document.createElement('dialog');panel.id='phoneMotionDialog';panel.setAttribute('aria-labelledby','phoneMotionTitle');
 panel.innerHTML='<div class="pm-head"><h2 id="phoneMotionTitle">手机陀螺仪</h2><button type="button" data-close aria-label="返回地图">×</button></div><p data-status role="status" aria-live="polite">正在检查连接…</p><section data-setup><p>首次使用：安装本机公开证书，信任后打开安全地图。</p><ol><li><a href="/phone-certificate.mobileconfig">iPhone：下载证书描述文件</a>；在设置 → 通用 → VPN 与设备管理中安装，再到通用 → 关于本机 → 证书信任设置，开启 TOTK Local Phone CA 完全信任。</li><li><a href="/phone-certificate.cer">Android：下载 CA 证书</a>；在系统安全设置中安装 CA 证书。</li><li>在电脑本机打开此面板，核对下面的 SHA-256 指纹一致。</li></ol><code data-fingerprint></code><p class="pm-note">此根证书会加入手机系统信任。仅信任你自己的电脑；不再使用时在系统设置中移除。本机私钥不会发送到手机。</p><div data-links></div></section><section data-controls hidden><p>将手机保持在舒适的握持姿势，点击启用并静置片刻。游戏须开启体感瞄准；鼠标模式优先使用鼠标。</p><div class="pm-actions"><button type="button" data-start>启用并授权</button><button type="button" data-calibrate disabled>重新校准</button><button type="button" data-stop disabled>停止</button></div><p class="pm-note">离开页面、锁屏或断流会自动停止；返回后需手动启用。</p></section>';
 document.body.append(panel);const find=s=>panel.querySelector(s);let pending=false,enabled=false;
 const request=async(data,closing=false)=>{
  if(closing&&navigator.sendBeacon){navigator.sendBeacon('/api/phone-motion',new Blob([JSON.stringify(data)],{type:'application/json'}));return {};}
  const abort=new AbortController(),timeout=setTimeout(()=>abort.abort(),data.action==='sample'?180:5000);
  try{const response=await fetch('/api/phone-motion',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data),cache:'no-store',signal:abort.signal,keepalive:closing});const value=await response.json();if(!response.ok)throw Error(value.error||'陀螺仪请求失败');return value;}
  finally{clearTimeout(timeout);}
 };
 const sensor=new PhoneSensor({request,platform:sensorPlatform(navigator),notify(message){find('[data-status]').textContent=message;const on=!!sensor.token;button.setAttribute('aria-pressed',String(on));button.textContent=on?'陀螺仪 · 已启用':'陀螺仪';find('[data-start]').disabled=on||pending||!enabled;find('[data-stop]').disabled=!on;find('[data-calibrate]').disabled=!on;}});
 async function refresh(){
  try{
   const response=await fetch('/api/phone-motion',{cache:'no-store'});if(!response.ok)return;const data=await response.json();button.hidden=false;
   const secure=data.secure&&window.isSecureContext;find('[data-setup]').hidden=secure;find('[data-controls]').hidden=!secure;
   enabled=secure&&typeof DeviceMotionEvent!=='undefined';find('[data-start]').disabled=!!sensor.token||pending||!enabled;
   if(!sensor.token)find('[data-status]').textContent=secure?(enabled?(data.native.available?'准备就绪':'请保存退出游戏并启动配套陀螺仪版游戏'):'此浏览器不支持手机运动传感器'):data.https.error||'请先安装证书并打开 HTTPS 地图';
   find('[data-fingerprint]').textContent=data.https.fingerprint||'本地 HTTPS 未就绪';
   const links=find('[data-links]');links.replaceChildren();
   for(const value of data.https.urls||[]){const url=new URL(value);if(url.protocol!=='https:'||!/^\d+\.\d+\.\d+\.\d+$/.test(url.hostname))continue;const a=document.createElement('a');a.href=url.href;a.textContent='打开安全地图 · '+url.host;a.className='pm-open';links.append(a);}
  }catch{find('[data-status]').textContent='地图服务暂时不可用';}
 }
 button.onclick=()=>{panel.showModal();refresh();};find('[data-close]').onclick=()=>panel.close();
 find('[data-start]').onclick=async()=>{
  if(pending)return;pending=true;find('[data-start]').disabled=true;
  try{
   // Safari requires this invocation directly in the click, before any fetch.
   const generation=sensor.generation;
   const permission=typeof DeviceMotionEvent.requestPermission==='function'?await DeviceMotionEvent.requestPermission():'granted';
   if(permission!=='granted')throw Error('未获得运动传感器权限，请在浏览器设置允许后重试');
   if(document.hidden||generation!==sensor.generation)throw Error("页面状态已改变，请重新启用");
   await sensor.start();
  }catch(error){sensor.stop(error.message||'启用失败');}
  finally{pending=false;find('[data-start]').disabled=!!sensor.token||!enabled;}
 };
 find('[data-stop]').onclick=()=>sensor.stop();find('[data-calibrate]').onclick=()=>sensor.recenter();
 const angle=()=>screen.orientation?.angle??window.orientation??0;
 window.addEventListener('devicemotion',event=>sensor.sample(event,angle()));
 let previousAngle=angle();setInterval(()=>{
  if(sensor.token&&angle()!==previousAngle)sensor.recenter();previousAngle=angle();
  if(sensor.calibration&&performance.now()-sensor.calibration.started>3000)sensor.stop('未收到有效传感器，请检查权限后重试');
  sensor.tick();
 },33);
 document.addEventListener('visibilitychange',()=>{if(document.hidden)sensor.stop('页面已进入后台，陀螺仪已停止');});window.addEventListener('pagehide',()=>sensor.stop());
 refresh();
}
