#!/usr/bin/env python3
"""
buzz_robot_fastest.pyのシンプルなテストクライアント
"""

import requests
import sys
from pathlib import Path

def test_proactive():
    """自発的メッセージのテスト"""
    print("=== GET /proactive テスト ===")
    try:
        response = requests.get("http://localhost:8080/proactive", stream=True)
        print(f"ステータスコード: {response.status_code}")
        
        if response.status_code == 200:
            # 音声データを保存
            with open("proactive_test.wav", "wb") as f:
                for chunk in response.iter_content(chunk_size=4096):
                    if chunk:
                        f.write(chunk)
            print("✓ proactive_test.wav として保存しました")
        else:
            print(f"✗ エラー: {response.text}")
    except Exception as e:
        print(f"✗ 接続エラー: {e}")
        print("  サーバーが起動していることを確認してください")

def test_audio_upload(file_path="proactive_test.wav"):
    """音声アップロードのテスト"""
    print(f"\n=== POST /audio テスト ===")
    
    # テスト用のダミー音声ファイルを作成
    if not Path(file_path).exists():
        print(f"音声ファイル {file_path} が見つかりません")
        print("テスト用のダミーWAVファイルを作成します...")
        
        import wave
        import numpy as np
        
        # 1秒間の無音WAVファイルを作成
        sample_rate = 16000
        duration = 1.0
        samples = int(sample_rate * duration)
        
        # 無音データ（わずかなノイズを追加）
        audio_data = np.random.randint(-100, 100, samples, dtype=np.int16)
        
        with wave.open(file_path, 'wb') as wf:
            wf.setnchannels(1)  # モノラル
            wf.setsampwidth(2)  # 16bit
            wf.setframerate(sample_rate)
            wf.writeframes(audio_data.tobytes())
        
        print(f"✓ {file_path} を作成しました")
    
    try:
        with open(file_path, "rb") as f:
            files = {"audio": (file_path, f, "audio/wav")}
            response = requests.post("http://localhost:8080/audio", files=files, stream=True)
        
        print(f"ステータスコード: {response.status_code}")
        
        if response.status_code == 200:
            # 応答音声を保存
            with open("response_test.wav", "wb") as f:
                for chunk in response.iter_content(chunk_size=4096):
                    if chunk:
                        f.write(chunk)
            print("✓ response_test.wav として保存しました")
        else:
            print(f"✗ エラー: {response.text}")
            
    except Exception as e:
        print(f"✗ エラー: {e}")

def check_server():
    """サーバーの稼働状況を確認"""
    print("=== サーバー接続テスト ===")
    try:
        # FastAPIの自動生成されるドキュメントページを確認
        response = requests.get("http://localhost:8080/docs")
        if response.status_code == 200:
            print("✓ サーバーは正常に稼働しています")
            print("  API ドキュメント: http://localhost:8080/docs")
            return True
        else:
            print("✗ サーバーに接続できますが、正常に応答していません")
            return False
    except requests.exceptions.ConnectionError:
        print("✗ サーバーに接続できません")
        print("  buzz_robot_fastest.py が起動していることを確認してください")
        return False
    except Exception as e:
        print(f"✗ エラー: {e}")
        return False

def main():
    print("Buzz Robot Fastest API テスト")
    print("-" * 40)
    
    # サーバー接続確認
    if not check_server():
        sys.exit(1)
    
    # 各エンドポイントをテスト
    test_proactive()
    test_audio_upload()
    
    print("\n" + "=" * 40)
    print("テスト完了！")
    print("生成されたファイル:")
    print("  - proactive_test.wav  : 自発的メッセージの音声")
    print("  - response_test.wav   : アップロードに対する応答音声")
    print("  - test_audio.wav      : テスト用の入力音声（自動生成）")

if __name__ == "__main__":
    main()