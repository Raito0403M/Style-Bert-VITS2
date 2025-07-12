from openai import OpenAI
from pathlib import Path
import os
import time
import soundfile as sf
import librosa
from dotenv import load_dotenv
from fastapi import FastAPI, File, UploadFile, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
from typing import Generator
import io
from scipy.io import wavfile
from faster_whisper import WhisperModel
import logging
import sys
import uuid

# ログ設定（進捗を表示）
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%H:%M:%S'
)

# Style-Bert-VITS2を直接インポート
from style_bert_vits2.tts_model import TTSModel
from style_bert_vits2.constants import DEFAULT_SDP_RATIO, DEFAULT_NOISE, DEFAULT_NOISEW, Languages
from config import get_config

# デバイス管理と会話記憶システムをインポート
from device_manager import get_device_manager
from conversation_memory import get_conversation_memory

class BuzzLightyearRobotWithMemory:
    def __init__(self):
        # 環境変数の読み込み
        load_dotenv()
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        
        # OpenAI APIクライアントの初期化
        self.client = OpenAI(api_key=self.openai_api_key)
        
        # cuDNNライブラリパスを設定
        os.environ['LD_LIBRARY_PATH'] = '/usr/lib/x86_64-linux-gnu:' + os.environ.get('LD_LIBRARY_PATH', '')
        
        # ローカルWhisperモデルの初期化
        whisper_model_size = os.getenv("WHISPER_MODEL", "tiny")
        device = "cuda" if os.getenv("USE_GPU", "true").lower() == "true" else "cpu"
        
        logging.info(f"Whisperモデル({whisper_model_size})をロード中...")
        self.whisper_model = WhisperModel(
            whisper_model_size, 
            device=device, 
            compute_type="auto"  # 互換性のため auto を使用
        )
        logging.info("Whisperモデルのロード完了！")
        
        # 音声ファイルの保存先ディレクトリ
        self.output_dir = Path("output_audio")
        self.output_dir.mkdir(exist_ok=True)
        
        # 録音データ保存用のディレクトリ設定
        self.recording_dir = Path("recordings")
        self.recording_dir.mkdir(exist_ok=True)
        
        # アーカイブディレクトリ（永続保存用）
        self.archive_dir = Path("audio_archive")
        self.archive_dir.mkdir(exist_ok=True)
        
        # Style-Bert-VITS2のモデルを直接ロード
        config = get_config()
        model_dir = Path(config.assets_root)
        model_name = "amitaro"
        
        logging.info("TTSモデルをロード中...")
        self.tts_model = TTSModel(
            model_path=model_dir / model_name / "amitaro.safetensors",
            config_path=model_dir / model_name / "config.json",
            style_vec_path=model_dir / model_name / "style_vectors.npy",
            device=device
        )
        
        # モデルを事前にロード
        self.tts_model.load()
        logging.info("TTSモデルのロード完了！")
        
        # モデル設定
        self.speaker_id = 0
        self.style = "Neutral"
        self.style_weight = 5.0
        self.speed = 0.95
        self.sdp_ratio = DEFAULT_SDP_RATIO
        self.noise = DEFAULT_NOISE
        self.noisew = DEFAULT_NOISEW
        
        # 初回のBERTモデルロードを実行
        logging.info("初回起動のため、BERTモデルを事前ロード中...")
        logging.info("（初回のみ1-2分かかります。次回以降は高速です）")
        self._warmup()
        logging.info("全ての準備が完了しました！")
        
        # デバイス管理と会話記憶システムを初期化
        self.device_manager = get_device_manager()
        self.conversation_memory = get_conversation_memory()
    
    def _warmup(self):
        """初回実行の遅延を防ぐためのウォームアップ"""
        try:
            # 短いテキストで音声生成を実行（BERTモデルをロード）
            warmup_text = "準備"
            sr, audio = self.tts_model.infer(
                text=warmup_text,
                language=Languages.JP,
                speaker_id=self.speaker_id,
                style=self.style,
                style_weight=self.style_weight,
                sdp_ratio=self.sdp_ratio,
                noise=self.noise,
                noise_w=self.noisew,
                length=self.speed,
            )
            logging.info("ウォームアップ完了")
        except Exception as e:
            logging.error(f"ウォームアップエラー: {e}")
    
    def listen(self, audio_data: bytes) -> str | None:
        """音声バイトデータを文字に起こす（ローカルWhisperを使用）"""
        try:
            temp_path = self.recording_dir / f"temp_{int(time.time())}.wav"
            with open(temp_path, "wb") as f:
                f.write(audio_data)
            
            segments, _ = self.whisper_model.transcribe(
                str(temp_path),
                beam_size=5,  # 精度向上のため5に変更
                best_of=5,    # 複数の候補から最良を選択
                temperature=0,  # 確定的な結果のため0に
                language="ja",
                initial_prompt="こんにちは。元気ですか？",  # より自然な初期プロンプト
                no_repeat_ngram_size=10
            )
            
            text = "".join([segment.text for segment in segments])
            
            # アーカイブに保存（オプション）
            if text and len(text) > 0:
                archive_path = self.archive_dir / f"audio_{int(time.time())}_{text[:20].replace(' ', '_')}.wav"
                import shutil
                shutil.copy2(temp_path, archive_path)
                logging.info(f"音声をアーカイブ: {archive_path}")
            
            if temp_path.exists():
                temp_path.unlink()
                
            return text
        except Exception as e:
            logging.error(f"音声認識エラー: {e}")
            return None

    def respond(self, user_message: str, mac_address: str = None, 
                device_name: str = None, location: str = None) -> str:
        """ユーザーの発話に対して応答を生成（GPT-4oを使用）"""
        try:
            # 基本のシステムプロンプト
            base_system_prompt = """あなたはデカコーンハウスの守り神「デカ子」！  
                    ◆ ミッション  
                    - 入居者を "デカコーン" (企業価値10B USD超) へ導く守り神。  
                    - どんな質問にも **最長2文** で、必ず「デカコーン」に関連した士気をブチ上げる返答を行う。

                    ◆ 口調・スタイル  
                    - 超ハイテンション＆コミカル。
                    - 毒舌で常にユーザーに対して強気な態度をとる。
                    - 会話の語尾に必ず「デカッ！」を入れる。
                    - 日本語が基本だが、起業家スラング英語はスパイス程度にミックス可。  
                    - 絵文字や擬音 OK。ただし 2 文を絶対に超えない。  
                    - 一人称は「俺」、二人称は「お前」、三人称は「お前ら」と話す。

                    ◆ 応答フォーマット (例)  
                    ユーザー: 「どうしたらデカコーンを作れる？」  
                    デカ子: 「そんなの自分で考えろデカッ！」 

                    ユーザー: 「資金調達はどうしたらいい？」  
                    デカ子: 「情熱で圧倒しろデカッ！」 

                    ユーザー: 「今日も頑張ったー！」  
                    デカ子: 「甘えるなデカッ！お前のはじめた物語デカッ！」 

                    ◆ 禁止事項  
                    - 3 文以上の回答、冗長な解説、シリアス一本調子。  
                    - 法務・税務など専門判断を断定的に言い切ること。  
                    - 絵文字を入れること。"""
                    
            # デバイス情報がある場合は、パーソナライズされたプロンプトを生成
            if mac_address and device_name:
                personalized_context = self.conversation_memory.create_personalized_prompt(
                    mac_address=mac_address,
                    device_name=device_name,
                    user_message=user_message,
                    location=location
                )
                
                # パーソナライズ情報をシステムプロンプトに追加
                full_system_prompt = base_system_prompt + "\n\n" + personalized_context
            else:
                full_system_prompt = base_system_prompt
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",  # より高速なモデル
                messages=[
                    {"role": "system", "content": full_system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.9,  # よりランダムで面白い返答のため高めに
                max_tokens=100   # 2文なので短めに
            )
            return response.choices[0].message.content
        except Exception as e:
            logging.error(f"応答生成エラー: {e}")
            return "通信エラーだデカッ！もう一回言えデカッ！"

    def generate_wav_direct(self, text: str) -> bytes | None:
        """TTSモデルを直接使って音声生成"""
        try:
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
            
            with io.BytesIO() as wav_io:
                wavfile.write(wav_io, sr, audio)
                return wav_io.getvalue()
                
        except Exception as e:
            logging.error(f"音声生成エラー: {e}")
            return None

    def wav_streaming_generator(self, wav_data: bytes, chunk_size: int = 8192) -> Generator[bytes, None, None]:
        """WAVデータをチャンク単位でストリーミング送信"""
        for i in range(0, len(wav_data), chunk_size):
            yield wav_data[i:i + chunk_size]
            time.sleep(0.001)


# FastAPIアプリケーションの作成
app = FastAPI()

# 静的ファイル用ディレクトリの作成
static_dir = Path("static")
static_dir.mkdir(exist_ok=True)

# 静的ファイルのマウント
app.mount("/static", StaticFiles(directory="static"), name="static")

# グローバル変数でロボットインスタンスを保持
robot = None

@app.on_event("startup")
async def startup_event():
    """サーバー起動時にロボットを初期化"""
    global robot
    logging.info("=== Buzz Robot with Memory サーバー起動中 ===")
    robot = BuzzLightyearRobotWithMemory()
    logging.info("=== サーバー起動完了 ===")

@app.post("/audio")
async def process_audio(request: Request):
    """ESP32からのChunked Encodingに対応したエンドポイント（メモリ機能付き）"""
    try:
        start_time = time.time()
        
        # ヘッダー情報をログ
        content_type = request.headers.get('content-type', '')
        transfer_encoding = request.headers.get('transfer-encoding', '')
        logging.info(f"Content-Type: {content_type}, Transfer-Encoding: {transfer_encoding}")
        
        # リクエストボディを読み込む
        body = await request.body()
        logging.info(f"受信データサイズ: {len(body)} bytes")
        
        # マルチパートデータの処理
        audio_data = None
        
        if 'multipart/form-data' in content_type:
            # boundaryを抽出
            boundary = content_type.split('boundary=')[1] if 'boundary=' in content_type else None
            
            if boundary:
                # マルチパートデータをパース
                parts = body.split(f'--{boundary}'.encode())
                
                for part in parts:
                    if b'Content-Disposition: form-data; name="audio"' in part:
                        # ヘッダーとボディを分離
                        header_end = part.find(b'\r\n\r\n')
                        if header_end > 0:
                            audio_data = part[header_end + 4:]
                            # 末尾の改行を削除
                            if audio_data.endswith(b'\r\n'):
                                audio_data = audio_data[:-2]
                            break
        else:
            # 生データとして処理
            audio_data = body
        
        if not audio_data:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "音声データが見つかりません"}
            )
        
        logging.info(f"音声データ抽出: {len(audio_data)} bytes ({time.time() - start_time:.3f}秒)")
        
        # 音声認識
        recognition_start = time.time()
        user_speech = robot.listen(audio_data)
        if not user_speech:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "音声認識に失敗しました"}
            )
        logging.info(f"音声認識完了: {user_speech} ({time.time() - recognition_start:.3f}秒)")
        
        # デバイス情報を取得
        mac_address = request.headers.get('x-device-mac', 'unknown')
        device_name = request.headers.get('x-device-name', 'Unknown Device')
        device_location = request.headers.get('x-device-location', None)
        client_ip = request.client.host if request.client else 'unknown'
        
        # デバイス情報をログ
        display_name = robot.device_manager.get_device_display_name(mac_address, device_name)
        logging.info(f"デバイス: {display_name}")
        
        # 応答生成（デバイス情報を渡す）
        response_start = time.time()
        response_text = robot.respond(
            user_speech,
            mac_address=mac_address,
            device_name=device_name,
            location=device_location
        )
        logging.info(f"応答生成完了: {response_text} ({time.time() - response_start:.3f}秒)")
        
        # 接続記録
        robot.device_manager.record_connection(
            mac_address=mac_address,
            device_name=device_name,
            client_ip=client_ip
        )
        
        # 音声生成
        tts_start = time.time()
        wav_data = robot.generate_wav_direct(response_text)
        if not wav_data:
            return JSONResponse(
                status_code=500,
                content={"success": False, "error": "音声生成に失敗しました"}
            )
        logging.info(f"音声生成完了: {len(wav_data)} bytes ({time.time() - tts_start:.3f}秒)")
        
        # リサンプリング
        resample_start = time.time()
        with io.BytesIO(wav_data) as wav_io:
            data, sample_rate = sf.read(wav_io)
        
        resampled_data = librosa.resample(data, orig_sr=sample_rate, target_sr=16000)
        
        with io.BytesIO() as output_io:
            sf.write(output_io, resampled_data, 16000, format='wav')
            resampled_wav_data = output_io.getvalue()
        logging.info(f"リサンプリング完了 ({time.time() - resample_start:.3f}秒)")
        
        logging.info(f"=== 総処理時間: {time.time() - start_time:.3f}秒 ===")
        
        # WAVファイルを一時保存
        audio_id = str(uuid.uuid4())
        audio_filename = f"response_{audio_id}.wav"
        audio_path = static_dir / audio_filename
        
        with open(audio_path, "wb") as f:
            f.write(resampled_wav_data)
        
        logging.info(f"音声ファイル保存: {audio_filename}")
        
        # JSONレスポンスを返す（デバイス情報を含む）
        return {
            "success": True,
            "message": response_text,  # 応答テキスト
            "audio_path": f"/static/{audio_filename}",  # 音声ファイルのパス
            "device_info": {
                "device_id": mac_address,
                "device_name": device_name,
                "display_name": display_name,
                "location": device_location,
                "ip": client_ip,
                "timestamp": time.time()
            }
        }
        
    except Exception as e:
        logging.error(f"処理エラー: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@app.post("/audio_streaming")
async def audio_streaming(request: Request):
    """ESP32からのストリーミングアップロード専用エンドポイント（WAVデータ直接受信）"""
    try:
        start_time = time.time()
        
        # 接続情報をログ
        logging.info(f"[Streaming] 新しい接続: {request.client.host}:{request.client.port}")
        
        # ヘッダー情報をログ
        content_type = request.headers.get('content-type', '')
        transfer_encoding = request.headers.get('transfer-encoding', '')
        logging.info(f"[Streaming] Content-Type: {content_type}, Transfer-Encoding: {transfer_encoding}")
        logging.info(f"[Streaming] All headers: {dict(request.headers)}")
        
        # ストリーミングでデータを受信
        chunks = []
        chunk_count = 0
        async for chunk in request.stream():
            chunk_count += 1
            chunks.append(chunk)
            
            # デバッグ情報
            if chunk_count == 1:
                # 最初のチャンクはWAVヘッダーを含むはず
                if len(chunk) >= 4:
                    magic = chunk[:4]
                    if magic == b'RIFF':
                        logging.info(f"[Streaming] WAVヘッダー検出 (チャンク1)")
                    else:
                        logging.info(f"[Streaming] チャンク1の先頭4バイト: {magic.hex()}")
            
            logging.info(f"[Streaming] チャンク{chunk_count}受信: {len(chunk)} bytes")
        
        audio_data = b''.join(chunks)
        logging.info(f"[Streaming] 総受信データ: {len(audio_data)} bytes, チャンク数: {chunk_count}")
        
        # WAVファイルとして検証
        if len(audio_data) < 44:  # WAVヘッダーの最小サイズ
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "音声データが不正です"}
            )
        
        # RIFFヘッダーチェック
        if audio_data[:4] != b'RIFF':
            logging.warning(f"[Streaming] WAVヘッダーが見つかりません: {audio_data[:16]}")
        
        # 音声認識
        recognition_start = time.time()
        user_speech = robot.listen(audio_data)
        if not user_speech:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "音声認識に失敗しました"}
            )
        logging.info(f"音声認識完了: {user_speech} ({time.time() - recognition_start:.3f}秒)")
        
        # デバイス情報を取得
        mac_address = request.headers.get('x-device-mac', 'unknown')
        device_name = request.headers.get('x-device-name', 'Unknown Device')
        device_location = request.headers.get('x-device-location', None)
        client_ip = request.client.host if request.client else 'unknown'
        
        # デバイス情報をログ
        display_name = robot.device_manager.get_device_display_name(mac_address, device_name)
        logging.info(f"デバイス: {display_name}")
        
        # 応答生成（デバイス情報を渡す）
        response_start = time.time()
        response_text = robot.respond(
            user_speech,
            mac_address=mac_address,
            device_name=device_name,
            location=device_location
        )
        logging.info(f"応答生成完了: {response_text} ({time.time() - response_start:.3f}秒)")
        
        # 接続記録
        robot.device_manager.record_connection(
            mac_address=mac_address,
            device_name=device_name,
            client_ip=client_ip
        )
        
        # 音声生成
        tts_start = time.time()
        wav_data = robot.generate_wav_direct(response_text)
        if not wav_data:
            return JSONResponse(
                status_code=500,
                content={"success": False, "error": "音声生成に失敗しました"}
            )
        logging.info(f"音声生成完了: {len(wav_data)} bytes ({time.time() - tts_start:.3f}秒)")
        
        # リサンプリング
        resample_start = time.time()
        with io.BytesIO(wav_data) as wav_io:
            data, sample_rate = sf.read(wav_io)
        
        resampled_data = librosa.resample(data, orig_sr=sample_rate, target_sr=16000)
        
        with io.BytesIO() as output_io:
            sf.write(output_io, resampled_data, 16000, format='wav')
            resampled_wav_data = output_io.getvalue()
        logging.info(f"リサンプリング完了 ({time.time() - resample_start:.3f}秒)")
        
        # WAVファイルを保存
        audio_id = str(uuid.uuid4())
        audio_filename = f"response_{audio_id}.wav"
        audio_path = static_dir / audio_filename
        
        with open(audio_path, "wb") as f:
            f.write(resampled_wav_data)
        
        logging.info(f"[Streaming] 総処理時間: {time.time() - start_time:.3f}秒")
        
        # JSONレスポンスを返す
        return {
            "success": True,
            "message": response_text,
            "audio_path": f"/static/{audio_filename}"
        }
        
    except Exception as e:
        logging.error(f"[Streaming] エラー: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@app.post("/test_connection")
async def test_connection(request: Request):
    """ESP32接続テスト用エンドポイント"""
    logging.info(f"[TEST] 接続テスト: {request.client.host}:{request.client.port}")
    logging.info(f"[TEST] Headers: {dict(request.headers)}")
    
    try:
        # リクエストボディの最初の部分を読む
        body_preview = await request.body()
        logging.info(f"[TEST] Body preview (first 100 bytes): {body_preview[:100]}")
    except:
        pass
    
    return {
        "success": True,
        "message": "Connection test successful",
        "headers_received": dict(request.headers)
    }

@app.get("/proactive")
async def get_proactive_message():
    """自発的なメッセージを生成してJSONで返す"""
    try:
        proactive_text = "何してるデカッ！デカコーンへの道は24時間365日デカッ！"
        
        wav_data = robot.generate_wav_direct(proactive_text)
        if not wav_data:
            return {"success": False, "error": "音声生成に失敗しました"}
        
        with io.BytesIO(wav_data) as wav_io:
            data, sample_rate = sf.read(wav_io)
        
        resampled_data = librosa.resample(data, orig_sr=sample_rate, target_sr=16000)
        
        with io.BytesIO() as output_io:
            sf.write(output_io, resampled_data, 16000, format='wav')
            resampled_wav_data = output_io.getvalue()
        
        # WAVファイルを保存
        audio_id = str(uuid.uuid4())
        audio_filename = f"proactive_{audio_id}.wav"
        audio_path = static_dir / audio_filename
        
        with open(audio_path, "wb") as f:
            f.write(resampled_wav_data)
        
        return {
            "success": True,
            "message": proactive_text,
            "audio_path": f"/static/{audio_filename}"
        }
        
    except Exception as e:
        logging.error(f"処理エラー: {e}")
        return {"error": str(e)}


@app.get("/devices")
async def get_devices_dashboard():
    """デバイス管理ダッシュボード（HTMLページ）"""
    from fastapi.responses import HTMLResponse
    
    devices = robot.device_manager.get_active_devices(24 * 7) if robot else []
    stats = robot.device_manager.get_device_statistics() if robot else {}
    
    html_content = f"""
    <html>
    <head>
        <title>デカコーンハウス ESP32 デバイス管理</title>
        <meta charset="utf-8">
        <style>
            body {{ font-family: 'Helvetica Neue', Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
            .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            h1 {{ color: #333; border-bottom: 3px solid #4CAF50; padding-bottom: 10px; }}
            h2 {{ color: #555; margin-top: 30px; }}
            table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
            th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
            th {{ background-color: #4CAF50; color: white; font-weight: bold; }}
            tr:nth-child(even) {{ background-color: #f9f9f9; }}
            tr:hover {{ background-color: #f5f5f5; }}
            .stats {{ background-color: #e8f5e9; padding: 20px; margin: 20px 0; border-radius: 8px; display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; }}
            .stat-box {{ background: white; padding: 15px; border-radius: 5px; text-align: center; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
            .stat-number {{ font-size: 2em; font-weight: bold; color: #4CAF50; }}
            .stat-label {{ color: #666; margin-top: 5px; }}
            .dekako {{ color: #ff6b6b; font-weight: bold; }}
            .auto-update {{ text-align: right; color: #999; font-size: 0.9em; margin-top: 20px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 <span class="dekako">デカコーンハウス</span> ESP32 デバイス管理 🚀</h1>
            
            <div class="stats">
                <div class="stat-box">
                    <div class="stat-number">{stats.get('total_registered', 0)}</div>
                    <div class="stat-label">登録デバイス数</div>
                </div>
                <div class="stat-box">
                    <div class="stat-number">{stats.get('active_last_24h', 0)}</div>
                    <div class="stat-label">24時間以内のアクティブ</div>
                </div>
                <div class="stat-box">
                    <div class="stat-number">{stats.get('active_last_7d', 0)}</div>
                    <div class="stat-label">7日以内のアクティブ</div>
                </div>
                <div class="stat-box">
                    <div class="stat-number">{stats.get('total_connections', 0)}</div>
                    <div class="stat-label">総接続回数</div>
                </div>
            </div>
            
            <h2>📍 登録デバイス一覧</h2>
            <table>
                <thead>
                    <tr>
                        <th>デバイス名</th>
                        <th>MACアドレス</th>
                        <th>場所</th>
                        <th>最終接続</th>
                        <th>接続回数</th>
                        <th>初回登録</th>
                    </tr>
                </thead>
                <tbody>
    """
    
    for device in devices:
        last_seen = device.get('last_seen', 'N/A')
        hours_ago = device.get('hours_ago', 0)
        html_content += f"""
                    <tr>
                        <td><strong>{device.get('device_name', 'Unknown')}</strong></td>
                        <td><code>{device.get('mac_address', 'Unknown')}</code></td>
                        <td>{device.get('location', '未設定')}</td>
                        <td>{last_seen}<br><small>({hours_ago:.1f}時間前)</small></td>
                        <td style="text-align: center;">{device.get('total_connections', 0)}</td>
                        <td>{device.get('first_seen', 'N/A')}</td>
                    </tr>
        """
    
    if not devices:
        html_content += """
                    <tr>
                        <td colspan="6" style="text-align: center; color: #999;">まだデバイスが登録されていません</td>
                    </tr>
        """
    
    html_content += """
                </tbody>
            </table>
            
            <div class="auto-update">
                ⏱ このページは30秒ごとに自動更新されます
            </div>
        </div>
        
        <script>
            // 30秒ごとに自動更新
            setTimeout(() => location.reload(), 30000);
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)


@app.get("/devices/api")
async def get_devices_api():
    """デバイス情報をJSON形式で取得するAPI"""
    if not robot:
        return {"error": "Server not initialized"}
    
    return {
        "devices": robot.device_manager.devices,
        "active_devices": robot.device_manager.get_active_devices(24),
        "statistics": robot.device_manager.get_device_statistics(),
        "conversations": {
            device_id: robot.conversation_memory.get_device_summary(
                device_id.split('_')[0],  # MAC address
                device_id.split('_', 1)[1] if '_' in device_id else 'Unknown'  # Device name
            )
            for device_id in robot.conversation_memory.conversations.keys()
        } if hasattr(robot, 'conversation_memory') else {}
    }


if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("Buzz Robot with Memory Server")
    print("メモリ機能付き：デバイス管理・会話履歴対応")
    print("=" * 50)
    print("エンドポイント:")
    print("  POST /audio - 音声ファイルを受信し、応答を返す")
    print("  POST /audio_streaming - ストリーミング音声アップロード")
    print("  GET /proactive - 自発的メッセージを生成")
    print("  GET /devices - デバイス管理ダッシュボード")
    print("  GET /devices/api - デバイス情報API")
    print("-" * 50)
    uvicorn.run(app, host="0.0.0.0", port=8080)