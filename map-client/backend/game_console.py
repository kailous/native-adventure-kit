"""Typed MCP facade for the maintained GUI console; no arbitrary commands."""
from game_control import ControlError, WEATHER_TYPES, encode

BOOLEAN = {'type': 'boolean'}
WEATHER = {'type': 'string', 'enum': list(WEATHER_TYPES)}
SEARCH = {'keyword': {'type': 'string'}, 'limit': {'type': 'integer', 'minimum': 1, 'maximum': 100}}
# name, description, properties, required, read-only
DEFINITIONS = [
 ('get_game_console_status', 'Read all native game console values, locks, durability, weather, spawn result and saved preferences. A spawn accepted flag is not proof of creation; inspect spawn.created and itemId.', {}, [], True),
 ('set_game_value', 'Set one current value: health 0–40 hearts in 0.25 steps, stamina 0–3 wheels, rupees integer 0–99999999, arrows integer 0–999. Zero health can kill Link. Does not enable its lock.', {'target': {'type': 'string', 'enum': ['health','stamina','rupees','arrows']}, 'value': {'type': 'number', 'minimum': 0, 'maximum': 99999999}}, ['target','value'], False),
 ('set_game_lock', 'Enable or disable a saved console lock for health, stamina, rupees, arrows, or materials/meals/capsules fixed at 99 (items_99). items_99 is fixed quantity, not a generic infinite-item feature. Shares GUI preferences.', {'target': {'type': 'string', 'enum': ['health','stamina','rupees','arrows','items_99']}, 'enabled': BOOLEAN}, ['target','enabled'], False),
 ('set_health_cap', 'Enable/disable the saved health cap. When enabled, value is required: 0.25–40 hearts in 0.25 steps.', {'enabled': BOOLEAN, 'value': {'type': 'number', 'minimum': 0.25, 'maximum': 40}}, ['enabled'], False),
 ('set_equipment_durability', 'Set durability for all pouch weapons, bows or shields. Modes: normal, near_break, reset, infinite. Normal/infinite persist with GUI settings; near_break/reset are one-shot. Requires pouch scope.', {'target': {'type': 'string', 'enum': ['weapon','bow','shield']}, 'mode': {'type': 'string', 'enum': ['normal','near_break','reset','infinite']}}, ['target','mode'], False),
 ('set_game_weather', 'Request one weather change. Region/game transitions may affect the visible result. If a weather lock is active, updates its saved choice too.', {'weather': WEATHER}, ['weather'], False),
 ('set_weather_lock', 'Enable/disable the saved weather lock. weather is required when enabling.', {'enabled': BOOLEAN, 'weather': WEATHER}, ['enabled'], False),
 ('search_spawn_items', 'Search the maintained wish-item catalog by Chinese name or actor ID. Empty keyword lists items up to limit (default 20). Use the returned actor with spawn_game_item.', SEARCH, [], True),
 ('spawn_game_item', 'Wish for exactly one catalog item near Link, identified by actor from search_spawn_items. At least one second between requests. Checks game catalog compatibility. Never retry after timeout. accepted means queued; only created=true confirms creation, later read get_game_console_status or observe the game.', {'actor': {'type': 'string'}}, ['actor'], False),
 ('search_amiibo', 'Search supported virtual amiibo by Chinese/English name or ID; duplicate display names can represent different models. Use the exact returned ID.', SEARCH, [], True),
 ('get_amiibo_status', 'Read native 1.4.3 virtual amiibo availability and pending scan state.', {}, [], True),
 ('scan_amiibo', 'Submit one virtual amiibo scan by catalog ID. accepted is not proof of recognition or rewards; check the game screen. Never retry automatically.', {'id': {'type': 'string'}}, ['id'], False),
]
NAMES = {row[0] for row in DEFINITIONS}

def search(items, keyword='', limit=20):
 query = keyword.strip().casefold()
 matches = [item for item in items if any(query in str(v).casefold() for v in item.values())]
 matches.sort(key=lambda item: not any(query == str(v).casefold() for v in item.values()))
 return {'items': matches[:limit], 'total': len(matches), 'limit': limit}

def execute(name, args):
 if name == 'search_spawn_items':
  from spawn_catalog import ITEMS, CATALOG_HASH
  return {**search(ITEMS, **args), 'catalogHash': CATALOG_HASH}
 if name == 'search_amiibo':
  from amiibo_catalog import ITEMS
  return search(ITEMS, **args)
 if name in ('get_amiibo_status', 'scan_amiibo'):
  from amiibo import execute as scan
  return scan(None if name == 'get_amiibo_status' else args)
 actions = {'get_game_console_status': 'status', 'set_health_cap': 'set_health_cap',
            'set_equipment_durability': 'set_durability', 'set_game_weather': 'set_weather',
            'set_weather_lock': 'set_weather_lock', 'spawn_game_item': 'spawn_item'}
 data = dict(args)
 if name == 'set_game_value':
  action = 'set_' + data.pop('target')
 elif name == 'set_game_lock':
  target = data.pop('target')
  action = 'set_items_99' if target == 'items_99' else 'set_' + target + '_lock'
 else:
  action = actions[name]
 data['action'] = action
 # Reject semantic errors before acquiring the GUI preference manager or doing I/O.
 encode(data, 0)
 from game_control_preferences import manager
 return manager().execute(data)
