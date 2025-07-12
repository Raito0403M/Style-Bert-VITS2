#!/usr/bin/env python3
"""
インポート順序の問題を確認するテスト
"""

import os

# 最初にcuDNNパスを設定
print("1. cuDNNパスを設定...")
os.environ['LD_LIBRARY_PATH'] = '/usr/lib/x86_64-linux-gnu:' + os.environ.get('LD_LIBRARY_PATH', '')
print(f"   LD_LIBRARY_PATH: {os.environ['LD_LIBRARY_PATH']}")

print("\n2. device_managerをインポート...")
try:
    from device_manager import get_device_manager
    print("   ✓ 成功")
except Exception as e:
    print(f"   ✗ エラー: {e}")

print("\n3. conversation_memoryをインポート...")
try:
    from conversation_memory import get_conversation_memory
    print("   ✓ 成功")
except Exception as e:
    print(f"   ✗ エラー: {e}")

print("\n4. faster_whisperをインポート...")
try:
    from faster_whisper import WhisperModel
    print("   ✓ 成功")
except Exception as e:
    print(f"   ✗ エラー: {e}")

print("\n5. Whisperモデルを初期化...")
try:
    model = WhisperModel("tiny", device="cuda", compute_type="auto")
    print("   ✓ 成功")
except Exception as e:
    print(f"   ✗ エラー: {e}")
    import traceback
    traceback.print_exc()

print("\n6. 音声認識テスト...")
try:
    segments, info = model.transcribe("proactive_test.wav", language="ja")
    text = "".join([segment.text for segment in segments])
    print(f"   ✓ 成功: {text[:30]}...")
except Exception as e:
    print(f"   ✗ エラー: {e}")

print("\n完了！")