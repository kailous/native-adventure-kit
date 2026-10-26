"""Registered cached guide images and expiring, read-only capability URLs."""
import hashlib,hmac,io,json,re,secrets,threading,time
from pathlib import Path
from urllib.parse import urlencode,parse_qs,urlsplit

class MediaError(Exception):
    def __init__(self,status,code):self.status,self.code=status,code

class GuideMedia:
    ttl=24*60*60
    def __init__(self,root,index,secret=None,reader=None):
        self.reader=reader;self.root=Path(root).resolve();self.secret=secret or secrets.token_bytes(32)
        self.entries={};self.urls={};self.cache={};self.lock=threading.Lock();self.slots=threading.BoundedSemaphore(8)
        for url,entry in index.items():
            if entry.get('kind')!='image':continue
            mid='media_'+hashlib.sha256(url.encode()).hexdigest()[:32]
            self.entries[mid]=(url,entry.get('path'));self.urls[url]=mid
    def sign(self,mid,expires):return hmac.new(self.secret,f'{mid}:{expires}'.encode(),hashlib.sha256).hexdigest()
    def link(self,mid,base=None):
        expires=int(time.time())+self.ttl
        route=f'/api/media/{mid}?'+urlencode({'expires':expires,'sig':self.sign(mid,expires)})
        return (base.rstrip('/')+route if base else None),route,expires
    def authorize(self,mid,query):
        if mid not in self.entries:raise MediaError(404,'media_not_found')
        q=parse_qs(query,keep_blank_values=True)
        try:
            if set(q)!={'expires','sig'} or any(len(v)!=1 for v in q.values()):raise ValueError()
            expires=int(q['expires'][0]);sig=q['sig'][0]
            if not int(time.time())<expires<=int(time.time())+self.ttl+60 or not hmac.compare_digest(sig,self.sign(mid,expires)):raise ValueError()
        except (ValueError,KeyError):raise MediaError(403,'media_link_expired_or_invalid')
        return expires
    def read(self,mid):
        if mid not in self.entries:raise MediaError(404,'media_not_found')
        if not self.slots.acquire(timeout=3):raise MediaError(503,'media_busy')
        try:
            try:from PIL import Image
            except ImportError:raise MediaError(503,'media_decoder_unavailable')
            raw=self.entries[mid][1]
            if not isinstance(raw,str):raise MediaError(404,'media_cache_missing')
            if self.reader is not None:
                if not raw.startswith('offline/') or '..' in Path(raw).parts:raise MediaError(404,'media_not_found')
                try:data=self.reader(raw)
                except (OSError,ValueError):raise MediaError(404,'media_cache_missing')
                if data is None:raise MediaError(404,'media_cache_missing')
                if not 0<len(data)<=16*1024*1024:raise MediaError(422,'media_invalid_size')
                signature=hashlib.sha256(data).hexdigest()
            else:
                path=(self.root/raw).resolve()
                if not path.is_relative_to(self.root/'offline'):raise MediaError(404,'media_not_found')
                try:
                    before=path.stat()
                    if not 0<before.st_size<=16*1024*1024:raise MediaError(422,'media_invalid_size')
                    data=path.read_bytes();after=path.stat()
                except OSError:raise MediaError(404,'media_cache_missing')
                signature=(after.st_mtime_ns,after.st_ctime_ns,after.st_size)
                if (before.st_mtime_ns,before.st_ctime_ns,before.st_size)!=signature:raise MediaError(503,'media_cache_changing')
            with self.lock:cached=self.cache.get(mid)
            if cached and cached[0]==signature:return data,cached[1]
            try:
                with Image.open(io.BytesIO(data)) as image:
                    mime={'JPEG':'image/jpeg','PNG':'image/png','WEBP':'image/webp','GIF':'image/gif'}.get(image.format)
                    if not mime or image.width*image.height>40_000_000:raise ValueError()
                    image.verify()
                with Image.open(io.BytesIO(data)) as image:image.load();width,height=image.size
            except Exception:raise MediaError(422,'media_cache_corrupt')
            meta={'mimeType':mime,'width':width,'height':height,'bytes':len(data),'etag':hashlib.sha256(data).hexdigest()}
            with self.lock:self.cache[mid]=(signature,meta)
            return data,meta
        finally:self.slots.release()
    def describe(self,url,base=None):
        mid=self.urls.get(url)
        if not mid:return {'id':None,'type':'image','url':None,'sourceUrl':url,'available':False,'error':'media_not_registered','role':'unknown'}
        result={'id':mid,'type':'image','url':None,'sourceUrl':url,'available':False,'role':'unknown','publicAvailable':False}
        try:
            _,meta=self.read(mid);public,local,expires=self.link(mid,base)
            result['fallbackTool']={'name':'get_guide_image','arguments':{'mediaId':mid}}
            result.update(meta,available=True,url=public,localUrl=local,expiresAt=expires,publicAvailable=bool(public),delivery='signed-cache' if public else 'local-only')
        except MediaError as error:result['error']=error.code
        return result


def adapt_guide(result,store,base):
    point=result.get('structured') or {};media={};blocks=[];steps=[]
    articles=[a for a in result.get('articles',{}).values() if a]
    sources=[(a.get('id'),a.get('blocks',[])) for a in articles] or [(None,point.get('summary',{}).get('blocks',[]))]
    def role(text):
        if '宝箱' in text:return 'treasure'
        if '位置如下图' in text:return 'location'
        return 'unknown'
    for article_id,original in sources:
        pending=[];current=None
        for block in original:
            item={'order':len(blocks)+1,'sourceOrder':block.get('order'),'articleId':article_id,'type':block['type']}
            if block['type']=='paragraph':
                item['text']=block['text'];pending.append(block['text']);current=None
            elif block['type']=='image':
                url=block['sourceURL'];entry=store.describe(url,base)
                mid=entry['id'];item['mediaId']=mid
                if pending or current is None:
                    current={'order':len(steps)+1,'instruction':'\n'.join(pending),'mediaIds':[],'articleId':article_id}
                    steps.append(current);pending=[]
                if mid:
                    entry['alt']=current['instruction'] or point.get('name','攻略截图')
                    entry['role']=role(current['instruction']);media.setdefault(mid,entry);current['mediaIds'].append(mid)
                else:item['error']=entry['error']
            blocks.append(item)
        if pending:steps.append({'order':len(steps)+1,'instruction':'\n'.join(pending),'mediaIds':[],'articleId':article_id})
    # Standalone point images keep their identity, but no invented paragraph association.
    for attachment in result.get('attachments',[]):
        if attachment.get('kind')=='image':
            entry=store.describe(attachment.get('sourceUrl',''),base)
            if entry['id']:entry['alt']=point.get('name','攻略图片');media.setdefault(entry['id'],entry)
    fields=point.get('summary',{}).get('fields',{})
    result.update(name=result.get('n'),guide={'title':'\n'.join(fields.get('name',[])) or result.get('n'),'blocks':blocks,'steps':steps},media=list(media.values()),
                  mediaDelivery={'publicBaseAvailable':bool(base),'expiresInSeconds':store.ttl,'browserWarningPossible':bool(base and '.ngrok-free.' in base),'fallbackTool':'get_guide_image','guidance':'按 guide.blocks 原始顺序展示文字和 mediaId 对应图片。优先使用本工具返回的原始攻略图片 URL，不要关键词搜图或生成替代截图。链接被 ngrok 警告页拦截时调用 get_guide_image 获取同一张缓存原图；不要搜图替代。链接过期后重新调用 get_point_guide。HTTP 可达不保证 ChatGPT 渲染成功。'})
    return result
