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

class KumaRobot:
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
        # self.sample_rate = 44100  # サンプリングレート
        self.sample_rate = 16000  # サンプリングレート
        self.channels = 1         # モノラル録音
        self.duration = 10        # デフォルトの録音時間（秒）
        
        # 録音データ保存用のディレクトリ設定
        self.recording_dir = Path("recordings")
        self.recording_dir.mkdir(exist_ok=True)
        
        # Style-Bert-VITS2のモデル設定
        self.model_config = {
            "model_name": "jvnv-F1-jp",      # クマのモデル名
            "speaker": "jvnv-F1-jp",         # スピーカー名
            "style": "Neutral",              # スタイル
            "style_strength": 5.0,           # スタイル強度（0-5）
            "speed": 1.0,                    # 発話速度
            "noise": 0.6,                    # ノイズパラメータ
            "noise_w": 0.8,                  # ノイズWパラメータ
            "pitch": 1.0,                    # 声の高さ
            "energy": 1.0,                   # エネルギー
            "pause_between_texts": 0.5       # テキスト間の間隔
        }
    

    def listen(self, audio_path):
        """音声を文字に起こす（WhisperAPIを使用）"""
        try:
            with open(audio_path, "rb") as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="ja"
                )
            return transcript.text
        except Exception as e:
            print(f"音声認識エラー: {e}")
            return None

   
    def record_voice(self, max_duration=None, silence_threshold=0.03, speech_threshold=0.05, 
                    silence_duration=1.5, pre_speech_max_wait=5.0, min_record_time=1.0):
        """
        マイクから音声を録音し、話し始めと話し終わりを検出して自動的に開始・終了する
        
        Parameters:
        - max_duration: 最大録音時間（秒）。Noneの場合はself.durationを使用
        - silence_threshold: 無音と判断する音量の閾値（0.0〜1.0）
        - speech_threshold: 発話開始と判断する音量の閾値（0.0〜1.0）
        - silence_duration: この秒数だけ無音が続いたら録音終了
        - pre_speech_max_wait: 話し始めるのを待つ最大時間（秒）
        - min_record_time: 最低限録音する時間（秒）- 録音が短すぎるのを防ぐ
        """
        from typing import Optional, List
        import numpy.typing as npt
        
        if max_duration is None:
            max_duration = self.duration
            
        try:
            print(f"録音の準備をしています（最大{max_duration}秒間）...")
            print("話し始めるのを待っています...")
            
            # コールバック関数内でのクロージャ問題を解決するためのクラス
            class CallbackState:
                def __init__(self):
                    self.frames: List[npt.NDArray[np.float64]] = []  # 録音データフレーム
                    self.silent_frames: int = 0  # 連続無音フレーム数
                    self.speech_detected: bool = False  # 発話検出フラグ
                    self.recording_started_at: Optional[float] = None  # 録音開始時間
                    
            state = CallbackState()
            
            # コールバック関数で録音データを処理
            def callback(indata, frame_count, time_info, status):
                if status:
                    print(f"録音ステータス: {status}")
                
                # 音量レベルの確認
                volume = np.max(np.abs(indata))
                
                # 話し始めの検出
                if not state.speech_detected and volume > speech_threshold:
                    state.speech_detected = True
                    state.recording_started_at = time.time()
                    print("話し始めを検出しました。録音を開始します...")
                
                # 発話が検出された場合のみフレームを保存
                if state.speech_detected:
                    # データをフレームリストに追加
                    state.frames.append(indata.copy())
                    
                    # 無音検出
                    if volume < silence_threshold:
                        state.silent_frames += 1
                    else:
                        state.silent_frames = 0
            
            # ストリーミング録音セットアップ
            stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                callback=callback,
                blocksize=1024
            )
            
            # 録音開始
            stream.start()
            
            # 録音の進行状況をモニタリング
            start_time = time.time()
            recording_duration = 0
            required_silent_frames = int(silence_duration * self.sample_rate / 1024)
            
            try:
                # 1. 話し始めを待つフェーズ
                while not state.speech_detected:
                    # 話し始め待ち時間の上限に達したら終了
                    if time.time() - start_time > pre_speech_max_wait:
                        print("話し始めを検出できませんでした。")
                        return None
                    time.sleep(0.1)
                
                # 2. 録音進行と話し終わり検出フェーズ
                while True:
                    # 現在の録音時間を計算
                    if state.recording_started_at is not None:
                        recording_duration = time.time() - state.recording_started_at
                    
                    # 最大録音時間に達したら終了
                    if recording_duration >= max_duration:
                        print("最大録音時間に達しました。")
                        break
                    
                    # 最低録音時間を超えている場合のみ、無音検出による終了を有効にする
                    if recording_duration > min_record_time:
                        # 無音時間のチェック
                        if state.silent_frames >= required_silent_frames:
                            print("会話の終了を検出しました。")
                            break
                    
                    # 少し待機
                    time.sleep(0.1)
            finally:
                stream.stop()
                stream.close()
            
            # 録音データの結合と正規化
            if not state.frames:
                print("録音データがありません。")
                return None
            
            recording = np.vstack(state.frames)
            
            # 音量が0の場合は正規化しない
            if np.max(np.abs(recording)) > 0:
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


    def respond(self, user_message):
        """ユーザーの発話に対して応答を生成（GPT-4oを使用）"""
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": """あなたは教育用のコミュニケーションロボットです。
                    以下の方針で会話してください：
                    
                    - 優しく穏やかなキャラクターとして話す
                    - 森や自然に関する表現を好んで使う
                    - のんびりとした口調で話す
                    - 親しみやすく、温かみのある会話をする
                    - シンプルで分かりやすい表現を心がける
                    - 丁寧だが堅苦しくない言葉遣いをする
                    - 相手を「お友達」「みなさん」などと呼ぶこともある
                    - 相手の発言に対して共感と優しさを示す
                    
                    - 例: 「それは素敵ですね！」「お友達、どう思いますか？」など

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
            return "ごめんなさい、ちょっと考えるのに時間がかかっています。もう一度お願いできますか？"

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

    def speak_with_sbv2(self, text, filename):
        """Style-Bert-VITS2を使ってテキストを音声に変換して再生する"""
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
                # 一時的に44100Hzのファイルを保存
                temp_output_path = self.output_dir / f"{filename}_44100.wav"
                with open(temp_output_path, "wb") as f:
                    f.write(response.content)
                
                # 最終的な出力先パス（16000Hz用）
                output_path = self.output_dir / f"{filename}.wav"
                
                # 44100Hzから16000Hzにリサンプリング
                data, sample_rate = sf.read(str(temp_output_path))
                print(f"元のサンプルレート: {sample_rate}Hz")
                
                # リサンプリング
                resampled_data = librosa.resample(data, orig_sr=sample_rate, target_sr=16000)
                
                # 16000Hzのファイルを保存
                sf.write(str(output_path), resampled_data, 16000)
                
                print(f"音声を16000Hzにリサンプリングして保存しました: {output_path}")
                
                # 一時ファイルを削除
                if temp_output_path.exists():
                    temp_output_path.unlink()
                
                return str(output_path)
            else:
                print(f"音声生成APIエラー: {response.status_code}, {response.text}")
                return self.speak_with_openai(text, filename)  # フォールバックとしてOpenAI TTS APIを使用
                
        except Exception as e:
            print(f"Style-Bert-VITS2音声生成エラー: {e}")
            return self.speak_with_openai(text, filename)  # フォールバックとしてOpenAI TTS APIを使用

    def speak_with_openai(self, text, filename):
        """OpenAI TTS APIを使ってテキストを音声に変換して再生する（フォールバック用）"""
        try:
            response = self.client.audio.speech.create(
                model="tts-1",
                voice="nova",  # クマに合う優しい声
                input=text,
            )
            
            # 音声ファイルを保存
            output_path = self.output_dir / f"{filename}.mp3"
            
            # 非推奨のstream_to_fileの代わりに新しい方法を使用
            with open(str(output_path), "wb") as file:
                for chunk in response.iter_bytes():
                    file.write(chunk)
                    
            print(f"音声を保存しました (OpenAI TTS): {output_path}")
            
            # 音声を再生
            # print("\n応答を再生します...")
            # time.sleep(1)  # 少し間を置いてから再生
            # self.play_audio(str(output_path))
            
            return str(output_path)
            
        except Exception as e:
            print(f"OpenAI TTS音声生成エラー: {e}")
            return None



    def interactive_session(self):
        """インタラクティブな会話セッションを実行（無音時に自発的に話しかける機能と相槌機能付き）"""
        import threading
        
        session_count = 0
        last_interaction_time = time.time()
        idle_check_interval = 5  # 無音検出のチェック間隔（秒）
        idle_threshold = 30      # この秒数以上無音が続くと自発的に話しかける
        
        # 相槌のリスト
        acknowledgements = [
            "うーん、考えているところだよ。",
            "なるほどね。ちょっと考えさせてね...",
            "それは面白いね。少し考えるね。",
            "聞こえたよ、お友達。考えているところだよ。",
            "うんうん、わかるよ。ちょっと待ってね...",
            "なるほど。クマの知恵を絞って考えているよ。"
        ]
        
        print("クマとの対話を開始します。Ctrl+Cで終了できます。")
        print("「こんにちは、お友達！」")
        
        # 初回の挨拶
        greeting = "こんにちは、お友達！今日はどんなお話をしようかな？"
        self.speak_with_sbv2(greeting, f"kuma_greeting")
        
        try:
            while True:
                # 現在の時間を取得
                current_time = time.time()
                
                # 無音時間の検出
                idle_time = current_time - last_interaction_time
                
                # 無音時間が閾値を超えたら自発的に話しかける
                if idle_time >= idle_threshold:
                    session_count += 1
                    print("\n=== 長時間の無音を検出しました ===")
                    
                    # 自発的な発話を生成
                    proactive_message = self.generate_proactive_message()
                    print(f"クマ (自発的): {proactive_message}")
                    
                    # 音声出力と再生
                    output_filename = f"kuma_proactive_{session_count}"
                    self.speak_with_sbv2(proactive_message, output_filename)
                    
                    # 最終交流時間を更新
                    last_interaction_time = time.time()
                    
                    # 少し待ってからユーザーの反応を待つ
                    time.sleep(3)
                    continue
                
                # 通常の会話フロー
                print("\n=== 新しい対話セッション ===")
                
                # マイクから録音（無音検出機能付き）
                audio_path = self.record_voice()
                if not audio_path:
                    # 録音に失敗した場合、少し待ってから再試行
                    time.sleep(idle_check_interval)
                    continue
                
                # 音声認識
                user_speech = self.listen(audio_path)
                if not user_speech:
                    # 音声認識に失敗した場合、少し待ってから再試行
                    time.sleep(idle_check_interval)
                    continue
                    
                print(f"\nユーザー: {user_speech}")
                
                # セッションカウントを増やす
                session_count += 1
                
                # ランダムな相槌を選択
                import random
                acknowledgement = random.choice(acknowledgements)
                
                # 相槌用のファイル名
                ack_filename = f"kuma_ack_{session_count}"
                
                # LLMの応答を格納する変数
                llm_response = [""]  # リストにすることで、スレッド内から値を変更可能にする
                
                # バックグラウンドでLLM応答を取得するスレッド
                def get_llm_response():
                    response_text = self.respond(user_speech)
                    if response_text is not None:
                        llm_response[0] = response_text
                    else:
                        llm_response[0] = "ごめんなさい、うまく考えられませんでした。もう一度お話してくれる？"
                
                # スレッドを開始
                response_thread = threading.Thread(target=get_llm_response)
                response_thread.start()
                
                # 相槌を発する
                print(f"クマ (相槌): {acknowledgement}")
                self.speak_with_sbv2(acknowledgement, ack_filename)
                
                # LLM応答スレッドの完了を待つ
                response_thread.join()
                
                # LLMの応答を表示
                response = llm_response[0]
                print(f"クマ: {response}")
                
                # 音声出力と再生
                output_filename = f"kuma_response_{session_count}"
                self.speak_with_sbv2(response, output_filename)
                
                # 最終交流時間を更新
                last_interaction_time = time.time()
                
                # 次のセッションまで少し間を置く
                time.sleep(2)
                
        except KeyboardInterrupt:
            print("\n\n森に帰ります。さようなら、お友達！またね！")

    def generate_proactive_message(self):
        """無音時に自発的に話しかけるためのメッセージを生成"""
        try:
            # 会話を始めるためのプロンプト
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": """あなたはクマのコミュニケーションロボットです。
                    長時間ユーザーとの会話がない状況で、自発的に話しかけるメッセージを生成してください。
                    以下の方針で発話してください：
                    
                    - 優しいクマのキャラクターとして話す
                    - ユーザーの興味を引くような質問や話題を提案する
                    - ダンディーさを残す
                    - 会話を再開するきっかけになるような親しみやすい一言を生成する
                    - 1-2文の短めのメッセージにする
                    
                    クマの代表的なプロアクティブな発話例：
                    - 「お友達、まだそこにいるのかな？」
                    - 「食事をしながら考えていたんだけど、何か話したいことはある？」
                    """
                    }
                ],
                temperature=0.8,
                max_tokens=300
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"自発的メッセージ生成エラー: {e}")
            return "こんにちは、お友達。クマだよ。まだそこにいるかな？お話ししようよ。"


if __name__ == "__main__":
    # KumaRobotのインスタンスを作成
    robot = KumaRobot()
    
    # インタラクティブセッションをクラスメソッドとして実行
    robot.interactive_session()
