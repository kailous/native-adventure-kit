function formatGuideSummary(text){return String(text||'').replace(/注意事项[：:]([^]*?)\n+\s*宝箱[：:]([^\n]*)/g,(_,notes,chest)=>'攻略：'+notes.trim()+' '+chest.trim());}
// Rendering guard also handles stale article JSON cached by older clients.
function cleanOfflineBlocks(blocks){
 const text=blocks.map(b=>b.text||'').join('');
 const match=/(?:更多相关内容请关注[：:]|责任编辑[：:]|本文是否解决了您的问题|文章内容导航|友情提示[：:]支持键盘)/.exec(text);
 const cutoff=match?match.index:text.length+1;
 let offset=0;const result=[];
 for(const block of blocks){
  if(offset>cutoff||(offset===cutoff&&typeof block.text==='string'))break;
  if(typeof block.text==='string'){
   const value=block.text.slice(0,Math.max(0,cutoff-offset));offset+=block.text.length;
   if(value)result.push({...block,text:value.replace(/(^|[\r\n])([ \t]*)第\s*\d+\s*页[：:][ \t]*/g,'$1$2')});
  }else result.push(block);
 }
 return result;
}
const offlineIndexPromise=fetch('offline/index.json',{cache:'no-store'}).then(r=>r.ok?r.json():{}).catch(()=>({}));
function offlineImage(path){const image=document.createElement('img');image.src=path;image.loading='lazy';image.alt='攻略附图';image.style.cssText='display:block;width:100%;height:auto;margin:12px 0;border-radius:6px';return image;}
async function appendOfflineGuides(container,guide){
 const index=await offlineIndexPromise;
 const urls=new Set(guide.media||[]);
 for(const meta of guide.metas||[])for(const key of ['imageUrl','videoUrl','contentUrl'])if(meta[key])urls.add(meta[key]);
 for(let url of urls){
  if(url.startsWith('//'))url='https:'+url;
  const item=index[url];
  if(item?.kind==='image'){container.appendChild(offlineImage(item.path));continue;}
  if(item?.kind==='video'){const video=document.createElement('video');video.src=item.path;video.controls=true;video.preload='none';video.style.width='100%';container.appendChild(video);continue;}
  if(item?.kind==='article'){
   const details=document.createElement('details'),summary=document.createElement('summary');summary.textContent='展开完整图文攻略（离线）';details.appendChild(summary);container.appendChild(details);
   try{
    const structured=await structuredGuidesPromise;
    const aid=item.path.split('/').pop().replace(/\.json$/,'');
    const article=structured?.articles[aid];
    const fallback=article?null:await fetch(item.path+'?v=guide-clean-5',{cache:'no-store'}).then(r=>r.json());
    for(const block of article?article.blocks:cleanOfflineBlocks(fallback.content)){
     if(block.type==='image'){if(block.path)details.appendChild(offlineImage(block.path));continue;}
     if(block.text){const text=document.createElement(block.type==='paragraph'?'p':'span');text.className=block.type==='paragraph'?'guide-article-paragraph':'';text.textContent=block.text;details.appendChild(text);}
     else if(block.image){const raw=block.image.startsWith('//')?'https:'+block.image:block.image;const image=index[raw];if(image?.path)details.appendChild(offlineImage(image.path));}
    }
   }catch(e){details.appendChild(document.createTextNode('本地完整攻略读取失败'));}
   continue;
  }
  const note=document.createElement('div');note.style.color='#a8b9ad';note.textContent='此附件未能离线保存（源链接无效或未提供可下载媒体）';container.appendChild(note);
 }
}

// Shared by map details and the guide library. Source text remains as a fallback.
const structuredGuidesPromise=fetch('structured-guides.json?v=1',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('Structured guides unavailable');return r.json();}).catch(()=>null);
async function renderStructuredSummary(container,point,fallback){
 const key=String(point.id);container.dataset.guideId=key;
 container.textContent=fallback;
 const data=await structuredGuidesPromise;
 if(!container.isConnected||container.dataset.guideId!==key)return;
 const guide=data?.points[key]||data?.storyChapters[key];
 if(!guide)return;
 const fields=guide.summary.fields,root=document.createElement('dl');root.className='structured-summary';
 const groups=[['名称',fields.name],['位置',fields.location],['前置条件',fields.requirements],
  ['攻略',[...(fields.walkthrough||[]),...(fields.rewards||[])]],['提示',fields.notes],
  ['商品',fields.inventory],['说明',fields.description]];
 for(const [label,values] of groups){
  if(!values?.length)continue;
  const row=document.createElement('div'),term=document.createElement('dt'),body=document.createElement('dd');
  row.className='guide-field';term.textContent=label;body.textContent=values.join(label==='攻略'?' ':'\n');
  row.append(term,body);root.append(row);
 }
 if(root.childElementCount)container.replaceChildren(root);
}
