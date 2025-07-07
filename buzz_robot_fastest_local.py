from openai import OpenAI
from pathlib import Path
import os
import time
import soundfile as sf
import librosa
from dotenv import load_dotenv
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import StreamingResponse
import uvicorn
from typing import Generator
import io
from scipy.io import wavfile
from faster_whisper import WhisperModel

# Style-Bert-VITS2を直接インポート
from style_bert_vits2.tts_model import TTSModel
from style_bert_vits2.constants import DEFAULT_SDP_RATIO, DEFAULT_NOISE, DEFAULT_NOISEW, Languages
from config import get_config

class BuzzLightyearRobotFastest:
    def __init__(self):
        # 環境変数の読み込み
        load_dotenv()
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        
        # OpenAI APIクライアントの初期化
        self.client = OpenAI(api_key=self.openai_api_key)
        
        # ローカルWhisperモデルの初期化
        whisper_model_size = os.getenv("WHISPER_MODEL", "base")  # baseをデフォルトに（turboは現在利用不可）
        device = "cuda" if os.getenv("USE_GPU", "true").lower() == "true" else "cpu"
        
        # compute_typeの選択（GPUの場合はfloat16、CPUの場合はint8）
        compute_type = "float16" if device == "cuda" else "int8"
        
        print(f"Whisperモデル({whisper_model_size})をロード中...")
        print(f"デバイス: {device}, compute_type: {compute_type}")
        print("初回実行時はモデルのダウンロードに時間がかかります...")
        
        try:
            self.whisper_model = WhisperModel(
                whisper_model_size, 
                device=device, 
                compute_type=compute_type,
                download_root=None,  # デフォルトのキャッシュディレクトリを使用
                local_files_only=False  # ダウンロードを許可
            )
            print(f"Whisperモデル({whisper_model_size})のロード完了！")
        except Exception as e:
            print(f"Whisperモデル({whisper_model_size})のロードに失敗: {e}")
            print("代わりにtinyモデルを使用します（最小サイズ）")
            self.whisper_model = WhisperModel(
                "tiny", 
                device=device, 
                compute_type=compute_type
            )
            print("Whisperモデル(tiny)のロード完了！")
        
        # 音声ファイルの保存先ディレクトリ
        self.output_dir = Path("output_audio")
        self.output_dir.mkdir(exist_ok=True)
        
        # 録音データ保存用のディレクトリ設定
        self.recording_dir = Path("recordings")
        self.recording_dir.mkdir(exist_ok=True)
        
        # Style-Bert-VITS2のモデルを直接ロード
        config = get_config()
        model_dir = Path(config.assets_root)
        model_name = "amitaro"
        
        self.tts_model = TTSModel(
            model_path=model_dir / model_name / "amitaro.safetensors",
            config_path=model_dir / model_name / "config.json",
            style_vec_path=model_dir / model_name / "style_vectors.npy",
            device=device
        )
        
        # モデルを事前にロード（初回の遅延を防ぐ）
        print("TTSモデルをロード中...")
        self.tts_model.load()
        print("TTSモデルのロード完了！")
        
        # モデル設定
        self.speaker_id = 0  # amitaro
        self.style = "Neutral"
        self.style_weight = 5.0
        self.speed = 0.95
        self.sdp_ratio = DEFAULT_SDP_RATIO
        self.noise = DEFAULT_NOISE
        self.noisew = DEFAULT_NOISEW
    
    def listen(self, audio_data: bytes):
        """音声バイトデータを文字に起こす（ローカルWhisperを使用）"""
        try:
            # バイトデータを一時ファイルに書き込む
            temp_path = self.recording_dir / f"temp_{int(time.time())}.wav"
            with open(temp_path, "wb") as f:
                f.write(audio_data)
            
            # ローカルWhisperで音声認識
            segments, _ = self.whisper_model.transcribe(
                str(temp_path),
                beam_size=1,
                language="ja",
                initial_prompt="こんにちは。",
                no_repeat_ngram_size=10
            )
            
            # セグメントからテキストを結合
            text = "".join([segment.text for segment in segments])
            
            # 一時ファイルを削除
            if temp_path.exists():
                temp_path.unlink()
                
            return text
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

    def generate_wav_direct(self, text):
        """TTSモデルを直接使って音声生成（HTTPリクエストなし）"""
        try:
            # 直接モデルで推論
            sr, audio = self.tts_model.infer(
                text=text,
                language=Languages.JP,
                speaker_id=self.speaker_id,
                style=self.style,
                style_weight=self.style_weight,
                sdp_ratio=self.sdp_ratio,
                noise=self.noise,
                noise_w=self.noisew,
                length=self.speed,
            )
            
            # WAVデータに変換
            with io.BytesIO() as wav_io:
                wavfile.write(wav_io, sr, audio)
                return wav_io.getvalue()
                
        except Exception as e:
            print(f"音声生成エラー: {e}")
            return None

    def wav_streaming_generator(self, wav_data: bytes, chunk_size: int = 8192) -> Generator[bytes, None, None]:
        """WAVデータをチャンク単位でストリーミング送信するジェネレーター"""
        for i in range(0, len(wav_data), chunk_size):
            yield wav_data[i:i + chunk_size]
            time.sleep(0.001)  # ESP32のバッファオーバーフロー防止


# FastAPIアプリケーションの作成
app = FastAPI()
robot = BuzzLightyearRobotFastest()

@app.post("/audio")
async def process_audio(audio: UploadFile = File(...)):
    """
    ESP32から送信された音声ファイルを処理し、応答音声をストリーミングで返す
    最速バージョン：HTTPリクエストを介さず直接TTSモデルを使用
    """
    try:
        start_time = time.time()
        
        # アップロードされた音声ファイルを読み込む
        audio_data = await audio.read()
        print(f"音声受信: {len(audio_data)} bytes ({time.time() - start_time:.3f}秒)")
        
        # 音声認識（ローカルWhisper）
        recognition_start = time.time()
        user_speech = robot.listen(audio_data)
        if not user_speech:
            return {"error": "音声認識に失敗しました"}
        print(f"音声認識完了: {user_speech} ({time.time() - recognition_start:.3f}秒)")
        
        # 応答生成
        response_start = time.time()
        response_text = robot.respond(user_speech)
        print(f"応答生成完了: {response_text} ({time.time() - response_start:.3f}秒)")
        
        # 音声生成（直接モデル使用）
        tts_start = time.time()
        wav_data = robot.generate_wav_direct(response_text)
        if not wav_data:
            return {"error": "音声生成に失敗しました"}
        print(f"音声生成完了: {len(wav_data)} bytes ({time.time() - tts_start:.3f}秒)")
        
        # リサンプリング（44100Hz → 16000Hz）
        resample_start = time.time()
        with io.BytesIO(wav_data) as wav_io:
            data, sample_rate = sf.read(wav_io)
        
        resampled_data = librosa.resample(data, orig_sr=sample_rate, target_sr=16000)
        
        with io.BytesIO() as output_io:
            sf.write(output_io, resampled_data, 16000, format='wav')
            resampled_wav_data = output_io.getvalue()
        print(f"リサンプリング完了 ({time.time() - resample_start:.3f}秒)")
        
        print(f"=== 総処理時間: {time.time() - start_time:.3f}秒 ===")
        
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
    """自発的なメッセージを生成してストリーミングで返す"""
    try:
        # プロアクティブメッセージを生成
        proactive_text = "宇宙飛行士、そこにいるかい？何か冒険の計画はあるかな？"
        
        # 音声生成（直接モデル使用）
        wav_data = robot.generate_wav_direct(proactive_text)
        if not wav_data:
            return {"error": "音声生成に失敗しました"}
        
        # リサンプリング処理
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


if __name__ == "__main__":
    print("Buzz Lightyear Robot FASTEST Server (Local Whisper版)")
    print("最速版：Style-Bert-VITS2とローカルWhisperを使用")
    print("エンドポイント:")
    print("  POST /audio - 音声ファイルを受信し、応答をストリーミング送信")
    print("  GET /proactive - 自発的メッセージをストリーミング送信")
    uvicorn.run(app, host="0.0.0.0", port=8080)