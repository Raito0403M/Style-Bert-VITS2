from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
import io
import logging
import time
import uuid
from pathlib import Path
from fastapi.staticfiles import StaticFiles

# 既存のインポートを追加
from openai import OpenAI
import os
import soundfile as sf
import librosa
from dotenv import load_dotenv
from scipy.io import wavfile
from faster_whisper import WhisperModel
from style_bert_vits2.tts_model import TTSModel
from style_bert_vits2.constants import DEFAULT_SDP_RATIO, DEFAULT_NOISE, DEFAULT_NOISEW, Languages
from config import get_config

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%H:%M:%S'
)

app = FastAPI()

# 静的ファイル用ディレクトリ
static_dir = Path("static")
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# グローバル変数でロボットインスタンスを保持
robot = None

# BuzzLightyearRobotFixedクラスをここに含める（省略）
# ... 既存のBuzzLightyearRobotFixedクラスのコード ...

@app.post("/audio")
async def process_audio_esp32(request: Request):
    """ESP32からのChunked Encodingに対応したエンドポイント"""
    try:
        start_time = time.time()
        
        # ヘッダー情報をログ
        logging.info(f"Headers: {dict(request.headers)}")
        content_type = request.headers.get('content-type', '')
        transfer_encoding = request.headers.get('transfer-encoding', '')
        
        # リクエストボディを読み込む
        body = await request.body()
        logging.info(f"受信データサイズ: {len(body)} bytes")
        
        # マルチパートデータの処理
        audio_data = None
        
        if 'multipart/form-data' in content_type:
            # boundaryを抽出
            boundary = content_type.split('boundary=')[1] if 'boundary=' in content_type else None
            
            if boundary:
                # 簡易的なマルチパートパーサー
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
        
        logging.info(f"音声データ抽出: {len(audio_data)} bytes")
        
        # 以降は既存の処理と同じ
        if not robot:
            return JSONResponse(
                status_code=500,
                content={"success": False, "error": "サーバーが初期化されていません"}
            )
        
        # 音声認識
        recognition_start = time.time()
        user_speech = robot.listen(audio_data)
        if not user_speech:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "音声認識に失敗しました"}
            )
        logging.info(f"音声認識完了: {user_speech} ({time.time() - recognition_start:.3f}秒)")
        
        # 応答生成
        response_start = time.time()
        response_text = robot.respond(user_speech)
        logging.info(f"応答生成完了: {response_text} ({time.time() - response_start:.3f}秒)")
        
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
        
        logging.info(f"音声ファイル保存: {audio_filename}")
        logging.info(f"=== 総処理時間: {time.time() - start_time:.3f}秒 ===")
        
        # JSONレスポンス
        return JSONResponse(content={
            "success": True,
            "message": response_text,
            "audio_path": f"/static/{audio_filename}"
        })
        
    except Exception as e:
        logging.error(f"処理エラー: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

# 既存のGET /proactive エンドポイントもそのまま使用
@app.get("/proactive")
async def get_proactive_message():
    """自発的なメッセージを生成してJSONで返す"""
    # 既存のコードをそのまま使用
    pass

if __name__ == "__main__":
    import uvicorn
    print("ESP32互換サーバー")
    print("Chunked Encoding対応版")
    uvicorn.run(app, host="0.0.0.0", port=8080)