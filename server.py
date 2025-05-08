
from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import os
from pathlib import Path
import time
import uvicorn
from dotenv import load_dotenv

# BuzzLightyearRobotクラスをインポート
from buzz_robot import BuzzLightyearRobot

# 環境変数の読み込み
load_dotenv()

app = FastAPI(title="Buzz Lightyear Robot API", 
              description="バズ・ライトイヤーのコミュニケーションロボットAPI")

# CORSミドルウェアを追加
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # すべてのオリジンを許可
    allow_credentials=True,
    allow_methods=["*"],  # すべてのメソッドを許可
    allow_headers=["*"],  # すべてのヘッダーを許可
)

# グローバルなロボットインスタンスを作成
robot = BuzzLightyearRobot()

# 出力ディレクトリの確認
output_dir = Path("output_audio")
output_dir.mkdir(exist_ok=True)

# 一時ファイル用のディレクトリ
temp_dir = Path("temp_audio")
temp_dir.mkdir(exist_ok=True)

# 音声アップロード用のディレクトリ
upload_dir = Path("temp_audio/uploads")
upload_dir.mkdir(exist_ok=True)

# 最新の音声レスポンスへのパス
latest_response_path = None

# リクエスト用のモデル
class TextRequest(BaseModel):
    text: str

class ResponseData(BaseModel):
    success: bool
    message: Optional[str] = None
    audio_path: Optional[str] = None

@app.get("/", response_class=HTMLResponse)
async def root():
    """ルートページ - 音声アップロードのテストフォームを表示"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>バズ・ライトイヤーのコミュニケーションロボットAPI</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
            h1 { color: #333; }
            form { background: #f5f5f5; padding: 20px; border-radius: 5px; }
            button { background: #4CAF50; color: white; padding: 10px 15px; border: none; border-radius: 4px; cursor: pointer; }
            button:hover { background: #45a049; }
            .response { margin-top: 20px; padding: 15px; background: #e9f7ef; border-radius: 5px; display: none; }
            audio { margin-top: 10px; width: 100%; }
        </style>
    </head>
    <body>
        <h1>バズ・ライトイヤーのコミュニケーションロボットAPI</h1>
        <p>音声をアップロードして、バズライトイヤーからの応答を受け取ります。</p>
        
        <form id="uploadForm" enctype="multipart/form-data">
            <h2>音声アップロード</h2>
            <p>
                <input type="file" id="audioFile" name="file" accept="audio/*" required>
            </p>
            <button type="submit">送信</button>
        </form>
        
        <div id="response" class="response">
            <h2>バズライトイヤーの応答:</h2>
            <p id="responseText"></p>
            <audio id="responseAudio" controls></audio>
        </div>
        
        <script>
            document.getElementById('uploadForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                
                const fileInput = document.getElementById('audioFile');
                const file = fileInput.files[0];
                
                if (!file) {
                    alert('ファイルを選択してください');
                    return;
                }
                
                const formData = new FormData();
                formData.append('file', file);
                
                try {
                    const response = await fetch('/upload_audio', {
                        method: 'POST',
                        body: formData
                    });
                    
                    const result = await response.json();
                    
                    if (result.success) {
                        document.getElementById('responseText').textContent = result.message;
                        document.getElementById('responseAudio').src = result.audio_path;
                        document.getElementById('response').style.display = 'block';
                    } else {
                        alert('エラー: ' + result.message);
                    }
                } catch (error) {
                    console.error('エラー:', error);
                    alert('リクエスト中にエラーが発生しました: ' + error.message);
                }
            });
        </script>
    </body>
    </html>
    """
    return html_content

@app.post("/respond", response_model=ResponseData)
async def respond_to_text(request: TextRequest, background_tasks: BackgroundTasks):
    """テキストからバズライトイヤーの応答を生成し、音声ファイルのパスを返す"""
    try:
        # GPT-4oを使って応答を生成
        response_text = robot.respond(request.text)
        
        # タイムスタンプベースのファイル名を生成
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"buzz_response_{timestamp}"
        
        # Style-Bert-VITS2 APIを使って音声を生成
        audio_path = robot.speak_with_sbv2(response_text, filename)
        
        if audio_path:
            # 絶対パスを相対URLに変換
            audio_url = f"/audio/{os.path.basename(audio_path)}"
            
            # 最新の応答パスを更新
            global latest_response_path
            latest_response_path = audio_path
            
            return ResponseData(
                success=True,
                message=response_text,
                audio_path=audio_url
            )
        else:
            return ResponseData(
                success=False,
                message="音声の生成に失敗しました。"
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"エラーが発生しました: {str(e)}")

@app.get("/audio/{filename}")
async def get_audio(filename: str):
    """音声ファイルをダウンロードするエンドポイント"""
    file_path = output_dir / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="音声ファイルが見つかりません")
    return FileResponse(path=file_path, media_type="audio/wav", filename=filename)

@app.get("/generate_proactive", response_model=ResponseData)
async def generate_proactive():
    """自発的なメッセージを生成して返す"""
    try:
        # 自発的なメッセージを生成
        proactive_message = robot.generate_proactive_message()
        
        # タイムスタンプベースのファイル名を生成
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"buzz_proactive_{timestamp}"
        
        # Style-Bert-VITS2 APIを使って音声を生成
        audio_path = robot.speak_with_sbv2(proactive_message, filename)
        
        if audio_path:
            # 絶対パスを相対URLに変換
            audio_url = f"/audio/{os.path.basename(audio_path)}"
            
            # 最新の応答パスを更新
            global latest_response_path
            latest_response_path = audio_path
            
            return ResponseData(
                success=True,
                message=proactive_message,
                audio_path=audio_url
            )
        else:
            return ResponseData(
                success=False,
                message="音声の生成に失敗しました。"
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"エラーが発生しました: {str(e)}")

@app.get("/debug")
async def debug_info():
    """デバッグ情報を表示するエンドポイント"""
    return JSONResponse({
        "api_status": "running",
        "directories": {
            "output_dir": str(output_dir),
            "temp_dir": str(temp_dir),
            "upload_dir": str(upload_dir)
        },
        "latest_response": str(latest_response_path) if latest_response_path else None,
        "robot_initialized": robot is not None
    })

@app.post("/upload_audio", response_model=ResponseData)
async def upload_audio(file: UploadFile = File()):
    """音声ファイルをアップロードして文字起こしし、応答を生成する"""
    try:
        # ファイルが提供されているか確認
        if not file:
            print("エラー: 音声ファイルが提供されていません。")
            return ResponseData(
                success=False,
                message="音声ファイルが提供されていません。"
            )
        
        # リクエストの詳細情報をログ出力
        print("=========== アップロードファイル詳細情報 ===========")
        print(f"ファイル名: {file.filename}")
        print(f"コンテンツタイプ: {file.content_type}")
        
        # リクエストヘッダー情報
        headers = getattr(file, "headers", {})
        for header_name, header_value in headers.items():
            print(f"ヘッダー: {header_name} = {header_value}")
        
        # アップロードされたファイルを一時保存
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        temp_file_path = upload_dir / f"upload_{timestamp}.wav"
        
        # ファイルコンテンツを読み込む
        content = await file.read()
        
        # ファイルサイズをチェック
        file_size = len(content)
        print(f"ファイルサイズ: {file_size} バイト")
        
        if file_size < 44:  # WAVヘッダーの最小サイズ
            print("エラー: ファイルサイズが小さすぎます（WAVヘッダーより小さい）")
            return ResponseData(
                success=False,
                message="無効な音声ファイル: ファイルサイズが小さすぎます"
            )
        
        # WAVヘッダーを解析（最初の44バイト）
        try:
            header = content[:44]
            # RIFF識別子をチェック
            if header[:4].decode('ascii', errors='ignore') != 'RIFF':
                print(f"警告: RIFFヘッダーが見つかりません。最初の4バイト: {header[:4]}")
            
            # WAVEフォーマットをチェック
            if header[8:12].decode('ascii', errors='ignore') != 'WAVE':
                print(f"警告: WAVEフォーマットが見つかりません。8-12バイト: {header[8:12]}")
            
            # fmt チャンクをチェック
            if header[12:16].decode('ascii', errors='ignore') != 'fmt ':
                print(f"警告: fmtチャンクが見つかりません。12-16バイト: {header[12:16]}")
            
            # サンプルレート (バイト 24-27)
            sample_rate = int.from_bytes(header[24:28], byteorder='little')
            
            # チャンネル数 (バイト 22-23)
            channels = int.from_bytes(header[22:24], byteorder='little')
            
            # ビット深度 (バイト 34-35)
            bits_per_sample = int.from_bytes(header[34:36], byteorder='little')
            
            # オーディオフォーマット (バイト 20-21)
            audio_format = int.from_bytes(header[20:22], byteorder='little')
            
            print(f"WAVヘッダー解析: サンプルレート={sample_rate} Hz, チャンネル数={channels}, ビット数={bits_per_sample}, フォーマット={audio_format}")
            
            # フォーマット検証
            if audio_format != 1:
                print(f"警告: 非PCMフォーマット ({audio_format}) が検出されました。PCM(1)が期待されています。")
            
            if sample_rate != 16000:
                print(f"警告: サンプルレートが16000Hzではありません ({sample_rate}Hz)")
            
            if channels != 1:
                print(f"警告: モノラルではありません (チャンネル数: {channels})")
            
            if bits_per_sample != 16:
                print(f"警告: 16ビットサンプルではありません ({bits_per_sample}ビット)")
                
            # data チャンクをチェック (通常は36バイト目以降に存在)
            # WAVファイルによっては追加メタデータがあるため、dataチャンクを検索
            data_chunk_found = False
            for i in range(36, min(100, file_size - 4)):  # 最初の100バイト内を検索
                if content[i:i+4].decode('ascii', errors='ignore') == 'data':
                    data_chunk_found = True
                    data_size = int.from_bytes(content[i+4:i+8], byteorder='little')
                    print(f"dataチャンク: 位置={i}, サイズ={data_size} バイト")
                    break
            
            if not data_chunk_found:
                print("警告: dataチャンクが見つかりません")
            
        except Exception as e:
            print(f"WAVヘッダー解析エラー: {e}")
            # ヘッダーのHEXダンプを出力（デバッグ用）
            print("ヘッダーHEXダンプ:")
            for i in range(0, min(44, file_size), 4):
                hex_data = ' '.join([f"{b:02x}" for b in header[i:i+4]])
                ascii_data = ''.join([chr(b) if 32 <= b <= 126 else '.' for b in header[i:i+4]])
                print(f"{i:04d}: {hex_data}  {ascii_data}")
        
        # ファイルを保存
        with open(temp_file_path, "wb") as buffer:
            buffer.write(content)
        
        print(f"音声ファイルを保存しました: {temp_file_path}")
        
        # ファイルポインタを先頭に戻す
        await file.seek(0)
        
        # 音声を文字起こし
        transcribed_text = robot.listen(str(temp_file_path))
        
        if not transcribed_text:
            return ResponseData(
                success=False,
                message="音声の文字起こしに失敗しました。"
            )
        
        print(f"文字起こし結果: {transcribed_text}")
        
        # 応答を生成
        response_text = robot.respond(transcribed_text)
        
        # タイムスタンプベースのファイル名を生成
        filename = f"buzz_response_{timestamp}"
        
        # Style-Bert-VITS2 APIを使って音声を生成
        audio_path = robot.speak_with_sbv2(response_text, filename)
        
        if audio_path:
            # 絶対パスを相対URLに変換
            audio_url = f"/audio/{os.path.basename(audio_path)}"
            
            # 最新の応答パスを更新
            global latest_response_path
            latest_response_path = audio_path
            
            return ResponseData(
                success=True,
                message=response_text,
                audio_path=audio_url
            )
        else:
            return ResponseData(
                success=False,
                message="音声の生成に失敗しました。"
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"エラーが発生しました: {str(e)}")

@app.get("/latest_response", response_model=ResponseData)
async def get_latest_response():
    """最新の生成された応答の情報を取得する"""
    global latest_response_path
    
    if latest_response_path and os.path.exists(latest_response_path):
        # 最新の応答がある場合
        filename = os.path.basename(latest_response_path)
        audio_url = f"/audio/{filename}"
        
        return ResponseData(
            success=True,
            message="最新の応答が利用可能です",
            audio_path=audio_url
        )
    else:
        # 最新の応答がない場合
        return ResponseData(
            success=False,
            message="最近の応答はありません"
        )

if __name__ == "__main__":
    # APIサーバーを起動
    uvicorn.run(app, host="0.0.0.0", port=8080)

