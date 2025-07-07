#!/usr/bin/env python3
"""
モデルを事前ロードしてキャッシュするスクリプト
初回実行時に一度だけ実行すれば、次回以降の起動が高速化されます
"""

import os
import sys
import time

print("=== モデル事前ロードスクリプト ===")
print("これにより次回以降の起動が高速化されます")
print("-" * 40)

# 1. BERTモデルのプリロード
print("\n1. BERTモデルをロード中...")
start_time = time.time()
try:
    # bert_modelsをインポートすることで全てのBERTモデルをロード
    from style_bert_vits2.models import bert_models
    from style_bert_vits2.constants import Languages
    
    # 各言語のBERTモデルを明示的にロード
    print("  - 日本語BERTモデル...")
    bert_models.load_model(Languages.JP)
    
    print("  - 英語BERTモデル...")
    bert_models.load_model(Languages.EN)
    
    print("  - 中国語BERTモデル...")
    bert_models.load_model(Languages.ZH)
    
    print(f"✓ BERTモデルのロード完了 ({time.time() - start_time:.2f}秒)")
except Exception as e:
    print(f"✗ BERTモデルのロードエラー: {e}")

# 2. TTSモデルのプリロード（メタデータのみ）
print("\n2. TTSモデル設定を確認中...")
try:
    from pathlib import Path
    from config import get_config
    
    config = get_config()
    model_dir = Path(config.assets_root)
    
    if (model_dir / "amitaro").exists():
        print("✓ amitaroモデルが利用可能")
    else:
        print("✗ amitaroモデルが見つかりません")
        
except Exception as e:
    print(f"✗ エラー: {e}")

# 3. Whisperモデルの確認
print("\n3. Whisperモデルを確認中...")
try:
    from faster_whisper import WhisperModel
    
    model_size = os.getenv("WHISPER_MODEL", "tiny")
    device = "cuda" if os.getenv("USE_GPU", "true").lower() == "true" else "cpu"
    compute_type = "float16" if device == "cuda" else "int8"
    
    print(f"  - モデル: {model_size}")
    print(f"  - デバイス: {device}")
    
    # キャッシュの存在確認
    cache_dir = Path.home() / ".cache" / "huggingface" / "hub"
    if cache_dir.exists():
        models = list(cache_dir.glob(f"models--*whisper*{model_size}*"))
        if models:
            print(f"✓ Whisperモデル({model_size})はキャッシュ済み")
        else:
            print(f"! Whisperモデル({model_size})は初回起動時にダウンロードされます")
    
except Exception as e:
    print(f"✗ エラー: {e}")

print("\n" + "=" * 40)
print("事前ロード完了！")
print("これで次回以降の起動が高速化されます。")
print("\n実行コマンド:")
print("  python buzz_robot_fastest_local.py")