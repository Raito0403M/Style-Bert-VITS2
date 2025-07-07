#!/usr/bin/env python3
"""
ストリーミング機能の簡易テスト（音声再生なし）
"""

import requests
import time
from pathlib import Path

def test_streaming():
    """ストリーミング受信のテスト"""
    print("=== ストリーミング機能テスト ===")
    
    # 1. GET /proactive のテスト
    print("\n1. GET /proactive のストリーミングテスト")
    print("   サーバーに接続中...")
    
    try:
        response = requests.get("http://localhost:8080/proactive", stream=True)
        
        if response.status_code == 200:
            print("   ✓ 接続成功")
            
            # ストリーミングデータを受信
            chunks_received = []
            chunk_times = []
            start_time = time.time()
            
            print("   チャンク受信状況:")
            for i, chunk in enumerate(response.iter_content(chunk_size=4096)):
                if chunk:
                    receive_time = time.time() - start_time
                    chunks_received.append(chunk)
                    chunk_times.append(receive_time)
                    print(f"     チャンク {i+1}: {len(chunk):,} bytes @ {receive_time:.3f}秒")
                    
                    # 最初の10チャンクのみ表示
                    if i >= 9:
                        remaining = sum(1 for _ in response.iter_content(chunk_size=4096))
                        if remaining > 0:
                            print(f"     ... 他 {remaining} チャンク")
                        break
            
            total_data = b"".join(chunks_received)
            total_size = len(total_data)
            
            # 残りのデータも取得（表示はしない）
            for chunk in response.iter_content(chunk_size=4096):
                if chunk:
                    total_size += len(chunk)
            
            print(f"\n   総データサイズ: {total_size:,} bytes ({total_size/1024:.1f} KB)")
            print(f"   受信完了時間: {time.time() - start_time:.3f}秒")
            
            # ストリーミングの分析
            if len(chunk_times) > 1:
                intervals = [chunk_times[i] - chunk_times[i-1] for i in range(1, len(chunk_times))]
                avg_interval = sum(intervals) / len(intervals)
                print(f"   平均チャンク間隔: {avg_interval*1000:.1f}ミリ秒")
                print(f"   ストリーミング: {'✓ 正常' if avg_interval < 0.1 else '△ 遅延あり'}")
            
        else:
            print(f"   ✗ エラー: {response.status_code}")
            print(f"   {response.text}")
    
    except requests.exceptions.ConnectionError:
        print("   ✗ サーバーに接続できません")
        print("   buzz_robot_fastest_fixed.py が起動していることを確認してください")
    except Exception as e:
        print(f"   ✗ エラー: {e}")

    # 2. POST /audio のテスト
    print("\n2. POST /audio のストリーミングテスト")
    
    test_file = Path("proactive_test.wav")
    if not test_file.exists():
        print("   ! proactive_test.wav が見つかりません")
        print("   test_buzz_simple.py を先に実行してください")
        return
    
    try:
        print(f"   音声ファイルをアップロード中 ({test_file.stat().st_size:,} bytes)...")
        
        with open(test_file, "rb") as f:
            files = {"audio": ("test.wav", f, "audio/wav")}
            response = requests.post("http://localhost:8080/audio", files=files, stream=True)
        
        if response.status_code == 200:
            print("   ✓ アップロード成功")
            
            # ストリーミング受信
            start_time = time.time()
            total_size = 0
            chunk_count = 0
            
            print("   レスポンス受信中...")
            for chunk in response.iter_content(chunk_size=4096):
                if chunk:
                    total_size += len(chunk)
                    chunk_count += 1
            
            elapsed = time.time() - start_time
            print(f"   ✓ 受信完了: {total_size:,} bytes ({chunk_count} チャンク)")
            print(f"   処理時間: {elapsed:.3f}秒")
            
            if total_size < 1000:
                print("   ⚠ レスポンスが小さすぎます（エラーの可能性）")
        
        else:
            print(f"   ✗ エラー: {response.status_code}")
            print(f"   {response.text}")
            
    except Exception as e:
        print(f"   ✗ エラー: {e}")

def main():
    print("Buzz Robot ストリーミング機能テスト（簡易版）")
    print("-" * 50)
    
    # サーバー確認
    try:
        response = requests.get("http://localhost:8080/docs", timeout=1)
        if response.status_code == 200:
            print("✓ サーバーが稼働中です")
        else:
            print("△ サーバーは応答していますが、正常ではありません")
    except:
        print("✗ サーバーが起動していません")
        print("  別のターミナルで以下を実行してください:")
        print("  python buzz_robot_fastest_fixed.py")
        return
    
    test_streaming()
    
    print("\n" + "=" * 50)
    print("テスト完了！")

if __name__ == "__main__":
    main()