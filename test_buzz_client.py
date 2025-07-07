import requests
import io
import wave
import pyaudio
import time
from pathlib import Path

class BuzzRobotClient:
    def __init__(self, server_url="http://localhost:8080"):
        self.server_url = server_url
        self.audio_format = pyaudio.paInt16
        self.channels = 1
        self.rate = 16000
        self.chunk = 1024
        
    def test_proactive_message(self):
        """GET /proactive エンドポイントをテスト"""
        try:
            print("自発的メッセージを取得中...")
            response = requests.get(f"{self.server_url}/proactive", stream=True)
            
            if response.status_code == 200:
                # 音声データを保存
                audio_data = b""
                for chunk in response.iter_content(chunk_size=4096):
                    if chunk:
                        audio_data += chunk
                
                # ファイルに保存
                output_path = Path("test_proactive.wav")
                with open(output_path, "wb") as f:
                    f.write(audio_data)
                print(f"音声ファイルを保存しました: {output_path}")
                
                # 音声を再生（オプション）
                self.play_audio(audio_data)
                
            else:
                print(f"エラー: {response.status_code}")
                print(response.json())
                
        except Exception as e:
            print(f"接続エラー: {e}")
    
    def test_audio_upload(self, audio_file_path):
        """POST /audio エンドポイントをテスト"""
        try:
            print(f"音声ファイルをアップロード中: {audio_file_path}")
            
            with open(audio_file_path, "rb") as f:
                files = {"audio": ("test.wav", f, "audio/wav")}
                response = requests.post(f"{self.server_url}/audio", files=files, stream=True)
            
            if response.status_code == 200:
                # ストリーミング音声データを受信
                audio_data = b""
                for chunk in response.iter_content(chunk_size=4096):
                    if chunk:
                        audio_data += chunk
                
                # ファイルに保存
                output_path = Path("test_response.wav")
                with open(output_path, "wb") as f:
                    f.write(audio_data)
                print(f"応答音声を保存しました: {output_path}")
                
                # 音声を再生（オプション）
                self.play_audio(audio_data)
                
            else:
                print(f"エラー: {response.status_code}")
                print(response.text)
                
        except Exception as e:
            print(f"エラー: {e}")
    
    def record_audio(self, duration=5):
        """マイクから音声を録音"""
        print(f"{duration}秒間録音します...")
        
        p = pyaudio.PyAudio()
        stream = p.open(format=self.audio_format,
                       channels=self.channels,
                       rate=self.rate,
                       input=True,
                       frames_per_buffer=self.chunk)
        
        frames = []
        for _ in range(0, int(self.rate / self.chunk * duration)):
            data = stream.read(self.chunk)
            frames.append(data)
        
        stream.stop_stream()
        stream.close()
        p.terminate()
        
        # WAVファイルとして保存
        output_path = Path("recorded_audio.wav")
        with wave.open(str(output_path), 'wb') as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(p.get_sample_size(self.audio_format))
            wf.setframerate(self.rate)
            wf.writeframes(b''.join(frames))
        
        print(f"録音完了: {output_path}")
        return output_path
    
    def play_audio(self, audio_data):
        """音声データを再生"""
        try:
            print("音声を再生中...")
            p = pyaudio.PyAudio()
            
            # WAVデータを読み込む
            with io.BytesIO(audio_data) as wav_io:
                with wave.open(wav_io, 'rb') as wf:
                    stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                                   channels=wf.getnchannels(),
                                   rate=wf.getframerate(),
                                   output=True)
                    
                    data = wf.readframes(self.chunk)
                    while data:
                        stream.write(data)
                        data = wf.readframes(self.chunk)
                    
                    stream.stop_stream()
                    stream.close()
            
            p.terminate()
            print("再生完了")
            
        except Exception as e:
            print(f"再生エラー: {e}")

def main():
    # サーバーのURLを指定（必要に応じて変更）
    client = BuzzRobotClient("http://localhost:8080")
    
    print("Buzz Robot クライアントテスト")
    print("1. 自発的メッセージをテスト")
    print("2. 音声ファイルをアップロード")
    print("3. マイクから録音してアップロード")
    
    choice = input("選択してください (1-3): ")
    
    if choice == "1":
        client.test_proactive_message()
        
    elif choice == "2":
        audio_path = input("音声ファイルのパスを入力: ")
        if Path(audio_path).exists():
            client.test_audio_upload(audio_path)
        else:
            print("ファイルが見つかりません")
            
    elif choice == "3":
        # 録音してアップロード
        audio_path = client.record_audio(duration=5)
        time.sleep(1)
        client.test_audio_upload(audio_path)
        
    else:
        print("無効な選択です")

if __name__ == "__main__":
    main()