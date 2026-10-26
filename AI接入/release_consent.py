"""Explicit consent gate used by the release helpers; never persists consent."""
import sys
from pathlib import Path

PHRASE = '我已阅读《使用协议与风险说明》v1.2，确认自备合法输入，遵守相应许可证，并授权本次构建或接入操作。'


def agreement_path():
    return Path(__file__).resolve().parents[1] / '使用协议.md'


def require_consent(value=None):
    path = agreement_path()
    print('请先完整阅读《使用协议与风险说明》v1.2：' + str(path), file=sys.stderr)
    print('重点：遵守开源及第三方许可；自备合法游戏、更新、密钥；'
          '原开源许可优先；存在构建、游戏与远程连接风险。', file=sys.stderr)
    if value is None and sys.stdin.isatty():
        print('请本人输入完整确认语（不同意请退出）：\n' + PHRASE, file=sys.stderr)
        value = input()
    if value != PHRASE:
        raise ValueError('未取得完整同意确认语，操作已停止。agent 不得代答；仅在使用者已亲自回复后才能传 --consent。')

