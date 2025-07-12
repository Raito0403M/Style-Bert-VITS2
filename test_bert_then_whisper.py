#!/usr/bin/env python3
"""
BERT → Whisperの順序でロードして問題を再現
"""

import os
os.environ['LD_LIBRARY_PATH'] = '/usr/lib/x86_64-linux-gnu:' + os.environ.get('LD_LIBRARY_PATH', '')

print("1. TTSModel（BERT含む）をロード...")
try:
    from style_bert_vits2.tts_model import TTSModel
    from style_bert_vits2.constants import Languages
    from config import get_config
    from pathlib import Path
    
    config = get_config()
    model_dir = Path(config.assets_root)
    model_name = "amitaro"
    
    tts_model = TTSModel(
        model_path=model_dir / model_name / "amitaro.safetensors",
        config_path=model_dir / model_name / "config.json",
        style_vec_path=model_dir / model_name / "style_vectors.npy",
        device="cuda"
    )
    tts_model.load()
    
    # BERTモデルを強制的にロード
    sr, audio = tts_model.infer(
        text="テスト",
        language=Languages.JP,
        speaker_id=0
    )
    print("   ✓ TTSModel（BERT含む）ロード成功")
except Exception as e:
    print(f"   ✗ エラー: {e}")
    import traceback
    traceback.print_exc()

print("\n2. Whisperをロード...")
try:
    from faster_whisper import WhisperModel
    model = WhisperModel("base", device="cuda", compute_type="auto")
    print("   ✓ Whisperロード成功")
    
    print("\n3. Whisperで音声認識...")
    segments, info = model.transcribe("proactive_test.wav", language="ja")
    text = "".join([segment.text for segment in segments])
    print(f"   ✓ 認識成功: {text[:30]}...")
except Exception as e:
    print(f"   ✗ エラー: {e}")
    import traceback
    traceback.print_exc()

print("\n完了！")