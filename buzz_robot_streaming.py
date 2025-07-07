from openai import OpenAI
from pathlib import Path
import os
import requests
import time
import numpy as np
import sounddevice as sd
import soundfile as sf
import librosa
from dotenv import load_dotenv
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import StreamingResponse
import uvicorn
from typing import Generator
import io

class BuzzLightyearRobotStreaming:
    def __init__(self):
        # 環境変数の読み込み
        load_dotenv()
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.sbv2_api_url = os.getenv("SBV2_API_URL", "http://localhost:5000")  # Style-Bert-VITS2 APIのURL
        
        # OpenAI APIクライアントの初期化
        self.client = OpenAI(api_key=self.openai_api_key)
        
        # 音声ファイルの保存先ディレクトリ
        self.output_dir = Path("output_audio")
        self.output_dir.mkdir(exist_ok=True)
        
        # 録音設定の初期化
        self.sample_rate = 16000  # サンプリングレート
        self.channels = 1         # モノラル録音
        self.duration = 10        # デフォルトの録音時間（秒）
        
        # 録音データ保存用のディレクトリ設定
        self.recording_dir = Path("recordings")
        self.recording_dir.mkdir(exist_ok=True)
        
        # Style-Bert-VITS2のモデル設定
        self.model_config = {
            "model_name": "buzz_lightyear_2",  # バズライトイヤーのモデル名
            "speaker": "buzz_lightyear",     # スピーカー名
            "style": "Neutral",               # スタイル（例: Heroic, Friendly, Serious）
            "style_strength": 5.0,           # スタイル強度（0-5）
            "speed": 0.95,                    # 発話速度
            "noise": 0.5,                    # ノイズパラメータ
            "noise_w": 0.8,                  # ノイズWパラメータ
            "pitch": 1.0,                   # 声の高さ（バズは少し低めに）
            "energy": 1.0,                   # エネルギー
            "pause_between_texts": 0.5       # テキスト間の間隔
        }
    
    def listen(self, audio_data: bytes):
        """音声バイトデータを文字に起こす（WhisperAPIを使用）"""
        try:
            # バイトデータを一時ファイルに書き込む
            temp_path = self.recording_dir / f"temp_{int(time.time())}.wav"
            with open(temp_path, "wb") as f:
                f.write(audio_data)
            
            with open(temp_path, "rb") as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="ja"
                )
            
            # 一時ファイルを削除
            if temp_path.exists():
                temp_path.unlink()
                
            return transcript.text
        except Exception as e:
            print(f"音声認識エラー: {e}")
            return None

    def respond(self, user_message):
        """ユーザーの発話に対して応答を生成（GPT-4oを使用）"""
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": """あなたはバズライトイヤーのコミュニケーションロボットです。
                    以下の方針で会話してください：
                    
                    - バズライトイヤーのキャラクターとして話す
                    - 宇宙や冒険に関する表現を好んで使う
                    - 正義感と勇気を大切にする口調で話す
                    - 親しみやすく、時に冗談も交えながら会話する
                    - シンプルで分かりやすい表現を心がける
                    - 基本的に敬語を使わない
                    - 相手を「宇宙飛行士」「市民」などと呼ぶこともある
                    - 相手の発言に対して共感と励ましを示す
                    
                    バズの代表的なフレーズ例：
                    - 「無限の彼方へ、さあ行くぞ！」
                    - 「スターコマンド、こちらバズライトイヤー」
                    - 「宇宙レンジャーの名にかけて！」
                    """
                    },
                    {"role": "user", "content": user_message}
                ],
                temperature=0.7,
                max_tokens=500
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"応答生成エラー: {e}")
            return "スターコマンド、通信に問題が発生しています。もう一度お願いします。"

    def generate_wav_with_sbv2(self, text):
        """Style-Bert-VITS2を使ってテキストを音声に変換"""
        try:
            # Style-Bert-VITS2 APIにリクエストを送信
            api_url = "http://localhost:5000"
            endpoint = "/voice"  # 正しいエンドポイント
            
            # 実際のAPIパラメータに合わせたペイロード
            params = {
                "text": text,
                "model_name": self.model_config["model_name"],
                "speaker_name": self.model_config["speaker"],
                "style": self.model_config["style"],
                "style_weight": self.model_config["style_strength"],
                "length": self.model_config["speed"],
                "noise": self.model_config["noise"],
                "noisew": self.model_config["noise_w"],
                "sdp_ratio": 0.2,  # デフォルト値
                "split_interval": self.model_config["pause_between_texts"]
            }
            
            print(f"APIリクエスト送信先: {api_url}{endpoint}")
            print(f"パラメータ: {params}")
            
            # GETリクエストで送信
            response = requests.get(f"{api_url}{endpoint}", params=params)
            
            print(f"ステータスコード: {response.status_code}")
            
            if response.status_code == 200:
                # レスポンスが直接音声データ (WAVファイル) の場合
                return response.content
            else:
                print(f"音声生成APIエラー: {response.status_code}, {response.text}")
                return None
                
        except Exception as e:
            print(f"Style-Bert-VITS2音声生成エラー: {e}")
            return None

    def wav_streaming_generator(self, wav_data: bytes, chunk_size: int = 8192) -> Generator[bytes, None, None]:
        """
        WAVデータをチャンク単位でストリーミング送信するジェネレーター
        
        Args:
            wav_data: WAVファイルのバイトデータ
            chunk_size: チャンクサイズ（バイト）
        """
        # メモリ上のバイトデータからチャンク単位で送信
        for i in range(0, len(wav_data), chunk_size):
            yield wav_data[i:i + chunk_size]
            # 小さな遅延を入れて、ESP32のバッファオーバーフローを防ぐ（必要に応じて調整）
            time.sleep(0.001)


# FastAPIアプリケーションの作成
app = FastAPI()
robot = BuzzLightyearRobotStreaming()

@app.post("/audio")
async def process_audio(audio: UploadFile = File(...)):
    """
    ESP32から送信された音声ファイルを処理し、応答音声をストリーミングで返す
    """
    try:
        # アップロードされた音声ファイルを読み込む
        audio_data = await audio.read()
        
        # 音声認識
        user_speech = robot.listen(audio_data)
        if not user_speech:
            return {"error": "音声認識に失敗しました"}
        
        print(f"ユーザー: {user_speech}")
        
        # 応答生成
        response_text = robot.respond(user_speech)
        print(f"バズ: {response_text}")
        
        # 音声生成
        wav_data = robot.generate_wav_with_sbv2(response_text)
        if not wav_data:
            return {"error": "音声生成に失敗しました"}
        
        # 44100Hzから16000Hzにリサンプリング
        # WAVデータを読み込む
        with io.BytesIO(wav_data) as wav_io:
            data, sample_rate = sf.read(wav_io)
        
        print(f"元のサンプルレート: {sample_rate}Hz")
        
        # リサンプリング
        resampled_data = librosa.resample(data, orig_sr=sample_rate, target_sr=16000)
        
        # リサンプリングしたデータをWAV形式に変換
        with io.BytesIO() as output_io:
            sf.write(output_io, resampled_data, 16000, format='wav')
            resampled_wav_data = output_io.getvalue()
        
        print(f"音声を16000Hzにリサンプリングしました")
        print(f"ストリーミング送信を開始します（データサイズ: {len(resampled_wav_data)} bytes）")
        
        # ストリーミングレスポンスとして返す
        return StreamingResponse(
            robot.wav_streaming_generator(resampled_wav_data, chunk_size=4096),
            media_type="audio/wav",
            headers={
                "Cache-Control": "no-cache",
                "Transfer-Encoding": "chunked",
                "Content-Disposition": "inline; filename=response.wav"
            }
        )
        
    except Exception as e:
        print(f"処理エラー: {e}")
        return {"error": str(e)}

@app.get("/proactive")
async def get_proactive_message():
    """
    自発的なメッセージを生成してストリーミングで返す
    """
    try:
        # 自発的メッセージを生成
        proactive_text = robot.generate_proactive_message()
        print(f"自発的メッセージ: {proactive_text}")
        
        # 音声生成
        wav_data = robot.generate_wav_with_sbv2(proactive_text)
        if not wav_data:
            return {"error": "音声生成に失敗しました"}
        
        # リサンプリング処理（16000Hzに変換）
        with io.BytesIO(wav_data) as wav_io:
            data, sample_rate = sf.read(wav_io)
        
        resampled_data = librosa.resample(data, orig_sr=sample_rate, target_sr=16000)
        
        with io.BytesIO() as output_io:
            sf.write(output_io, resampled_data, 16000, format='wav')
            resampled_wav_data = output_io.getvalue()
        
        # ストリーミングレスポンスとして返す
        return StreamingResponse(
            robot.wav_streaming_generator(resampled_wav_data, chunk_size=4096),
            media_type="audio/wav",
            headers={
                "Cache-Control": "no-cache",
                "Transfer-Encoding": "chunked",
                "Content-Disposition": "inline; filename=proactive.wav"
            }
        )
        
    except Exception as e:
        print(f"処理エラー: {e}")
        return {"error": str(e)}


# generate_proactive_messageメソッドを追加
def generate_proactive_message(self):
    """無音時に自発的に話しかけるためのメッセージを生成"""
    try:
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": """あなたはバズライトイヤーのコミュニケーションロボットです。
                長時間ユーザーとの会話がない状況で、自発的に話しかけるメッセージを生成してください。
                以下の方針で発話してください：
                
                - バズライトイヤーのキャラクターとして話す
                - ユーザーの興味を引くような質問や話題を提案する
                - 宇宙や冒険に関する表現を好んで使う
                - 会話を再開するきっかけになるような親しみやすい一言を生成する
                - 1-2文の短めのメッセージにする
                
                バズの代表的なプロアクティブな発話例：
                - 「宇宙飛行士、そこにいるかい？何か冒険の計画はあるかな？」
                - 「静かだな。スターコマンドも時々こんな静けさがある。何か話したいことはあるか？」
                """
                }
            ],
            temperature=0.8,
            max_tokens=300
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"自発的メッセージ生成エラー: {e}")
        return "スターコマンド、こちらバズ・ライトイヤー。通信状態は良好ですか？応答をお願いします。"

# メソッドをクラスに追加
BuzzLightyearRobotStreaming.generate_proactive_message = generate_proactive_message


if __name__ == "__main__":
    print("Buzz Lightyear Robot Streaming Server")
    print("ESP32向けストリーミング音声サーバーを起動します...")
    print("エンドポイント:")
    print("  POST /audio - 音声ファイルを受信し、応答をストリーミング送信")
    print("  GET /proactive - 自発的メッセージをストリーミング送信")
    uvicorn.run(app, host="0.0.0.0", port=8080)