#!/usr/bin/env python3
"""
TTSModelだけを分離してテスト
"""

import os
import sys
from pathlib import Path

# cuDNNパスを設定
print("1. cuDNNパスを設定...")
os.environ['LD_LIBRARY_PATH'] = '/usr/lib/x86_64-linux-gnu:' + os.environ.get('LD_LIBRARY_PATH', '')
print(f"   LD_LIBRARY_PATH: {os.environ['LD_LIBRARY_PATH']}")

# 必要最小限のインポート
print("\n2. 基本的なインポート...")
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("   ✓ dotenv loaded")
except Exception as e:
    print(f"   ✗ エラー: {e}")

# device_managerとconversation_memoryをインポート（メモリ版と同じ順序）
print("\n3. device_managerとconversation_memoryをインポート...")
try:
    from device_manager import get_device_manager
    from conversation_memory import get_conversation_memory
    dm = get_device_manager()
    cm = get_conversation_memory()
    print("   ✓ 成功")
except Exception as e:
    print(f"   ✗ エラー: {e}")

print("\n4. Style-Bert-VITS2をインポート...")
try:
    from style_bert_vits2.tts_model import TTSModel
    from style_bert_vits2.constants import DEFAULT_SDP_RATIO, DEFAULT_NOISE, DEFAULT_NOISEW, Languages
    from config import get_config
    print("   ✓ 成功")
except Exception as e:
    print(f"   ✗ エラー: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n5. TTSModelを初期化...")
try:
    config = get_config()
    model_dir = Path(config.assets_root)
    model_name = "amitaro"
    device = "cuda" if os.getenv("USE_GPU", "true").lower() == "true" else "cpu"
    
    print(f"   モデルパス: {model_dir / model_name}")
    print(f"   デバイス: {device}")
    
    tts_model = TTSModel(
        model_path=model_dir / model_name / "amitaro.safetensors",
        config_path=model_dir / model_name / "config.json",
        style_vec_path=model_dir / model_name / "style_vectors.npy",
        device=device
    )
    print("   ✓ TTSModel作成成功")
except Exception as e:
    print(f"   ✗ エラー: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n6. モデルをロード...")
try:
    tts_model.load()
    print("   ✓ ロード成功")
except Exception as e:
    print(f"   ✗ エラー: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n7. ウォームアップテスト...")
try:
    sr, audio = tts_model.infer(
        text="準備",
        language=Languages.JP,
        speaker_id=0,
        style="Neutral",
        style_weight=5.0,
        sdp_ratio=DEFAULT_SDP_RATIO,
        noise=DEFAULT_NOISE,
        noise_w=DEFAULT_NOISEW,
        length=0.95,
    )
    print(f"   ✓ 成功: サンプルレート={sr}, オーディオ長={len(audio)}")
except Exception as e:
    print(f"   ✗ エラー: {e}")
    import traceback
    traceback.print_exc()

print("\n完了！")