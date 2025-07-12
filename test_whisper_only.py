#!/usr/bin/env python3
"""
Whisperだけを単独でテスト
"""

import os
from faster_whisper import WhisperModel

# cuDNNパスを設定
os.environ['LD_LIBRARY_PATH'] = '/usr/lib/x86_64-linux-gnu:' + os.environ.get('LD_LIBRARY_PATH', '')

print("Whisperモデルをロード中...")
model = WhisperModel("base", device="cuda", compute_type="auto")
print("✓ ロード成功")

print("\n音声認識テスト...")
try:
    segments, info = model.transcribe("proactive_test.wav", language="ja")
    text = "".join([segment.text for segment in segments])
    print(f"✓ 認識成功: {text[:50]}...")
except Exception as e:
    print(f"✗ エラー: {e}")
    import traceback
    traceback.print_exc()

print("\n完了！")