#!/usr/bin/env python3
"""
各コンポーネントを個別にテストして問題を特定
"""

import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

# 環境変数読み込み
load_dotenv()

print("=== Buzz Robot コンポーネントテスト ===")
print("-" * 40)

# 1. 環境変数チェック
print("\n1. 環境変数チェック:")
print(f"   OPENAI_API_KEY: {'設定済み' if os.getenv('OPENAI_API_KEY') else '未設定'}")
print(f"   WHISPER_MODEL: {os.getenv('WHISPER_MODEL', 'tiny')}")
print(f"   USE_GPU: {os.getenv('USE_GPU', 'true')}")

# 2. cuDNNライブラリパスを設定
os.environ['LD_LIBRARY_PATH'] = '/usr/lib/x86_64-linux-gnu:' + os.environ.get('LD_LIBRARY_PATH', '')
print(f"\n2. LD_LIBRARY_PATH設定:")
print(f"   {os.environ['LD_LIBRARY_PATH']}")

# 3. Whisperモデルテスト
print("\n3. Whisperモデルテスト:")
try:
    from faster_whisper import WhisperModel
    
    device = "cuda" if os.getenv("USE_GPU", "true").lower() == "true" else "cpu"
    model_size = os.getenv("WHISPER_MODEL", "tiny")
    
    print(f"   モデル: {model_size}, デバイス: {device}")
    print("   ロード中...")
    
    whisper_model = WhisperModel(
        model_size,
        device=device,
        compute_type="auto"  # autoで互換性を確保
    )
    
    print("   ✓ Whisperモデルロード成功")
    
    # テスト音声ファイルで認識テスト
    test_wav = Path("test_audio.wav")
    if test_wav.exists():
        print("   音声認識テスト中...")
        segments, _ = whisper_model.transcribe(
            str(test_wav),
            language="ja"
        )
        text = "".join([s.text for s in segments])
        print(f"   ✓ 認識結果: {text}")
    else:
        print("   ! test_audio.wav が見つかりません")
        
except Exception as e:
    print(f"   ✗ エラー: {e}")
    import traceback
    traceback.print_exc()

# 4. TTSモデルテスト
print("\n4. TTSモデルテスト:")
try:
    from style_bert_vits2.tts_model import TTSModel
    from style_bert_vits2.constants import Languages
    from config import get_config
    
    config = get_config()
    model_dir = Path(config.assets_root)
    
    print("   TTSモデルロード中...")
    tts_model = TTSModel(
        model_path=model_dir / "amitaro" / "amitaro.safetensors",
        config_path=model_dir / "amitaro" / "config.json",
        style_vec_path=model_dir / "amitaro" / "style_vectors.npy",
        device=device
    )
    
    tts_model.load()
    print("   ✓ TTSモデルロード成功")
    
    # 音声生成テスト
    print("   音声生成テスト中...")
    sr, audio = tts_model.infer(
        text="テストです",
        language=Languages.JP,
        speaker_id=0,
        style="Neutral",
        style_weight=5.0,
    )
    
    print(f"   ✓ 音声生成成功: サンプルレート={sr}, 長さ={len(audio)}")
    
except Exception as e:
    print(f"   ✗ エラー: {e}")
    import traceback
    traceback.print_exc()

# 5. OpenAI APIテスト
print("\n5. OpenAI APIテスト:")
try:
    from openai import OpenAI
    
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    print("   API接続テスト中...")
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": "こんにちは"}],
        max_tokens=10
    )
    
    print(f"   ✓ API応答: {response.choices[0].message.content}")
    
except Exception as e:
    print(f"   ✗ エラー: {e}")
    if "api_key" in str(e).lower():
        print("   ! APIキーが無効または未設定です")

# 6. 統合テスト
print("\n6. 統合テスト (音声ファイル処理):")
try:
    import io
    from scipy.io import wavfile
    import numpy as np
    
    # ダミー音声データ作成
    print("   ダミー音声データ作成...")
    sample_rate = 16000
    duration = 1.0
    samples = int(sample_rate * duration)
    audio_data = np.random.randint(-1000, 1000, samples, dtype=np.int16)
    
    with io.BytesIO() as wav_io:
        wavfile.write(wav_io, sample_rate, audio_data)
        audio_bytes = wav_io.getvalue()
    
    print(f"   ✓ 音声データ作成: {len(audio_bytes)} bytes")
    
    # 音声認識
    if 'whisper_model' in locals():
        print("   音声認識テスト...")
        temp_path = Path("temp_test.wav")
        with open(temp_path, "wb") as f:
            f.write(audio_bytes)
        
        try:
            segments, _ = whisper_model.transcribe(
                str(temp_path),
                language="ja",
                initial_prompt="こんにちは"
            )
            text = "".join([s.text for s in segments])
            print(f"   ✓ 認識完了: {text if text else '(無音)'}")
        finally:
            if temp_path.exists():
                temp_path.unlink()
    
    # TTS生成
    if 'tts_model' in locals():
        print("   TTS生成テスト...")
        sr, audio = tts_model.infer(
            text="テスト完了",
            language=Languages.JP,
            speaker_id=0,
            style="Neutral",
            style_weight=5.0,
        )
        print(f"   ✓ TTS生成完了: {len(audio)} samples")
        
except Exception as e:
    print(f"   ✗ エラー: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 40)
print("テスト完了！")
print("\n問題がある場合は、エラーメッセージを確認してください。")