"""Isolated Douyin receiver. stdout is a bounded JSONL protocol to the map service.

Third-party receiver and signatures are shipped with their AGPL-3.0 source/license.
This process never imports game control or executes user commands.
"""
import json
import os
from pathlib import Path
import sys
import time


def main():
    base = (Path(sys._MEIPASS) / 'douyin' if getattr(sys, 'frozen', False)
            else Path(__file__).resolve().parents[1] / 'douyin')
    sys.path.insert(0, str(base))
    # Upstream reads its signature scripts relative to cwd; isolate from the HTTP process.
    os.chdir(base / 'DouyinLiveWebFetcher')
    from danmaku_hook import HookedFetcher
    from protobuf.douyin import ChatMessage

    def emit(value):
        print(json.dumps(value, ensure_ascii=False), flush=True)

    def connection_error(exc):
        name=type(exc).__name__
        if name in ('LibNotFoundError','LibNotLoadedError','FileNotFoundError'):
            message='直播签名引擎资源缺失，请更新地图工具'
        else:
            status=getattr(exc,'status_code',None)
            message=f'直播连接失败（{name}）'+(f'，HTTP {status}' if type(status) is int else '')
        emit({'type':'connection','state':'error','error':message})

    class Receiver(HookedFetcher):
        def _wsOnError(self, ws, error):
            connection_error(error)

        def _wsOnClose(self, ws, *unused):
            emit({'type':'connection','state':'reconnecting'})

        def _wsOnOpen(self, ws):
            super()._wsOnOpen(ws)
            emit({'type': 'connection', 'state': 'warming'})

        def _parseChatMsg(self, payload):
            m = ChatMessage().parse(payload)
            emit({'type': 'chat', 'id': str(m.common.msg_id),
                  'user': m.user.nick_name[:100], 'text': m.content[:1000],
                  'warming': time.time() < self.warmup_until})

        def _emit(self, evt):
            if evt.get('type') == 'live_end':
                emit(evt)

    if '--self-test' in sys.argv:
        message = ChatMessage()
        message.common.msg_id = 123456
        message.user.nick_name = '测试观众'
        message.content = '加血'
        receiver = Receiver('0', lambda evt: None)
        receiver._parseChatMsg(message.SerializeToString())
        from liveMan import generateSignature
        signature=generateSignature('wss://example.invalid/?room_id=0')
        assert isinstance(signature,str) and signature
        emit({'type':'signature_self_test','passed':True})
        from douyin_commands import defaults, preview, WEATHERS
        rules = defaults()
        gift = preview('送苹果', rules)
        money = preview('可以加１００卢比', rules)
        assert gift['item']['actor'] == 'Item_Fruit_A'
        assert money['command']['argument'] == '100'
        assert all(preview(name, rules)['matched'] for name in WEATHERS.values())
        emit({'type':'command_self_test','gift':gift['item']['name'],
              'rupees':money['command']['argument'],'weatherTypes':len(WEATHERS)})
        return

    room, kind = sys.argv[-2:]
    while True:
        try:
            receiver = Receiver(room, lambda evt: None,
                                room_id=room if kind == 'room' else None, warmup=20)
            receiver._connectWebSocket()
        except Exception as exc:
            connection_error(exc)
        emit({'type': 'connection', 'state': 'reconnecting'})
        time.sleep(5)


if __name__ == '__main__':
    main()
