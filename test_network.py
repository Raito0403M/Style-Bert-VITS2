#!/usr/bin/env python3
"""
ネットワーク接続テスト
"""

import requests
import time

print("=== ネットワーク接続テスト ===")
print("-" * 40)

# テストするURL
urls = {
    "ローカル": "http://localhost:8080/docs",
    "WSL IP": "http://172.29.125.206:8080/docs",
    "Windows IP": "http://192.168.3.6:8080/docs",
    "Cloudflare": "https://jewel-simply-betty-floors.trycloudflare.com/docs"
}

# 各URLをテスト
for name, url in urls.items():
    print(f"\n{name}: {url}")
    try:
        start = time.time()
        response = requests.get(url, timeout=5)
        elapsed = time.time() - start
        
        if response.status_code == 200:
            print(f"  ✓ 成功 (ステータス: {response.status_code}, 時間: {elapsed:.2f}秒)")
            if "openapi" in response.text:
                print("  ✓ FastAPI ドキュメントを確認")
        else:
            print(f"  △ ステータス: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("  ✗ 接続エラー")
    except requests.exceptions.Timeout:
        print("  ✗ タイムアウト")
    except Exception as e:
        print(f"  ✗ エラー: {e}")

# APIエンドポイントのテスト
print("\n" + "=" * 40)
print("APIエンドポイントテスト")

endpoints = [
    ("GET", "/proactive"),
    ("POST", "/audio")
]

base_url = "https://jewel-simply-betty-floors.trycloudflare.com"

for method, endpoint in endpoints:
    print(f"\n{method} {endpoint}")
    try:
        if method == "GET":
            response = requests.get(f"{base_url}{endpoint}", timeout=10)
        else:
            # POST用のダミーファイル
            files = {"audio": ("test.wav", b"dummy", "audio/wav")}
            response = requests.post(f"{base_url}{endpoint}", files=files, timeout=10)
        
        print(f"  ステータス: {response.status_code}")
        if response.status_code == 200:
            content_type = response.headers.get('content-type', '')
            print(f"  Content-Type: {content_type}")
            if 'json' in content_type:
                print(f"  レスポンス: {response.json()}")
        elif response.status_code == 422:
            print("  ✓ 422エラー (正常 - ファイル形式の検証が機能)")
            
    except Exception as e:
        print(f"  ✗ エラー: {type(e).__name__}: {e}")

print("\n" + "=" * 40)
print("テスト完了！")