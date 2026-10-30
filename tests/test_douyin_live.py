"""Share parsing and interaction regressions; no network or game writes."""
import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'map-client/backend'))
from douyin_live import Live, config, resolve_room


class Response:
    def __init__(self, url):
        self.status_code=302
        self.headers={'Location':url}
        self.closed=False
    def close(self):self.closed=True


class DouyinTests(unittest.TestCase):
    def test_share_text_redirect(self):
        response=Response('https://webcast.amemv.com/douyin/webcast/reflow/7700996771553135387?foo=1')
        result=resolve_room('3.14 复制此链接打开抖音，来看直播！ https://v.douyin.com/abcD/ 主播正在直播',get=lambda *a,**k:response)
        self.assertEqual(result,{'kind':'room','room':'7700996771553135387'})
        self.assertTrue(response.closed)

    def test_web_link_and_numeric(self):
        self.assertEqual(resolve_room('来看直播 https://live.douyin.com/12345'),{'room':'12345','kind':'live'})
        self.assertEqual(resolve_room('12345','room'),{'room':'12345','kind':'room'})

    def test_untrusted_redirect_and_invalid_share(self):
        for value in ['没有链接的口令','https://evil.test/123','https://live.douyin.com.evil.test/123','http://v.douyin.com/abc']:
            with self.subTest(value=value),self.assertRaises(ValueError):resolve_room(value)
        response=Response('http://127.0.0.1:7075/')
        with self.assertRaises(ValueError):resolve_room('https://v.douyin.com/abc',get=lambda *a,**k:response)
        self.assertTrue(response.closed)

    def test_redirect_loop(self):
        calls=[]
        def get(*a,**k):calls.append(1);return Response('https://v.douyin.com/loop')
        with self.assertRaises(ValueError):resolve_room('https://v.douyin.com/loop',get=get)
        self.assertEqual(len(calls),6)

    def test_validation(self):
        for change in [{'step':float('nan')},{'cooldown':0},{'heal':'减血'},{'step':.3},{'step':True}]:
            with self.subTest(change=change),self.assertRaises(ValueError):config({'room':'123',**change})

    def make_live(self, hearts=2, **status):
        now=[100.]
        writes=[]
        def execute(name,args):
            if name=='get_game_console_status':return {'hearts':hearts,**status}
            writes.append(args['value']);return {'hearts':args['value']}
        live=Live(execute=execute,clock=lambda:now[0]);live.settings=config({'room':'123'})
        return live,writes,now

    def test_duplicate_cooldown_and_warmup(self):
        live,writes,now=self.make_live()
        event={'type':'chat','id':'1','text':'减血','warming':True}
        live.receive(event);live.receive({**event,'warming':False})
        self.assertFalse(writes)
        live.receive({**event,'id':'2','warming':False});self.assertEqual(writes,[1])
        live.receive({**event,'id':'3','warming':False});self.assertEqual(writes,[1])
        now[0]+=3;live.receive({**event,'id':'4','warming':False});self.assertEqual(writes,[1,1])

    def test_ambiguous_locked_and_floor(self):
        live,writes,_=self.make_live(.25)
        live.receive({'type':'chat','id':'1','text':'加血减血'});self.assertFalse(writes)
        live.receive({'type':'chat','id':'2','text':'减血'});self.assertEqual(writes,[.25])
        live,writes,_=self.make_live(healthLocked=True)
        live.receive({'type':'chat','id':'3','text':'减血'});self.assertFalse(writes)

    def test_health_cap(self):
        live,writes,_=self.make_live(hearts=3,healthCapEnabled=True,healthCap=3)
        live.receive({'type':'chat','id':'1','text':'加血'});self.assertEqual(writes,[3])

    def test_no_retry_after_failure(self):
        live,_,_=self.make_live();calls=[]
        def failure(*args):calls.append(1);raise TimeoutError('timeout')
        live.execute=failure;live.receive({'type':'chat','id':'1','text':'减血'})
        self.assertEqual(calls,[1]);self.assertIn('timeout',live.events[0]['result'])

if __name__=='__main__':unittest.main()

class DouyinHTTPTests(unittest.TestCase):
    def setUp(self):
        from http.server import ThreadingHTTPServer
        from server import Handler
        import threading
        self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        self.thread=threading.Thread(target=self.server.serve_forever);self.thread.start()
        self.base=f'http://127.0.0.1:{self.server.server_port}'
    def tearDown(self):
        self.server.shutdown();self.thread.join();self.server.server_close()
    def post(self,value,origin=None):
        import json,urllib.request
        req=urllib.request.Request(self.base+'/api/douyin',data=json.dumps(value).encode(),headers={'Content-Type':'application/json','Origin':origin or self.base})
        return urllib.request.urlopen(req)
    def test_resolve_without_start_or_game(self):
        import json
        from unittest.mock import patch
        with patch('douyin_live.live.start') as start:
            with self.post({'action':'resolve','room':'分享 https://live.douyin.com/123'}) as response:
                self.assertEqual(json.load(response),{'room':'123','kind':'live'})
            start.assert_not_called()
    def test_foreign_origin_rejected(self):
        import urllib.error
        with self.assertRaises(urllib.error.HTTPError) as caught:
            self.post({'action':'start','room':'123'},'https://example.com')
        self.assertEqual(caught.exception.code,403)
    def test_invalid_share_does_not_start(self):
        import urllib.error
        from unittest.mock import patch
        with patch('douyin_live.subprocess.Popen') as spawn:
            with self.assertRaises(urllib.error.HTTPError) as caught:
                self.post({'action':'start','room':'复制口令但没有链接'})
            self.assertEqual(caught.exception.code,400);spawn.assert_not_called()
    def test_preview_and_save_routes_do_not_modify_game(self):
        import json
        from unittest.mock import patch,Mock
        from douyin_commands import defaults
        execute=Mock();isolated=Live(execute=execute)
        with patch('douyin_live.live',isolated):
            with self.post({'action':'preview','text':'送苹果','rules':defaults()}) as response:
                self.assertEqual(json.load(response)['item']['name'],'苹果')
            rules=defaults();rules[1]['keywords']='回血'
            with self.post({'action':'save','rules':rules,'cooldown':4}) as response:
                self.assertEqual(json.load(response)['rules'][1]['keywords'],'回血')
            self.assertEqual(isolated.cooldown,4)
        execute.assert_not_called()
    def test_display_and_commands_routes_are_independent(self):
        import json
        from unittest.mock import patch,Mock
        from danmaku import Danmaku,DEFAULTS
        display=Danmaku();display.send=Mock();isolated=Live(display=display)
        with patch('douyin_live.live',isolated):
            with self.post({'action':'display','settings':{**DEFAULTS,'enabled':True,'position':'middle','mode':'fade'}}) as response:
                self.assertTrue(json.load(response)['settings']['enabled'])
            with self.post({'action':'commands','commandsEnabled':False}) as response:
                self.assertFalse(json.load(response)['commandsEnabled'])
            self.assertTrue(display.settings['enabled']);self.assertFalse(isolated.commands_enabled)
            with self.post({'action':'commands','commandsEnabled':True}) as response:json.load(response)
            self.assertTrue(display.settings['enabled'])
