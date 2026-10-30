"""Typed command routing, matching, persistence and acknowledgements; no real game."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'map-client/backend'))
from douyin_commands import defaults, validate_rules, preview, perform, best_item
from douyin_live import Live
from game_control import WEATHER_TYPES


class CommandTests(unittest.TestCase):
    def test_all_weather_types(self):
        rules=defaults()
        weather_rows=[r for r in rules if r['action'].startswith('weather:')]
        self.assertEqual({r['action'].split(':')[1] for r in weather_rows},set(WEATHER_TYPES))
        for row in weather_rows:
            calls=[]
            command=preview(row['keywords'].split('|')[0],rules)['command']
            perform(command,lambda name,args:calls.append((name,args)))
            self.assertEqual(calls,[('set_game_weather',{'weather':row['action'].split(':')[1]})])

    def test_amount_orders_fullwidth_and_bounds(self):
        for text in ['加卢比100','加100卢比','可以加 １００ 卢比！']:
            self.assertEqual(preview(text,defaults())['command']['argument'],'100')
        for text in ['加-100卢比','加1.5卢比','加0卢比','加100000000卢比','不要加100卢比']:
            self.assertFalse(preview(text,defaults())['matched'],text)

    def test_exact_no_unintended_commands(self):
        for text in ['不要减血','解除锁定体力','加血减血','晴天然后打雷']:
            self.assertFalse(preview(text,defaults())['matched'])
        rules=defaults();rules[1]['enabled']=False
        self.assertFalse(preview('加血',rules)['matched'])
        rules.append(dict(action='damage',keywords='加血',enabled=True,value=1))
        rules[1]['enabled']=True
        self.assertIn('多条',preview('加血',rules)['reason'])

    def test_templates_are_literals_and_validate(self):
        rules=validate_rules([dict(action='rupees_add',keywords='发.*{数量}',enabled=True)])
        self.assertTrue(preview('发.*10',rules)['matched'])
        self.assertFalse(preview('发财10',rules)['matched'])
        for changes in [dict(action='shell'),dict(keywords='送'),dict(keywords='{物品}'),dict(keywords='送{物品}{数量}'),dict(enabled=1)]:
            with self.assertRaises(ValueError):validate_rules([{**defaults()[0],**changes}])

    def test_item_exact_partial_typo_and_no_match(self):
        self.assertEqual(best_item('苹果')['actor'],'Item_Fruit_A')
        self.assertEqual(best_item('金苹果')['actor'],'Item_Fruit_P')
        self.assertEqual(best_item('大师之剑')['actor'],'Weapon_Sword_070')
        self.assertEqual(best_item('大师剑')['name'],'大师之剑')
        item=preview('送钻石',defaults())['item']
        self.assertEqual(item['name'],'钻石')
        with self.assertRaises(ValueError):best_item('zzzzzzzzzzzzzz')

    def test_item_request_once_no_false_creation(self):
        calls=[]
        def execute(name,args):calls.append((name,args));return {'spawn':{'accepted':True,'created':False}}
        result=perform(preview('送苹果',defaults())['command'],execute)
        self.assertIn('等待游戏确认',result);self.assertNotIn('已创建',result)
        self.assertEqual(calls,[('spawn_game_item',{'actor':'Item_Fruit_A'})])
        def failure(*args):calls.append(args);raise TimeoutError()
        with self.assertRaises(TimeoutError):perform(preview('送苹果',defaults())['command'],failure)
        self.assertEqual(len(calls),2)

    def test_rupees_zero_add_clamp_and_lock(self):
        for text,current,expected in [('卢比清零',50,0),('加100卢比',50,150),('加100卢比',99999990,99999999)]:
            calls=[]
            def execute(name,args):
                calls.append((name,args))
                return {'rupees':current} if name=='get_game_console_status' else {'rupees':args['value']}
            result=perform(preview(text,defaults())['command'],execute)
            self.assertIn(str(expected),result)
            self.assertEqual(calls[-1],('set_game_value',{'target':'rupees','value':expected}))
        with self.assertRaises(ValueError):
            perform(preview('卢比清零',defaults())['command'],lambda *args:{'rupees':50,'rupeesLocked':True})

    def test_cap_and_stamina_do_not_enable_invulnerability(self):
        calls=[]
        def execute(name,args):
            calls.append((name,args))
            return {'hearts':6,'maxHearts':10} if name=='get_game_console_status' else {'healthCapEnabled':True,'healthCap':10}
        self.assertIn('仍会扣血',perform(preview('锁定最大血量',defaults())['command'],execute))
        self.assertEqual(calls[-1],('set_health_cap',{'enabled':True,'value':10}))
        calls.clear()
        def lock(name,args):calls.append((name,args));return {'staminaLocked':args['enabled']}
        perform(preview('锁定体力',defaults())['command'],lock)
        perform(preview('解除体力锁定',defaults())['command'],lock)
        self.assertEqual([x[1]['enabled'] for x in calls],[True,False])

    def test_preview_never_calls_game(self):
        execute=unittest.mock.Mock()
        live=Live(execute=execute)
        self.assertTrue(live.preview({'text':'送苹果'})['matched'])
        self.assertTrue(live.preview({'text':'卢比清零'})['matched'])
        execute.assert_not_called()

    def test_save_reload_live_update_and_atomic_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'rules.json';live=Live(rules_path=path)
            rules=defaults();rules[1]['keywords']='回血'
            live.settings={'rules':defaults(),'cooldown':2}
            live.save_rules({'rules':rules,'cooldown':3})
            self.assertEqual(live.settings['rules'][1]['keywords'],'回血')
            restored=Live(rules_path=path)
            self.assertEqual(restored.cooldown,3)
            self.assertTrue(restored.preview({'text':'回血'})['matched'])
            self.assertFalse(restored.preview({'text':'加血'})['matched'])
            old=path.read_bytes()
            with patch('douyin_live.os.replace',side_effect=OSError('disk')):
                with self.assertRaises(OSError):live.save_rules({'rules':defaults()})
            self.assertEqual(path.read_bytes(),old)
            self.assertEqual(live.rules[1]['keywords'],'回血')
            self.assertEqual(len(list(Path(folder).iterdir())),1)

    def test_bad_saved_rules_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'rules.json';path.write_text('{broken')
            live=Live(rules_path=path)
            self.assertIsNotNone(live.save_error);self.assertEqual(path.read_text(),'{broken')

    def test_global_cooldown_shared_between_weather_and_gifts(self):
        calls=[];now=[100.]
        def execute(name,args):calls.append(name);return {'spawn':{'accepted':True}}
        live=Live(execute=execute,clock=lambda:now[0]);live.settings={'rules':defaults(),'cooldown':2}
        for i,text in enumerate(['打雷','送苹果']):live.receive({'type':'chat','id':str(i+1),'text':text})
        self.assertEqual(calls,['set_game_weather'])
        now[0]+=3;live.receive({'type':'chat','id':'3','text':'送苹果'})
        self.assertEqual(calls,['set_game_weather','spawn_game_item'])

if __name__=='__main__':unittest.main()

class RuleNameTests(unittest.TestCase):
    def test_editable_name_survives_validation_and_preview(self):
        rule={**defaults()[0],'name':' 我的礼物 '}
        saved=validate_rules([rule]);self.assertEqual(saved[0]['name'],'我的礼物')
        self.assertEqual(preview('送苹果',saved)['label'],'我的礼物')
        for invalid in ['',42,'x'*41]:
            with self.assertRaises(ValueError):validate_rules([{**rule,'name':invalid}])

class MovementTests(unittest.TestCase):
    def test_mapping_and_duration(self):
        from douyin_commands import movement_defaults
        from link_control import payload
        for text,button,axes in [('前进',[],(0,1)),('后退',[],(0,-1)),('左移',[],(-1,0)),('右移',[],(1,0)),('奔跑',['b'],(0,1)),('跳跃',['x'],(0,0)),('攻击',['y'],(0,0)),('防御',['zl'],(0,0)),('瞄准',['zr'],(0,0)),('互动',['a'],(0,0)),('准备投掷',['r'],(0,0)),('蹲下',['l_stick'],(0,0)),('左侧跳',['zl','x'],(-1,0)),('右侧跳',['zl','x'],(1,0)),('后空翻',['zl','x'],(0,-1))]:
            calls=[]
            command=preview(text,defaults())['command']
            perform(command,lambda name,args:calls.append((name,args)) or {})
            name,args=calls[0]
            self.assertEqual(name,'control_link');self.assertEqual(args['buttons'],button)
            self.assertEqual(tuple(args['left_stick'].values()),axes)
            self.assertTrue(payload(args)[1]<=3000)
        for invalid in [True,0,3001,1.5]:
            with self.assertRaises(ValueError):validate_rules([{**movement_defaults()[0],'duration_ms':invalid}])

    def test_stop_bypasses_cooldown(self):
        calls=[]
        live=Live(execute=lambda name,args:calls.append(args) or {},clock=lambda:100)
        live.settings={'rules':defaults(),'cooldown':60}
        live.receive({'type':'chat','id':'m1','text':'奔跑'})
        live.receive({'type':'chat','id':'m2','text':'停止移动'})
        self.assertEqual(calls[-1],{'action':'stop'});self.assertEqual(len(calls),2)
