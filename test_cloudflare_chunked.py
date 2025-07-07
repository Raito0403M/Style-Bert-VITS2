#!/usr/bin/env python3
"""
Cloudflare Tunnel経由でのchunked encodingテスト
"""

import requests
import io

print("=== Cloudflare Tunnel Chunked Encoding テスト ===")
print("-" * 50)

# テストするURL
cloudflare_url = "https://jewel-simply-betty-floors.trycloudflare.com"
local_url = "http://localhost:8080"

def test_normal_upload(base_url):
    """通常のファイルアップロード"""
    print(f"\n1. 通常のアップロード: {base_url}")
    try:
        # テスト用のWAVファイル
        with open("proactive_test.wav", "rb") as f:
            files = {"audio": ("test.wav", f, "audio/wav")}
            response = requests.post(f"{base_url}/audio", files=files)
        
        print(f"   ステータス: {response.status_code}")
        print(f"   Headers: {dict(response.headers)}")
        if response.status_code == 200:
            print(f"   レスポンス: {response.json()}")
        else:
            print(f"   エラー: {response.text}")
    except Exception as e:
        print(f"   ✗ エラー: {e}")

def test_chunked_upload(base_url):
    """Chunked encodingでのアップロード"""
    print(f"\n2. Chunked Encodingアップロード: {base_url}")
    try:
        # マルチパートデータを手動で構築
        boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
        
        # WAVファイルを読み込む
        with open("proactive_test.wav", "rb") as f:
            wav_data = f.read()
        
        # マルチパートボディを構築
        body = io.BytesIO()
        body.write(f"------{boundary}\r\n".encode())
        body.write(b"Content-Disposition: form-data; name=\"audio\"; filename=\"test.wav\"\r\n")
        body.write(b"Content-Type: audio/wav\r\n\r\n")
        body.write(wav_data)
        body.write(f"\r\n------{boundary}--\r\n".encode())
        
        # ストリーミング用のジェネレータ
        def chunked_data():
            body.seek(0)
            while True:
                chunk = body.read(1024)  # 1KBずつ
                if not chunk:
                    break
                yield chunk
        
        headers = {
            "Content-Type": f"multipart/form-data; boundary=----{boundary}",
            "Transfer-Encoding": "chunked"
        }
        
        response = requests.post(
            f"{base_url}/audio",
            data=chunked_data(),
            headers=headers,
            stream=True
        )
        
        print(f"   ステータス: {response.status_code}")
        print(f"   Headers: {dict(response.headers)}")
        if response.status_code == 200:
            print(f"   レスポンス: {response.json()}")
        else:
            print(f"   エラー: {response.text[:200]}...")
            
    except Exception as e:
        print(f"   ✗ エラー: {e}")

def test_raw_chunked(base_url):
    """生データのchunked送信"""
    print(f"\n3. 生データChunked送信: {base_url}")
    try:
        with open("proactive_test.wav", "rb") as f:
            wav_data = f.read()
        
        def chunked_data():
            for i in range(0, len(wav_data), 4096):
                yield wav_data[i:i+4096]
        
        headers = {
            "Content-Type": "audio/wav",
            "Transfer-Encoding": "chunked"
        }
        
        response = requests.post(
            f"{base_url}/audio",
            data=chunked_data(),
            headers=headers
        )
        
        print(f"   ステータス: {response.status_code}")
        if response.status_code == 200:
            print("   ✓ 成功")
        else:
            print(f"   エラー: {response.text[:200]}...")
            
    except Exception as e:
        print(f"   ✗ エラー: {e}")

# Cloudflare制限の確認
print("\n=== Cloudflare制限の確認 ===")
print("1. Cloudflare Free Tierの制限:")
print("   - 最大アップロードサイズ: 100MB")
print("   - Chunked encoding: サポート（ただし制限あり）")
print("   - タイムアウト: 100秒")

# テスト実行
print("\n=== ローカルテスト ===")
test_normal_upload(local_url)
test_chunked_upload(local_url)
test_raw_chunked(local_url)

print("\n=== Cloudflare経由テスト ===")
test_normal_upload(cloudflare_url)
test_chunked_upload(cloudflare_url)
test_raw_chunked(cloudflare_url)

print("\n" + "=" * 50)
print("推奨事項:")
print("1. ESP32側でContent-Lengthヘッダーを設定（chunkedを使わない）")
print("2. または、通常のマルチパートアップロードを使用")
print("3. Cloudflareの有料プランでより大きなchunkedをサポート")