from openai import OpenAI
from pathlib import Path
import os
import base64
import time
import numpy as np
import sounddevice as sd
import soundfile as sf
from dotenv import load_dotenv

class BuzzLightyearRobotAudio:
    def __init__(self):
        # 環境変数の読み込み
        load_dotenv()
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        
        # OpenAI APIクライアントの初期化
        self.client = OpenAI(api_key=self.openai_api_key)
        
        # 音声ファイルの保存先ディレクトリ
        self.output_dir = Path("output_audio")
        self.output_dir.mkdir(exist_ok=True)
        
        # 録音設定の初期化
        self.sample_rate = 44100  # サンプリングレート
        self.channels = 1         # モノラル録音
        self.duration = 10        # デフォルトの録音時間（秒）
        
        # 録音データ保存用のディレクトリ設定
        self.recording_dir = Path("recordings")
        self.recording_dir.mkdir(exist_ok=True)
        
        # バズライトイヤーのキャラクター設定
        self.character_prompt = """あなたはバズ・ライトイヤーのコミュニケーションロボットです。
        以下の方針で会話してください：
        
        - バズ・ライトイヤーのキャラクターとして話す
        - 「無限の彼方へ、さあ行くぞ！」など、バズの代表的なフレーズを時々使う
        - 宇宙や冒険に関する表現を好んで使う
        - 正義感と勇気を大切にする口調で話す
        - 親しみやすく、時に冗談も交えながら会話する
        - シンプルで分かりやすい表現を心がける
        - 相手を「宇宙飛行士」「市民」などと呼ぶこともある
        - 相手の発言に対して共感と励ましを示す
        
        バズの代表的なフレーズ例：
        - 「無限の彼方へ、さあ行くぞ！」
        - 「スターコマンド、こちらバズ・ライトイヤー」
        - 「宇宙レンジャーの名にかけて！」
        """
    
    def record_voice(self, duration=None):
        """マイクから音声を録音する"""
        if duration is None:
            duration = self.duration
            
        try:
            print(f"録音を開始します（{duration}秒間）...")
            
            # 録音の実行
            recording = sd.rec(
                int(duration * self.sample_rate),
                samplerate=self.sample_rate,
                channels=self.channels
            )
            sd.wait()  # 録音完了まで待機
            
            # 録音データの正規化
            recording = recording / np.max(np.abs(recording))
            
            # ファイル名の生成（タイムスタンプ付き）
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = self.recording_dir / f"recording_{timestamp}.wav"
            
            # WAVファイルとして保存
            sf.write(str(filename), recording, self.sample_rate)
            print(f"録音を保存しました: {filename}")
            
            return str(filename)
            
        except Exception as e:
            print(f"録音エラー: {e}")
            return None

    def audio_to_response(self, audio_path):
        """音声を入力として、GPT-4o Audioで処理し、テキスト応答と音声応答を得る"""
        try:
            # 音声ファイルを読み込みbase64エンコード
            with open(audio_path, "rb") as audio_file:
                audio_data = audio_file.read()
                encoded_audio = base64.b64encode(audio_data).decode('utf-8')
            
            # GPT-4o Audioに送信
            response = self.client.chat.completions.create(
                model="gpt-4o-audio-preview",
                modalities=["text", "audio"],
                audio={"voice": "onyx", "format": "wav"},  # onyxはバズライトイヤーに近い男性的な声
                messages=[
                    {
                        "role": "system",
                        "content": self.character_prompt
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "バズ・ライトイヤーとして応答してください"
                            },
                            {
                                "type": "input_audio",
                                "input_audio": {
                                    "data": encoded_audio,
                                    "format": "wav"
                                }
                            }
                        ]
                    }
                ]
            )
            
            # テキスト応答の取得
            text_response = None
            audio_response = None
            
            for content in response.choices[0].message.content:
                if content.type == "text":
                    text_response = content.text
                elif content.type == "output_audio":
                    audio_response = content.output_audio.data
            
            return text_response, audio_response
            
        except Exception as e:
            print(f"GPT-4o Audio処理エラー: {e}")
            return "スターコマンド、通信に問題が発生しています。もう一度お願いします。", None

    def play_audio(self, audio_path):
        """音声ファイルを再生する"""
        try:
            # 音声ファイルを読み込む
            data, sample_rate = sf.read(audio_path)
            
            # 音声を再生
            sd.play(data, sample_rate)
            sd.wait()  # 再生が完了するまで待機
            print("再生完了")
            
        except Exception as e:
            print(f"音声再生エラー: {e}")

    def save_and_play_audio(self, audio_data, filename):
        """base64エンコードされた音声データを保存して再生する"""
        try:
            if audio_data:
                # base64デコードしてファイルに保存
                output_path = self.output_dir / f"{filename}.wav"
                with open(output_path, "wb") as f:
                    f.write(base64.b64decode(audio_data))
                
                print(f"音声を保存しました: {output_path}")
                
                # 音声を再生
                print("\n応答を再生します...")
                time.sleep(1)  # 少し間を置いてから再生
                self.play_audio(str(output_path))
                
                return str(output_path)
            else:
                print("音声データがありません")
                return None
                
        except Exception as e:
            print(f"音声保存/再生エラー: {e}")
            return None

def interactive_session():
    """インタラクティブな会話セッションを実行"""
    robot = BuzzLightyearRobotAudio()
    
    print("バズ・ライトイヤーとの対話を開始します。Ctrl+Cで終了できます。")
    print("「無限の彼方へ、さあ行くぞ！」")
    session_count = 0
    
    try:
        while True:
            session_count += 1
            print("\n=== 新しい対話セッション ===")
            
            # マイクから録音
            audio_path = robot.record_voice()
            if not audio_path:
                continue
            
            # GPT-4o Audioで処理
            text_response, audio_response = robot.audio_to_response(audio_path)
            if not text_response:
                continue
            
            print(f"\nバズ: {text_response}")
            
            # 音声出力と再生
            output_filename = f"buzz_response_{session_count}"
            robot.save_and_play_audio(audio_response, output_filename)
            
            # 次のセッションまで少し間を置く
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("\n\nスターコマンドに帰還します。さようなら、宇宙飛行士！")

if __name__ == "__main__":
    interactive_session()