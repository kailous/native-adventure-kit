"""On-demand native game-frame capture; no desktop capture or arbitrary file paths."""
import os
import struct
import tempfile
import threading
import time
from pathlib import Path
from PIL import Image

from game_control import ControlError

_lock = threading.Lock()
MAX_IMAGE_BYTES = 2 * 1024 * 1024

def capture():
    if os.environ.get('TOTK_CLIENT_EDITION') != 'native':
        raise ControlError('游戏截图仅接入原生地图版', 501)
    if not _lock.acquire(blocking=False):
        raise ControlError('已有截图请求，请稍后重试', 409)
    try:
        from game_control import execute
        execute({'action': 'status'})  # Fail before queuing if the game is offline.
        channel = Path.home() / 'Library/Application Support/MacNativeGames/TOTK/input.txt'
        if not channel.is_file() or channel.is_symlink():
            raise ControlError('原生游戏截图通道不可用，请通过游戏 App 启动', 409)
        with tempfile.TemporaryDirectory(prefix='totk-mcp-frame-') as directory:
            png = Path(directory) / 'frame.png'
            jpg = Path(directory) / 'frame.jpg'
            requested = time.time()
            # The native reader tails this append-only channel. Never truncate or
            # replace its inode, which would lose other commands / detach its reader.
            command = ('shot ' + str(png) + '\n').encode()
            fd = os.open(channel, os.O_WRONLY | os.O_APPEND | os.O_NOFOLLOW)
            try:
                if os.write(fd, command) != len(command):
                    raise ControlError('截图请求未完整写入')
            finally:
                os.close(fd)
            deadline = time.monotonic() + 8
            while time.monotonic() < deadline:
                if png.exists():
                    data = png.read_bytes()
                    if data.startswith(b'\x89PNG\r\n\x1a\n') and data.endswith(b'IEND\xaeB`\x82'):
                        break
                time.sleep(0.05)
            else:
                raise ControlError('等待游戏新画面超时；未返回旧截图', 504)
            if len(data) < 24:
                raise ControlError('游戏截图无效')
            width, height = struct.unpack('>II', data[16:24])
            with Image.open(png) as frame:
                rgb = frame.convert('RGB')
                # Remove only exactly black outer padding, retaining every
                # nonblack source pixel. An entirely black frame stays full size.
                bounds = rgb.getbbox() or (0, 0, width, height)
                picture = rgb.crop(bounds)
                picture.thumbnail((1280, 1280), Image.Resampling.LANCZOS)
                picture.save(jpg, format='JPEG', quality=75)
                output_width, output_height = picture.size
            image = jpg.read_bytes()
            if not image.startswith(b'\xff\xd8') or len(image) > MAX_IMAGE_BYTES:
                raise ControlError('游戏截图超出传输限制')
            return image, {'source': 'native-game-render', 'requestedAt': requested,
                           'capturedAt': png.stat().st_mtime, 'receivedAt': time.time(),
                           'sourceWidth': width, 'sourceHeight': height,
                           'crop': list(bounds), 'imageWidth': output_width, 'imageHeight': output_height,
                           'maxImageDimension': 1280, 'mimeType': 'image/jpeg'}
    except (OSError, ValueError) as error:
        raise ControlError('游戏截图读取或编码失败') from error
    finally:
        _lock.release()
