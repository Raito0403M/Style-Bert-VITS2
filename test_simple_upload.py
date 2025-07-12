#!/usr/bin/env python3
"""
シンプルなアップロードテスト（デバッグ用）
"""

import requests

# サーバー起動確認
try:
    r = requests.get("http://localhost:8080/docs", timeout=2)
    print(f"サーバー状態: {r.status_code}")
except:
    print("サーバーが起動していません")
    exit(1)

# シンプルなアップロードテスト
print("\nシンプルなファイルアップロードテスト:")
try:
    with open("proactive_test.wav", "rb") as f:
        files = {"audio": ("test.wav", f, "audio/wav")}
        
        # ヘッダーなしでテスト
        print("1. ヘッダーなしでテスト...")
        response = requests.post("http://localhost:8080/audio", files=files, timeout=30)
        print(f"   ステータス: {response.status_code}")
        if response.status_code == 200:
            print(f"   レスポンス: {response.json()}")
        else:
            print(f"   エラー: {response.text}")
            
except Exception as e:
    print(f"エラー: {e}")

# デバイスAPIテスト
print("\n2. デバイスAPIテスト...")
try:
    response = requests.get("http://localhost:8080/devices/api", timeout=5)
    print(f"   ステータス: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   登録デバイス数: {len(data.get('devices', {}))}")
except Exception as e:
    print(f"   エラー: {e}")