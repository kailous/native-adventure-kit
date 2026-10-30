import json
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from unittest.mock import Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'map-client/backend'))
from danmaku import Danmaku,DEFAULTS,validate
from douyin_live import Live,config

class DanmakuTests(unittest.TestCase):
    def test_validation(self):
        for invalid in [{'fontSize':100},{'speed':float('nan')},{'duration':1},{'enabled':1},{'mode':'bad'},{'position':'left'}]:
            with self.assertRaises(ValueError):validate({**DEFAULTS,**invalid})
    def test_persistence_and_loopback_protocol(self):
        with tempfile.TemporaryDirectory() as folder,socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as receiver:
            receiver.bind(('127.0.0.1',0));receiver.settimeout(1)
            path=Path(folder)/'danmaku.json';sender=Danmaku(path,receiver.getsockname())
            sender.save({**DEFAULTS,'enabled':True,'mode':'fade','position':'bottom','nickname':False})
            packet=json.loads(receiver.recv(8192));self.assertEqual(packet['kind'],'config')
            sender.chat('观众','你好🐱'*200)
            packet=json.loads(receiver.recv(8192));self.assertEqual(packet['protocol'],'totk-danmaku/1');self.assertLessEqual(len(packet['text']),160)
            self.assertEqual(Danmaku(path).settings['position'],'bottom');self.assertEqual(path.stat().st_mode&0o777,0o600)
    def test_chat_display_independent_of_commands_and_cooldown(self):
        execute=Mock();display=Mock();live=Live(execute=execute,display=display,clock=lambda:100)
        live.settings=config({'room':'123'});live.commands_enabled=False
        live.receive({'type':'chat','id':'1','text':'减血','user':'观众'})
        display.chat.assert_called_once_with('观众','减血');execute.assert_not_called()
        live.receive({'type':'chat','id':'1','text':'减血','user':'观众'})
        self.assertEqual(display.chat.call_count,1)
        live.receive({'type':'chat','id':'2','text':'旧弹幕','warming':True})
        self.assertEqual(display.chat.call_count,1)
    def test_save_rules_retains_display_independent_command_setting(self):
        live=Live();live.save_rules({'rules':live.rules,'commandsEnabled':False})
        live.save_rules({'rules':live.rules});self.assertFalse(live.commands_enabled)

class ConnectionErrorTests(unittest.TestCase):
    def test_reconnect_retains_error_until_socket_opens(self):
        live=Live()
        live.receive({'type':'connection','state':'error','error':'signature runtime missing'})
        live.receive({'type':'connection','state':'reconnecting'})
        self.assertEqual(live.status()['connectionError'],'signature runtime missing')
        live.receive({'type':'connection','state':'warming'})
        self.assertIsNone(live.status()['connectionError'])
