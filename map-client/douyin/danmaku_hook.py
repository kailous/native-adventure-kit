#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""订阅抖音直播间事件（弹幕/礼物/点赞/进场/关注），JSONL 输出到 stdout，
弹幕可按关键词规则触发 shell 命令。

用法:
  python3 danmaku_hook.py <live_id> [--room-id] [--hook CMD] [--rules rules.json]

live_id 即直播间链接 https://live.douyin.com/<live_id> 中的数字；
分享短链解析出的 room_id（webcast.amemv.com 跳转页路径里的数字）加 --room-id 直连。
每条事件打印一行 JSON；--hook 命令在每条弹幕到达时执行，JSON 从 stdin 传入；
--rules 指定关键词规则文件，见 rules.example.json。
"""

import argparse
import json
import os
import subprocess
import sys
import threading
import time
import warnings
from datetime import datetime, timezone

import websocket

warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL.*")

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "DouyinLiveWebFetcher"))
from liveMan import DouyinLiveWebFetcher
from protobuf.douyin import (
    PushFrame, ChatMessage, GiftMessage, LikeMessage, MemberMessage, SocialMessage,
    EmojiChatMessage, RoomUserSeqMessage, RoomStatsMessage, FansclubMessage,
    RoomRankMessage, ControlMessage,
)


def run_cmd(cmd, payload):
    def worker():
        try:
            proc = subprocess.run(
                cmd, shell=True, input=json.dumps(payload, ensure_ascii=False) + "\n",
                text=True, capture_output=True, timeout=30,
            )
            if proc.returncode != 0:
                print(f"[hook] {cmd!r} 退出码 {proc.returncode}: {proc.stderr.strip()}", file=sys.stderr)
        except Exception as e:
            print(f"[hook] {cmd!r} 执行失败: {e}", file=sys.stderr)

    threading.Thread(target=worker, daemon=True).start()


class HookedFetcher(DouyinLiveWebFetcher):
    def __init__(self, live_id, on_event, room_id=None, warmup=20):
        super().__init__(live_id)
        self.on_event = on_event
        self.warmup = warmup
        self.warmup_until = 0
        if room_id:
            # 分享短链（reflow URL）里只能拿到 room_id，跳过 live_id 网页解析直接连接
            self._DouyinLiveWebFetcher__room_id = room_id

    def _emit(self, evt):
        evt["ts"] = datetime.now(timezone.utc).astimezone().isoformat(timespec="milliseconds")
        try:
            self.on_event(evt)
        except Exception as e:
            print(f"[emit] 处理失败: {e}", file=sys.stderr)

    def _parseChatMsg(self, payload):
        m = ChatMessage().parse(payload)
        self._emit({"type": "chat", "user": m.user.nick_name, "user_id": str(m.user.id), "text": m.content})

    def _parseEmojiChatMsg(self, payload):
        m = EmojiChatMessage().parse(payload)
        self._emit({"type": "emoji", "user": m.user.nick_name, "user_id": str(m.user.id), "text": m.default_content})

    def _parseGiftMsg(self, payload):
        m = GiftMessage().parse(payload)
        self._emit({"type": "gift", "user": m.user.nick_name, "gift": m.gift.name, "count": m.combo_count})

    def _parseLikeMsg(self, payload):
        m = LikeMessage().parse(payload)
        self._emit({"type": "like", "user": m.user.nick_name, "count": m.count})

    def _parseMemberMsg(self, payload):
        m = MemberMessage().parse(payload)
        self._emit({"type": "member", "user": m.user.nick_name, "user_id": str(m.user.id)})

    def _parseSocialMsg(self, payload):
        m = SocialMessage().parse(payload)
        self._emit({"type": "follow", "user": m.user.nick_name, "user_id": str(m.user.id)})

    def _parseRoomUserSeqMsg(self, payload):
        m = RoomUserSeqMessage().parse(payload)
        self._emit({"type": "stats", "viewers": m.total, "total_viewers": m.total_pv_for_anchor})

    def _parseRoomStatsMsg(self, payload):
        m = RoomStatsMessage().parse(payload)
        self._emit({"type": "online", "text": m.display_long})

    def _parseFansclubMsg(self, payload):
        m = FansclubMessage().parse(payload)
        self._emit({"type": "fansclub", "text": m.content})

    def _parseRankMsg(self, payload):
        m = RoomRankMessage().parse(payload)
        self._emit({
            "type": "rank",
            "users": [{"user": r.user.nick_name, "score": r.score_str} for r in m.ranks_list],
        })

    def _parseControlMsg(self, payload):
        m = ControlMessage().parse(payload)
        if m.status == 3:
            self._emit({"type": "live_end"})
            self.stop()

    def _parseRoomMsg(self, payload):
        pass

    def _parseRoomStreamAdaptationMsg(self, payload):
        pass

    def _sendHeartbeat(self):
        while True:
            try:
                heartbeat = PushFrame(payload_type='hb').SerializeToString()
                self.ws.send(heartbeat, websocket.ABNF.OPCODE_PING)
            except Exception:
                break
            else:
                time.sleep(5)

    def _wsOnOpen(self, ws):
        # 连接后协议会回放最近 ~15 条历史弹幕；预热期内只打印不触发钩子/规则
        self.warmup_until = time.time() + self.warmup
        threading.Thread(target=self._sendHeartbeat, daemon=True).start()


def match_rule(rule, text):
    if "exact" in rule:
        return text.strip() == rule["exact"]
    if "contains" in rule:
        return rule["contains"] in text
    if "startswith" in rule:
        return text.startswith(rule["startswith"])
    return False


def make_handler(hook=None, rules=None, warmup_getter=None):
    rules = rules or []

    def on_event(evt):
        print(json.dumps(evt, ensure_ascii=False), flush=True)
        if evt["type"] == "chat":
            if warmup_getter and time.time() < warmup_getter():
                return
            if hook:
                run_cmd(hook, evt)
            for rule in rules:
                if match_rule(rule, evt["text"]):
                    print(f"[rule] 命中 {rule!r}", file=sys.stderr)
                    run_cmd(rule["cmd"], evt)

    return on_event


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("live_id", help="直播间号（live.douyin.com/ 后的数字）或分享链接里的 room_id")
    ap.add_argument("--room-id", action="store_true", help="参数视为 room_id 直连（分享短链解析出的数字）")
    ap.add_argument("--hook", help="每条弹幕到达时执行的 shell 命令（JSON 走 stdin）")
    ap.add_argument("--rules", help="关键词规则 JSON 文件")
    ap.add_argument("--warmup", type=float, default=20,
                    help="连接后跳过钩子/规则触发的秒数（协议会回放历史弹幕），默认 20，0 关闭")
    args = ap.parse_args()

    rules = []
    if args.rules:
        with open(args.rules, "r", encoding="utf-8") as f:
            rules = json.load(f).get("rules", [])

    # liveMan.py 内部用相对路径读取 sign.js / a_bogus.js，须在其目录下运行
    os.chdir(os.path.join(HERE, "DouyinLiveWebFetcher"))

    handler = make_handler(args.hook, rules, warmup_getter=lambda: fetcher_ref[0].warmup_until)
    fetcher_ref = [None]
    fetcher = HookedFetcher(
        args.live_id,
        handler,
        room_id=args.live_id if args.room_id else None,
        warmup=args.warmup,
    )
    fetcher_ref[0] = fetcher

    backoff = 3
    while True:
        try:
            fetcher._connectWebSocket()
        except Exception as e:
            print(f"[ws] 连接中断: {e}，{backoff}s 后重连", file=sys.stderr)
        time.sleep(backoff)
        backoff = min(backoff * 2, 60)


if __name__ == "__main__":
    main()
