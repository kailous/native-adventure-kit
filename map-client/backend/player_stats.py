"""Read player capacity from validated save flag values; no game memory writes."""
import math
import struct

MAX_STAMINA_HASH = 0xf9212c74


def player_stats(flags):
    bits = flags.get(MAX_STAMINA_HASH)
    if type(bits) is not int or not 0 <= bits <= 0xffffffff:
        return {'maxStamina': None, 'source': 'save'}
    value = struct.unpack('<f', struct.pack('<I', bits))[0] / 1000
    if not math.isfinite(value) or not 1 <= value <= 3:
        value = None
    return {'maxStamina': round(value, 3) if value is not None else None, 'source': 'save'}
