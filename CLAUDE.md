# CLAUDE.md

## 意図どおりの挙動（バグとして直さないこと）

- **出力ファイル名の互換漢字**: `pipeline.safe_filename()` は NFC 正規化するため、
  カード名の互換漢字はファイル名では普通の字になる
  （例: 「CiNo.1000 夢幻虚光神ヌメロニアス・ヌメロニア」の「神」は U+FA19 → U+795E）。
  GUI の一覧と `log.csv` には公式DBどおりの字が残る。ビューア側で対処するので変更しない。
- **`updater.fetch_pack_cards()` の `rp=99999`**: 公式サイトのパック一覧のリンクと同じ値で、
  全件が返ることを実測で確認済み（10件に落ちることはない）。
- **tkdnd の同梱**: `pyinstaller-hooks-contrib` の `hook-tkinterdnd2.py` が
  自分のプラットフォームの DLL だけを入れる。spec に `collect_data_files` を足すと他OS用まで入るので不要。

## 変えるときに注意すること

- **ハッシュの計算方法**（`phash.py` の領域・ビット順）を変えると、同梱の `data/card_hashes.json` が使えなくなる。
  変える場合は `tools/build_hash_db.py` で作り直し、`catalog.HASH_FORMAT` を上げること。
- 公式DBへのアクセスは `REQUEST_INTERVAL`（0.4秒）の間隔を守ること。

## テスト

```bash
python -m unittest discover -s tests -v
```
