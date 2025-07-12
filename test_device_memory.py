#!/usr/bin/env python3
"""
デバイス識別・メモリ機能のテストスクリプト
proactive_test.wavを使用して、異なるデバイスからの接続をシミュレート
"""

import requests
import json
import time
import os
from datetime import datetime

# テスト設定
SERVER_URL = "http://localhost:8080"
AUDIO_FILE = "proactive_test.wav"

# カラー出力用
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_colored(text, color):
    print(f"{color}{text}{Colors.ENDC}")

def test_audio_upload(device_mac, device_name, device_location, message_prefix=""):
    """音声ファイルをアップロードしてテスト"""
    
    print_colored(f"\n{'='*60}", Colors.HEADER)
    print_colored(f"テスト: {device_name} ({device_mac})", Colors.BOLD)
    print_colored(f"場所: {device_location}", Colors.OKBLUE)
    print_colored(f"{'='*60}", Colors.HEADER)
    
    # 音声ファイルの確認
    if not os.path.exists(AUDIO_FILE):
        print_colored(f"エラー: {AUDIO_FILE} が見つかりません", Colors.FAIL)
        return None
    
    # ヘッダー設定（ASCII文字のみ使用）
    import urllib.parse
    headers = {
        "X-Device-MAC": device_mac,
        "X-Device-Name": urllib.parse.quote(device_name),
        "X-Device-Location": urllib.parse.quote(device_location)
    }
    
    # ファイルアップロード
    print(f"\n1. 音声ファイルをアップロード中...")
    try:
        with open(AUDIO_FILE, 'rb') as f:
            files = {'audio': ('test.wav', f, 'audio/wav')}
            
            start_time = time.time()
            response = requests.post(
                f"{SERVER_URL}/audio",
                files=files,
                headers=headers,
                timeout=30
            )
            elapsed_time = time.time() - start_time
            
        if response.status_code == 200:
            result = response.json()
            print_colored("✓ アップロード成功", Colors.OKGREEN)
            print(f"  処理時間: {elapsed_time:.2f}秒")
            print(f"  認識テキスト: {result.get('message', 'N/A')}")
            
            # デバイス情報の表示
            device_info = result.get('device_info', {})
            if device_info:
                print_colored("\n2. デバイス情報:", Colors.OKCYAN)
                print(f"  - デバイスID: {device_info.get('device_id')}")
                print(f"  - デバイス名: {device_info.get('device_name')}")
                print(f"  - 表示名: {device_info.get('display_name')}")
                print(f"  - 場所: {device_info.get('location')}")
                print(f"  - IPアドレス: {device_info.get('ip')}")
            
            # 音声ファイルの確認
            audio_path = result.get('audio_path')
            if audio_path:
                print_colored("\n3. 生成された音声:", Colors.OKCYAN)
                print(f"  - パス: {audio_path}")
                
                # 音声ファイルをダウンロード（オプション）
                audio_url = f"{SERVER_URL}{audio_path}"
                audio_response = requests.get(audio_url)
                if audio_response.status_code == 200:
                    output_filename = f"response_{device_name.replace(' ', '_')}_{int(time.time())}.wav"
                    with open(output_filename, 'wb') as f:
                        f.write(audio_response.content)
                    print(f"  - 保存: {output_filename}")
            
            return result
            
        else:
            print_colored(f"✗ エラー: ステータスコード {response.status_code}", Colors.FAIL)
            print(f"  レスポンス: {response.text}")
            return None
            
    except Exception as e:
        print_colored(f"✗ エラー: {str(e)}", Colors.FAIL)
        return None

def test_device_api():
    """デバイスAPIのテスト"""
    print_colored(f"\n{'='*60}", Colors.HEADER)
    print_colored("デバイスAPI テスト", Colors.BOLD)
    print_colored(f"{'='*60}", Colors.HEADER)
    
    try:
        response = requests.get(f"{SERVER_URL}/devices/api", timeout=10)
        if response.status_code == 200:
            data = response.json()
            
            print_colored("\n登録デバイス:", Colors.OKCYAN)
            devices = data.get('devices', {})
            for mac, device in devices.items():
                print(f"  - {device.get('device_name')} ({mac})")
                print(f"    場所: {device.get('location')}")
                print(f"    接続回数: {device.get('total_connections')}")
                print(f"    最終接続: {device.get('last_seen')}")
                print()
            
            print_colored("統計情報:", Colors.OKCYAN)
            stats = data.get('statistics', {})
            print(f"  - 登録デバイス数: {stats.get('total_registered')}")
            print(f"  - 24時間以内のアクティブ: {stats.get('active_last_24h')}")
            print(f"  - 総接続回数: {stats.get('total_connections')}")
            
        else:
            print_colored(f"✗ エラー: ステータスコード {response.status_code}", Colors.FAIL)
            
    except Exception as e:
        print_colored(f"✗ エラー: {str(e)}", Colors.FAIL)

def main():
    """メインテスト実行"""
    print_colored("\n" + "="*80, Colors.BOLD)
    print_colored("デバイス識別・メモリ機能テスト", Colors.BOLD)
    print_colored("="*80, Colors.BOLD)
    
    # サーバー接続確認
    print("\nサーバー接続確認中...")
    try:
        response = requests.get(f"{SERVER_URL}/docs", timeout=5)
        if response.status_code == 200:
            print_colored("✓ サーバーに接続できました", Colors.OKGREEN)
        else:
            print_colored("✗ サーバーに接続できません", Colors.FAIL)
            return
    except:
        print_colored("✗ サーバーに接続できません", Colors.FAIL)
        print(f"  {SERVER_URL} でサーバーが起動していることを確認してください")
        return
    
    # テストシナリオ（一旦英語でテスト）
    test_scenarios = [
        {
            "mac": "D8:0F:99:D8:00:96",
            "name": "LivingRoom-ESP32",
            "location": "1F-Living",
            "wait": 2
        },
        {
            "mac": "AC:67:B2:36:FC:D8",
            "name": "Bedroom-ESP32",
            "location": "2F-Bedroom",
            "wait": 2
        },
        {
            "mac": "D8:0F:99:D8:00:96",  # 同じデバイスから再度
            "name": "LivingRoom-ESP32",
            "location": "1F-Living",
            "wait": 0
        }
    ]
    
    # 各シナリオを実行
    for i, scenario in enumerate(test_scenarios):
        result = test_audio_upload(
            device_mac=scenario["mac"],
            device_name=scenario["name"],
            device_location=scenario["location"]
        )
        
        if result and i < len(test_scenarios) - 1:
            print(f"\n{scenario['wait']}秒待機中...")
            time.sleep(scenario['wait'])
    
    # デバイスAPIテスト
    test_device_api()
    
    # ダッシュボードURL表示
    print_colored(f"\n{'='*60}", Colors.HEADER)
    print_colored("デバイス管理ダッシュボード", Colors.BOLD)
    print_colored(f"{'='*60}", Colors.HEADER)
    print(f"ブラウザで以下のURLを開いてください:")
    print_colored(f"{SERVER_URL}/devices", Colors.OKCYAN)
    
    print_colored("\n✓ テスト完了", Colors.OKGREEN)

if __name__ == "__main__":
    main()