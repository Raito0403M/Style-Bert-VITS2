#!/usr/bin/env python3
"""
Whisperモデルのロードテスト
"""

import os
import time
from faster_whisper import WhisperModel

print("=== Whisperモデルロードテスト ===")

# 環境設定
model_size = os.getenv("WHISPER_MODEL", "base")
device = "cuda" if os.getenv("USE_GPU", "true").lower() == "true" else "cpu"
compute_type = "float16" if device == "cuda" else "int8"

print(f"モデル: {model_size}")
print(f"デバイス: {device}")
print(f"Compute Type: {compute_type}")
print("-" * 40)

# モデルロード
print(f"{model_size}モデルをロード中...")
start_time = time.time()

try:
    model = WhisperModel(
        model_size,
        device=device,
        compute_type=compute_type,
        download_root=None,
        local_files_only=False
    )
    
    load_time = time.time() - start_time
    print(f"✓ モデルロード完了！ ({load_time:.2f}秒)")
    
    # モデル情報を表示
    print(f"\nモデル情報:")
    print(f"- デバイス: {model.device}")
    print(f"- 特徴量抽出器: {model.feature_extractor}")
    
except Exception as e:
    print(f"✗ エラー: {e}")
    print("\nトラブルシューティング:")
    print("1. インターネット接続を確認")
    print("2. ディスク容量を確認")
    print("3. より小さいモデル（tiny）を試す")

print("\n完了！")