# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 用の設定。`pyinstaller ygo-card-cropper.spec` で exe を作る。"""

block_cipher = None

a = Analysis(
    ["app.py"],
    pathex=[],
    binaries=[],
    # 同梱するハッシュDB。tkdnd の DLL は pyinstaller-hooks-contrib のフックが入れる
    datas=[("data", "data")],
    hiddenimports=["tkinterdnd2"],
    hookspath=[],
    runtime_hooks=[],
    # OCR を使わないので、重い科学計算系は明示的に外しておく
    excludes=["scipy", "torch", "cv2", "matplotlib", "pandas", "imagehash", "PyQt5", "PySide6"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="遊戯王カード切り抜きツール",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,                          # UPX 圧縮はウイルス対策ソフトの誤検知を招きやすい
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,                      # GUI なのでコンソールは出さない
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
