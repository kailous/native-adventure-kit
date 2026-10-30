/* Independent live interaction navigation and drawer lifecycle. */
(()=>{
 const opener=document.getElementById('streamMenu');if(!opener)return;
 let dispose=()=>{};
 opener.onclick=()=>{
  const panel=document.getElementById('right'),container=document.getElementById('rightContent');
  if(panel.dataset.navMode==='stream'&&!panel.classList.contains('hidden')){document.getElementById('hideRight').click();return;}
  dispose();window.openStreamDrawer();
  panel.dataset.streamView='main';container.scrollTop=0;
  container.innerHTML='<section class="stream-drawer game-control-drawer" aria-label="直播互动"><div id="douyinControl"></div></section>';
  const content=container.firstElementChild;
  const stopPolling=window.mountDouyinControl(content.querySelector('#douyinControl'),{
   close:()=>document.getElementById('hideRight').click(),
   view:value=>{panel.dataset.streamView=value;panel.scrollTop=0;container.scrollTop=0;requestAnimationFrame(()=>{if(panel.dataset.navMode==='stream'){panel.scrollTop=0;container.scrollTop=0;}});}
  });
  const active=()=>content.isConnected&&panel.dataset.navMode==='stream'&&!panel.classList.contains('hidden');
  const observer=new MutationObserver(()=>{if(!active())dispose();});
  observer.observe(panel,{attributes:true,attributeFilter:['class','data-nav-mode']});observer.observe(container,{childList:true});
  dispose=()=>{stopPolling();observer.disconnect();};
 };
})();
