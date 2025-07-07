#!/usr/bin/env python3
"""
Whisper tinyモデルのテスト（最小サイズ）
"""

import os
import time
from faster_whisper import WhisperModel

print("=== Whisper Tinyモデルテスト ===")
print("最小サイズ（39MB）のモデルを使用します")

device = "cuda" if os.getenv("USE_GPU", "true").lower() == "true" else "cpu"
compute_type = "float16" if device == "cuda" else "int8"

print(f"デバイス: {device}")
print(f"Compute Type: {compute_type}")
print("-" * 40)

print("tinyモデルをロード中...")
start_time = time.time()

try:
    model = WhisperModel(
        "tiny",  # 最小モデル
        device=device,
        compute_type=compute_type
    )
    
    load_time = time.time() - start_time
    print(f"✓ モデルロード完了！ ({load_time:.2f}秒)")
    
    # テスト音声認識
    print("\nテスト: 'こんにちは'")
    segments, info = model.transcribe(
        None,  # ダミー（実際のファイルは不要）
        language="ja",
        initial_prompt="こんにちは"
    )
    
except Exception as e:
    print(f"✗ エラー: {e}")

print("\n完了！")