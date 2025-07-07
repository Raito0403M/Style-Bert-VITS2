#!/usr/bin/env python3
"""
proactive_test.wavをローカルWhisperで音声認識するテスト
"""

import os
import time
from pathlib import Path
from faster_whisper import WhisperModel
from dotenv import load_dotenv

# 環境変数読み込み
load_dotenv()

print("=== Whisper音声認識テスト ===")
print(f"対象ファイル: proactive_test.wav")
print("-" * 40)

# ファイル確認
wav_path = Path("proactive_test.wav")
if not wav_path.exists():
    print("エラー: proactive_test.wav が見つかりません")
    exit(1)

print(f"ファイルサイズ: {wav_path.stat().st_size / 1024:.1f} KB")

# Whisperモデル設定
model_size = os.getenv("WHISPER_MODEL", "tiny")
device = "cuda" if os.getenv("USE_GPU", "true").lower() == "true" else "cpu"

# cuDNNライブラリパス設定
os.environ['LD_LIBRARY_PATH'] = '/usr/lib/x86_64-linux-gnu:' + os.environ.get('LD_LIBRARY_PATH', '')

print(f"\nWhisperモデル設定:")
print(f"  モデル: {model_size}")
print(f"  デバイス: {device}")
print(f"  compute_type: auto")

# モデルロード
print("\nモデルをロード中...")
start_time = time.time()

model = WhisperModel(
    model_size,
    device=device,
    compute_type="auto"
)

print(f"モデルロード完了 ({time.time() - start_time:.2f}秒)")

# 音声認識実行
print("\n音声認識を実行中...")
recognition_start = time.time()

try:
    # 複数の設定で試す
    print("\n--- 基本設定での認識 ---")
    start1 = time.time()
    segments, info = model.transcribe(
        str(wav_path),
        language="ja",
        beam_size=1
    )
    time1 = time.time() - start1
    
    text = "".join([segment.text for segment in segments])
    print(f"認識結果: {text}")
    print(f"処理時間: {time1:.3f}秒")
    print(f"言語: {info.language}")
    print(f"確率: {info.language_probability:.2%}")
    
    # より詳細な設定で再実行
    print("\n--- 詳細設定での認識 ---")
    start2 = time.time()
    segments, info = model.transcribe(
        str(wav_path),
        language="ja",
        beam_size=5,
        best_of=5,
        temperature=0,
        initial_prompt="宇宙飛行士、そこにいるかい？",
        no_repeat_ngram_size=10
    )
    time2 = time.time() - start2
    
    text = "".join([segment.text for segment in segments])
    print(f"認識結果: {text}")
    print(f"処理時間: {time2:.3f}秒")
    
    # セグメント詳細
    print("\n--- セグメント詳細 ---")
    for i, segment in enumerate(segments):
        print(f"セグメント {i+1}:")
        print(f"  時間: {segment.start:.2f}s - {segment.end:.2f}s")
        print(f"  テキスト: {segment.text}")
        print(f"  確率: {segment.no_speech_prob:.2%} (no speech)")
    
except Exception as e:
    print(f"エラー: {e}")
    import traceback
    traceback.print_exc()

print(f"\n合計処理時間: {time.time() - recognition_start:.3f}秒")

# 音声ファイル情報を表示
print("\n--- 音声ファイル情報 ---")
try:
    import soundfile as sf
    data, samplerate = sf.read(wav_path)
    duration = len(data) / samplerate
    print(f"サンプルレート: {samplerate} Hz")
    print(f"チャンネル数: {data.shape[1] if len(data.shape) > 1 else 1}")
    print(f"長さ: {duration:.2f}秒")
    print(f"サンプル数: {len(data)}")
except Exception as e:
    print(f"音声ファイル情報取得エラー: {e}")

print("\n完了！")