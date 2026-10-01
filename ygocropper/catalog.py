# -*- coding: utf-8 -*-
"""照合用データの置き場所と読み書き。

  * 同梱データ    : アプリに同梱するハッシュDB（カードIDとハッシュ値だけ）
  * ユーザーデータ : %APPDATA%/YgoCardCropper/ 以下。
                    追加ハッシュ・取得したカード名・設定を置く。

同梱データは書き換えず、更新分はユーザーデータ側に重ねる。
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

from .phash import HASH_HEX, HEX_PER_REGION

APP_NAME = "YgoCardCropper"
BUNDLED_HASHES = "card_hashes.json"
USER_HASHES = "card_hashes_user.json"
USER_NAMES = "card_names.json"
CONFIG_FILE = "config.json"
HASH_FORMAT = 2          # 1=64bit 1領域 / 2=128bit 2領域


def app_dir() -> str:
    """アプリ本体（exe 化された場合はその展開先）のディレクトリ。"""
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def bundled_data_dir() -> str:
    return os.path.join(app_dir(), "data")


def user_data_dir() -> str:
    base = os.environ.get("APPDATA") or os.path.expanduser("~/.config")
    path = os.path.join(base, APP_NAME)
    os.makedirs(path, exist_ok=True)
    return path


def _read_json(path):
    """JSON の辞書を読む。無い・壊れている・辞書でない場合は None。"""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _hex_list(value):
    """ハッシュの一覧として使える文字列だけを取り出す（壊れた・書き換えられたファイル対策）。"""
    if not isinstance(value, list):
        return []
    return [h for h in value if isinstance(h, str) and len(h) == HASH_HEX
            and all(c in "0123456789abcdef" for c in h)]


def _write_json(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, path)


class Catalog:
    """カードIDごとのハッシュ一覧と、カードID→カード名の対応。"""

    def __init__(self):
        self.hashes: dict[str, list[str]] = {}
        self.names: dict[str, dict] = {}
        self.names_fetched = ""
        self.known_packs: set[str] = set()   # イラストを取り込み済みの収録シリーズ
        self.bundled_count = 0
        self.user_count = 0
        self._ids = np.zeros(0, dtype=object)
        self._upper = np.zeros(0, dtype=np.uint64)   # 上側の領域（粗い照合用）
        self._lower = np.zeros(0, dtype=np.uint64)   # 下側の領域
        self.load()

    # ---------- 読み込み ----------
    def load(self):
        self.hashes = {}
        bundled = _read_json(os.path.join(bundled_data_dir(), BUNDLED_HASHES)) or {}
        for cid, hexes in (bundled.get("hashes") or {}).items():
            self.hashes[cid] = _hex_list(hexes)
        self.bundled_count = len(self.hashes)

        user = _read_json(os.path.join(user_data_dir(), USER_HASHES)) or {}
        added = 0
        if (user.get("meta") or {}).get("format") == HASH_FORMAT:
            packs = (user.get("meta") or {}).get("packs")
            self.known_packs = {p for p in packs if isinstance(p, str)} if isinstance(packs, list) else set()
            for cid, hexes in (user.get("hashes") or {}).items():
                cur = self.hashes.setdefault(cid, [])
                for h in _hex_list(hexes):
                    if h not in cur:
                        cur.append(h)
                added += 1
        else:
            # ハッシュの作り方が変わった場合は、古い追加分を捨てて取り直してもらう
            self.known_packs = set()
        self.user_count = added

        names = _read_json(os.path.join(user_data_dir(), USER_NAMES)) or {}
        cards = names.get("cards")
        self.names = {k: v for k, v in cards.items() if isinstance(v, dict)}             if isinstance(cards, dict) else {}
        self.names_fetched = (names.get("meta") or {}).get("fetched", "")
        self._reindex()

    def _reindex(self):
        ids, upper, lower = [], [], []
        for cid, hexes in self.hashes.items():
            for h in hexes:
                try:
                    hi = int(h[:HEX_PER_REGION], 16)
                    lo = int(h[HEX_PER_REGION:], 16)
                except ValueError:
                    continue
                ids.append(cid)
                upper.append(hi)
                lower.append(lo)
        self._ids = np.array(ids, dtype=object)
        self._upper = np.array(upper, dtype=np.uint64)
        self._lower = np.array(lower, dtype=np.uint64)

    # ---------- 保存 ----------
    def save_user_hashes(self):
        bundled = _read_json(os.path.join(bundled_data_dir(), BUNDLED_HASHES)) or {}
        base = bundled.get("hashes") or {}
        extra = {}
        for cid, hexes in self.hashes.items():
            diff = [h for h in hexes if h not in base.get(cid, [])]
            if diff:
                extra[cid] = diff
        _write_json(os.path.join(user_data_dir(), USER_HASHES),
                    {"meta": {"format": HASH_FORMAT, "cards": len(extra),
                              "packs": sorted(self.known_packs)},
                     "hashes": extra})

    def save_names(self, cards, fetched=""):
        meta = {"format": 1, "fetched": fetched or time.strftime("%Y-%m-%d %H:%M"),
                "count": len(cards)}
        _write_json(os.path.join(user_data_dir(), USER_NAMES), {"meta": meta, "cards": cards})
        self.names = cards
        self.names_fetched = meta["fetched"]

    # ---------- 照合 ----------
    @property
    def card_count(self):
        return len(self.hashes)

    @property
    def hash_count(self):
        return int(self._upper.size)

    def has_names(self):
        return bool(self.names)

    def display_name(self, cid):
        info = self.names.get(str(cid))
        if info and isinstance(info.get("n"), str) and info["n"]:
            return info["n"]
        return f"cid_{cid}"

    def rank(self, hex_hash, top=3, coarse=False):
        """距離の近い順に [(距離, カードID), ...] を返す（同じカードは1件にまとめる）。

        coarse=True のときは上側の領域（64bit）だけで採点する。
        ビット数が多いほど切り出し位置のズレに弱いので、
        枠を探している間はこちらを使い、確定の判断は128bit全体で行う。
        """
        if self._upper.size == 0:
            return []
        distances = _popcount(self._upper ^ np.uint64(int(hex_hash[:HEX_PER_REGION], 16)))
        if not coarse:
            distances = distances + _popcount(
                self._lower ^ np.uint64(int(hex_hash[HEX_PER_REGION:], 16)))
        limit = min(distances.size, 256)
        idx = np.argpartition(distances, limit - 1)[:limit]
        idx = idx[np.argsort(distances[idx], kind="stable")]
        out, seen = [], set()
        for i in idx:
            cid = self._ids[i]
            if cid in seen:
                continue
            seen.add(cid)
            out.append((int(distances[i]), cid))
            if len(out) >= top:
                break
        return out


if hasattr(np, "bitwise_count"):
    def _popcount(v):
        return np.bitwise_count(v)
else:                                    # numpy < 2.0 向けの手計算
    def _popcount(v):
        v = v - ((v >> np.uint64(1)) & np.uint64(0x5555555555555555))
        v = (v & np.uint64(0x3333333333333333)) + ((v >> np.uint64(2)) & np.uint64(0x3333333333333333))
        v = (v + (v >> np.uint64(4))) & np.uint64(0x0F0F0F0F0F0F0F0F)
        return (v * np.uint64(0x0101010101010101)) >> np.uint64(56)


# ---------- 設定 ----------
def load_config():
    return _read_json(os.path.join(user_data_dir(), CONFIG_FILE)) or {}


def save_config(cfg):
    _write_json(os.path.join(user_data_dir(), CONFIG_FILE), cfg)
