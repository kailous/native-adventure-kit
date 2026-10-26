"""Lossless, deterministic structure for point summaries and ordered guide content."""
import re
from html.parser import HTMLParser

SCHEMA_VERSION = 1
LABELS = {
    '名称':'name', '名字':'name', '位置':'location', '详细坐标':'location',
    '注意事项':'walkthrough', '攻略':'walkthrough', '获取方式':'walkthrough',
    '获取方法':'walkthrough', '开启方式':'walkthrough', '解锁方式':'walkthrough',
    '宝箱':'rewards', '宝箱掉落':'rewards', '奖励':'rewards', '任务奖励':'rewards',
    '可获得素材':'rewards', '可获得的材料':'rewards',
    '条件':'requirements', '前置任务':'requirements', '目标与前置':'requirements',
    '注意':'notes', '关键提示':'notes', '推进步骤':'walkthrough',
    '售卖材料':'inventory', '商品':'inventory',
}
FIELDS = tuple(dict.fromkeys(LABELS.values())) + ('description',)
PAGE_PREFIX = re.compile(r'^第\s*\d+\s*页[：:]\s*')
FOOTER = re.compile(r'更多相关内容请关注[：:]|责任编辑[：:]|本文是否解决了您的问题|文章内容导航|友情提示[：:]支持键盘')

class TextBlocks(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts=[]; self.skip=0
    def handle_starttag(self, tag, attrs):
        if tag in ('script','style','iframe'): self.skip+=1
        if self.skip:return
        if tag in ('p','div','br','li','h1','h2','h3'):self.parts.append('\n')
        if tag=='img':
            attrs=dict(attrs);url=attrs.get('data-src') or attrs.get('src')
            if url:self.parts.append({'image':url})
    def handle_endtag(self,tag):
        if tag in ('script','style','iframe'):self.skip=max(0,self.skip-1)
        if not self.skip and tag in ('p','div','li','h1','h2','h3'):self.parts.append('\n')
    def handle_data(self,text):
        if not self.skip:self.parts.append(text)

def normalize_url(url):return 'https:'+url if url.startswith('//') else url

def html_blocks(raw):
    parser=TextBlocks();parser.feed(raw or '')
    result=[];text=''
    for part in parser.parts:
        if isinstance(part,str):text+=part
        else:
            if text:result.append({'text':text});text=''
            result.append(part)
    if text:result.append({'text':text})
    return result

def ordered_blocks(raw_blocks,index):
    """Keep text/image order. Paragraph ordinals are not inferred gameplay steps."""
    output=[];buffer='';ended=False
    def flush():
        nonlocal buffer,ended
        for line in re.split(r'[\r\n]+',buffer):
            line=PAGE_PREFIX.sub('',line.strip())
            if not line or line=='展开':continue
            marker=FOOTER.search(line)
            if marker:
                line=line[:marker.start()].strip();ended=True
            if line:output.append({'type':'paragraph','text':line})
            if ended:break
        buffer=''
    for block in raw_blocks:
        if ended:break
        if 'text' in block:buffer+=block['text']
        elif block.get('image'):
            flush()
            if ended:break
            url=normalize_url(block['image']);entry=index.get(url,{})
            output.append({'type':'image','sourceURL':url,'path':entry.get('path'),
                           'available':bool(entry.get('path'))})
    flush()
    return [{**block,'order':i+1} for i,block in enumerate(output)]

def summarize(blocks):
    fields={field:[] for field in FIELDS};sections=[];active='description'
    for block in blocks:
        if block['type']!='paragraph':continue
        text=block['text'];label=None;value=text
        match=re.match(r'^(?:【([^】]+)】|([^：:]{1,20})[：:])\s*(.*)$',text)
        if match and (match[1] or match[2]) in LABELS:
            label=match[1] or match[2];active=LABELS[label];value=match[3]
        elif text in LABELS:
            label=text;active=LABELS[text];value=''
        if label or not sections:sections.append({'kind':active,'label':label,'paragraphs':[]})
        if value:
            fields[active].append(value);sections[-1]['paragraphs'].append(value)
    return fields,sections

def structure_text(raw,index):
    blocks=ordered_blocks(html_blocks(raw),index)
    fields,sections=summarize(blocks)
    return {'fields':fields,'sections':sections,'blocks':blocks,
            'text':'\n'.join(b['text'] for b in blocks if b['type']=='paragraph')}
