#!/usr/bin/env python3
"""
ストリーミング再生機能のテストクライアント
"""

import requests
import time
import pyaudio
import wave
import io
from pathlib import Path

def test_streaming_playback():
    """ストリーミング再生のテスト"""
    print("=== ストリーミング再生テスト ===")
    
    # PyAudioの初期化
    p = pyaudio.PyAudio()
    
    try:
        # 1. GET /proactive でストリーミングテスト
        print("\n1. GET /proactive のストリーミングテスト")
        print("   サーバーに接続中...")
        
        response = requests.get("http://localhost:8080/proactive", stream=True)
        
        if response.status_code == 200:
            print("   ✓ 接続成功")
            
            # ストリーミングデータを受信しながら表示
            chunks_received = []
            chunk_times = []
            start_time = time.time()
            
            print("   チャンク受信状況:")
            for i, chunk in enumerate(response.iter_content(chunk_size=4096)):
                if chunk:
                    receive_time = time.time() - start_time
                    chunks_received.append(chunk)
                    chunk_times.append(receive_time)
                    print(f"     チャンク {i+1}: {len(chunk)} bytes @ {receive_time:.3f}秒")
            
            total_data = b"".join(chunks_received)
            print(f"\n   合計: {len(total_data)} bytes")
            print(f"   受信完了時間: {time.time() - start_time:.3f}秒")
            
            # ストリーミングの分析
            if len(chunk_times) > 1:
                intervals = [chunk_times[i] - chunk_times[i-1] for i in range(1, len(chunk_times))]
                avg_interval = sum(intervals) / len(intervals)
                print(f"   平均チャンク間隔: {avg_interval:.3f}秒")
            
            # WAVファイルとして保存して検証
            with open("streaming_test.wav", "wb") as f:
                f.write(total_data)
            print("   ✓ streaming_test.wav として保存")
            
            # 音声再生（オプション）
            try:
                print("\n   音声を再生しますか？ (y/n): ", end="")
                if input().lower() == 'y':
                    with io.BytesIO(total_data) as wav_io:
                        with wave.open(wav_io, 'rb') as wf:
                            stream = p.open(
                                format=p.get_format_from_width(wf.getsampwidth()),
                                channels=wf.getnchannels(),
                                rate=wf.getframerate(),
                                output=True
                            )
                            
                            data = wf.readframes(1024)
                            while data:
                                stream.write(data)
                                data = wf.readframes(1024)
                            
                            stream.stop_stream()
                            stream.close()
                    print("   ✓ 再生完了")
            except Exception as e:
                print(f"   ! 再生エラー: {e}")
        
        else:
            print(f"   ✗ エラー: {response.status_code}")
            print(f"   {response.text}")
    
    except Exception as e:
        print(f"   ✗ 接続エラー: {e}")
    
    finally:
        p.terminate()

    # 2. POST /audio でのストリーミングテスト
    print("\n2. POST /audio のストリーミングテスト")
    
    test_file = Path("proactive_test.wav")
    if not test_file.exists():
        print("   ! proactive_test.wav が見つかりません")
        return
    
    try:
        print("   音声ファイルをアップロード中...")
        
        with open(test_file, "rb") as f:
            files = {"audio": ("test.wav", f, "audio/wav")}
            response = requests.post("http://localhost:8080/audio", files=files, stream=True)
        
        if response.status_code == 200:
            print("   ✓ アップロード成功")
            
            # ストリーミング受信
            chunks_received = []
            chunk_times = []
            start_time = time.time()
            
            print("   チャンク受信状況:")
            for i, chunk in enumerate(response.iter_content(chunk_size=4096)):
                if chunk:
                    receive_time = time.time() - start_time
                    chunks_received.append(chunk)
                    chunk_times.append(receive_time)
                    print(f"     チャンク {i+1}: {len(chunk)} bytes @ {receive_time:.3f}秒")
            
            total_data = b"".join(chunks_received)
            print(f"\n   合計: {len(total_data)} bytes")
            print(f"   受信完了時間: {time.time() - start_time:.3f}秒")
            
            # 保存
            with open("response_streaming.wav", "wb") as f:
                f.write(total_data)
            print("   ✓ response_streaming.wav として保存")
        
        else:
            print(f"   ✗ エラー: {response.status_code}")
            
    except Exception as e:
        print(f"   ✗ エラー: {e}")

def main():
    print("Buzz Robot ストリーミング機能テスト")
    print("-" * 40)
    print("サーバー: http://localhost:8080")
    print("\n注: サーバーが起動していることを確認してください")
    
    test_streaming_playback()
    
    print("\n" + "=" * 40)
    print("テスト完了！")

if __name__ == "__main__":
    main()