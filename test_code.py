import requests
import time
import os
from pprint import pprint

# APIサーバーのベースURL（デフォルトでは同じマシン上で実行されているとする）
BASE_URL = "http://localhost:8080"

def test_root_endpoint():
    """ルートエンドポイントが応答するかテスト"""
    print("\n===== ルートエンドポイントのテスト =====")
    response = requests.get(f"{BASE_URL}/")
    print(f"ステータスコード: {response.status_code}")
    pprint(response.json())
    return response.status_code == 200

def test_respond_endpoint():
    """テキスト応答エンドポイントをテスト"""
    print("\n===== 応答エンドポイントのテスト =====")
    payload = {"text": "こんにちは、バズ・ライトイヤー！"}
    response = requests.post(f"{BASE_URL}/respond", json=payload)
    print(f"ステータスコード: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        pprint(result)
        
        # 音声ファイルが存在するか確認
        if result.get("success") and result.get("audio_path"):
            audio_url = f"{BASE_URL}{result['audio_path']}"
            print(f"\n音声ファイルのURL: {audio_url}")
            
            # 音声ファイルをダウンロードしてみる
            audio_response = requests.get(audio_url)
            if audio_response.status_code == 200:
                print("音声ファイルのダウンロード成功！")
                
                # 一時ファイルとして保存
                with open("temp_test_audio.wav", "wb") as f:
                    f.write(audio_response.content)
                print("音声ファイルをtemp_test_audio.wavとして保存しました。")
                return True
            else:
                print(f"音声ファイルのダウンロード失敗: {audio_response.status_code}")
                return False
    else:
        print(f"応答エンドポイントの呼び出しに失敗: {response.text}")
        return False

def test_proactive_endpoint():
    """自発的メッセージ生成エンドポイントをテスト"""
    print("\n===== 自発的メッセージエンドポイントのテスト =====")
    response = requests.get(f"{BASE_URL}/generate_proactive")
    print(f"ステータスコード: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        pprint(result)
        return result.get("success", False)
    else:
        print(f"自発的メッセージエンドポイントの呼び出しに失敗: {response.text}")
        return False

def test_latest_response_endpoint():
    """最新の応答情報取得エンドポイントをテスト"""
    print("\n===== 最新応答情報エンドポイントのテスト =====")
    response = requests.get(f"{BASE_URL}/latest_response")
    print(f"ステータスコード: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        pprint(result)
        return True
    else:
        print(f"最新応答情報エンドポイントの呼び出しに失敗: {response.text}")
        return False

def run_all_tests():
    """すべてのテストを実行"""
    print("===== バズ・ライトイヤーロボットAPI テスト開始 =====")
    
    root_ok = test_root_endpoint()
    respond_ok = test_respond_endpoint()
    time.sleep(1)  # APIの応答を待つ
    proactive_ok = test_proactive_endpoint()
    time.sleep(1)  # APIの応答を待つ
    latest_ok = test_latest_response_endpoint()
    
    print("\n===== テスト結果サマリー =====")
    print(f"ルートエンドポイント: {'成功' if root_ok else '失敗'}")
    print(f"応答エンドポイント: {'成功' if respond_ok else '失敗'}")
    print(f"自発的メッセージエンドポイント: {'成功' if proactive_ok else '失敗'}")
    print(f"最新応答情報エンドポイント: {'成功' if latest_ok else '失敗'}")
    
    # 一時ファイルの削除
    if os.path.exists("temp_test_audio.wav"):
        try:
            os.remove("temp_test_audio.wav")
            print("一時音声ファイルを削除しました。")
        except:
            print("一時音声ファイルの削除に失敗しました。")
    
    if all([root_ok, respond_ok, proactive_ok, latest_ok]):
        print("\nすべてのテストに成功しました！APIは正常に動作しています。")
    else:
        print("\n一部のテストに失敗しました。APIに問題がある可能性があります。")

if __name__ == "__main__":
    run_all_tests()