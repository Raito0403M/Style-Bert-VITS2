from openai import OpenAI
from pathlib import Path
import os
import requests
import time
import numpy as np
import sounddevice as sd
import soundfile as sf
from dotenv import load_dotenv

class BuzzLightyearRobot:
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
        self.sample_rate = 44100  # サンプリングレート
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

    # def record_voice(self, max_duration=None, silence_threshold=0.03, silence_duration=1.5):
    #     """
    #     マイクから音声を録音し、無音検出で自動的に終了する
        
    #     Parameters:
    #     - max_duration: 最大録音時間（秒）。Noneの場合はself.durationを使用
    #     - silence_threshold: 無音と判断する音量の閾値（0.0〜1.0）
    #     - silence_duration: この秒数だけ無音が続いたら録音終了
    #     """
    #     if max_duration is None:
    #         max_duration = self.duration
            
    #     try:
    #         print(f"録音を開始します（最大{max_duration}秒間）...")
    #         print("話し終わったら自動的に録音を終了します...")
            
    #         # 音声データを格納するリスト
    #         frames = []
    #         silent_frames = 0
    #         required_silent_frames = int(silence_duration * self.sample_rate / 1024)  # 1024はフレームサイズ
            
    #         # コールバック関数内でのクロージャ問題を解決するためのクラス
    #         class CallbackState:
    #             def __init__(self):
    #                 self.frames = []
    #                 self.silent_frames = 0
                    
    #         state = CallbackState()
            
    #         # コールバック関数で録音データを処理
    #         def callback(indata, frame_count, time_info, status):
    #             if status:
    #                 print(f"録音ステータス: {status}")
                
    #             # データをフレームリストに追加
    #             state.frames.append(indata.copy())
                
    #             # 無音検出（音量レベルの確認）
    #             volume = np.max(np.abs(indata))
    #             if volume < silence_threshold:
    #                 state.silent_frames += 1
    #             else:
    #                 state.silent_frames = 0
            
    #         # ストリーミング録音セットアップ
    #         stream = sd.InputStream(
    #             samplerate=self.sample_rate,
    #             channels=self.channels,
    #             callback=callback,
    #             blocksize=1024
    #         )
            
    #         # 録音開始
    #         stream.start()
            
    #         # 録音の進行状況をモニタリング
    #         start_time = time.time()
    #         try:
    #             while True:
    #                 # 経過時間のチェック
    #                 elapsed_time = time.time() - start_time
    #                 if elapsed_time >= max_duration:
    #                     print("最大録音時間に達しました。")
    #                     break
                    
    #                 # 無音時間のチェック
    #                 if state.silent_frames >= required_silent_frames:
    #                     print("会話の終了を検出しました。")
    #                     break
                    
    #                 # 少し待機
    #                 time.sleep(0.1)
    #         finally:
    #             stream.stop()
    #             stream.close()
            
    #         # 録音データの結合と正規化
    #         if not state.frames:
    #             print("録音データがありません。")
    #             return None
            
    #         recording = np.vstack(state.frames)
            
    #         # 音量が0の場合は正規化しない
    #         if np.max(np.abs(recording)) > 0:
    #             recording = recording / np.max(np.abs(recording))
            
    #         # ファイル名の生成（タイムスタンプ付き）
    #         timestamp = time.strftime("%Y%m%d_%H%M%S")
    #         filename = self.recording_dir / f"recording_{timestamp}.wav"
            
    #         # WAVファイルとして保存
    #         sf.write(str(filename), recording, self.sample_rate)
    #         print(f"録音を保存しました: {filename}")
            
    #         return str(filename)
            
    #     except Exception as e:
    #         print(f"録音エラー: {e}")
    #         return None
        
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
                max_tokens=150
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"応答生成エラー: {e}")
            return "スターコマンド、通信に問題が発生しています。もう一度お願いします。"

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
                output_path = self.output_dir / f"{filename}.wav"
                with open(output_path, "wb") as f:
                    f.write(response.content)
                
                print(f"音声を保存しました: {output_path}")
                
                # 音声を再生
                print("\n応答を再生します...")
                time.sleep(1)  # 少し間を置いてから再生
                self.play_audio(str(output_path))
                
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
                voice="onyx",  # バズライトイヤーに近い男性的な声
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
            print("\n応答を再生します...")
            time.sleep(1)  # 少し間を置いてから再生
            self.play_audio(str(output_path))
            
            return str(output_path)
            
        except Exception as e:
            print(f"OpenAI TTS音声生成エラー: {e}")
            return None

    def interactive_session(self):
        """インタラクティブな会話セッションを実行（無音時に自発的に話しかける機能付き）"""
        session_count = 0
        last_interaction_time = time.time()
        idle_check_interval = 5  # 無音検出のチェック間隔（秒）
        idle_threshold = 30      # この秒数以上無音が続くと自発的に話しかける
        
        print("バズ・ライトイヤーとの対話を開始します。Ctrl+Cで終了できます。")
        print("「無限の彼方へ、さあ行くぞ！」")
        
        # 初回の挨拶
        greeting = "こんにちは、宇宙飛行士！バズライトイヤーだ。何か手伝えることはあるかな？"
        self.speak_with_sbv2(greeting, f"buzz_greeting")
        
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
                    print(f"バズ (自発的): {proactive_message}")
                    
                    # 音声出力と再生
                    output_filename = f"buzz_proactive_{session_count}"
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
                start_time = time.time()
                # 音声認識
                user_speech = self.listen(audio_path)
                recognize_time = time.time() - start_time
                print(f"音声認識時間: {recognize_time:.2f}秒")
                if not user_speech:
                    # 音声認識に失敗した場合、少し待ってから再試行
                    time.sleep(idle_check_interval)
                    continue
                    
                print(f"\nユーザー: {user_speech}")
                respond_time = time.time()


                # 応答生成
                session_count += 1
                response = self.respond(user_speech)
                print(f"バズ: {response}")
                # 応答時間を計測
                response_time = time.time() - respond_time
                print(f"応答時間: {response_time:.2f}秒")
                # 音声出力と再生
                output_filename = f"buzz_response_{session_count}"
                self.speak_with_sbv2(response, output_filename)
                # 応答時間を計測
                output_time = time.time() - response_time
                print(f"音声出力時間: {output_time:.2f}秒")
                # 最終交流時間を更新
                last_interaction_time = time.time()
                
                # 次のセッションまで少し間を置く
                time.sleep(2)
                
        except KeyboardInterrupt:
            print("\n\nスターコマンドに帰還します。さようなら、宇宙飛行士！")

    def generate_proactive_message(self):
        """無音時に自発的に話しかけるためのメッセージを生成"""
        try:
            # 会話を始めるためのプロンプト
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
                max_tokens=100
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"自発的メッセージ生成エラー: {e}")
            return "スターコマンド、こちらバズ・ライトイヤー。通信状態は良好ですか？応答をお願いします。"

# def interactive_session():
#     """インタラクティブな会話セッションを実行"""
#     robot = BuzzLightyearRobot()
    
#     print("バズ・ライトイヤーとの対話を開始します。Ctrl+Cで終了できます。")
#     print("「無限の彼方へ、さあ行くぞ！」")
#     session_count = 0
    
#     try:
#         while True:
#             session_count += 1
#             print("\n=== 新しい対話セッション ===")
            
#             # マイクから録音
#             audio_path = robot.record_voice()
#             if not audio_path:
#                 continue
            
#             # 音声認識
#             user_speech = robot.listen(audio_path)
#             if not user_speech:
#                 continue
#             print(f"\nユーザー: {user_speech}")
            
#             # 応答生成
#             response = robot.respond(user_speech)
#             print(f"バズ: {response}")
            
#             # 音声出力と再生
#             output_filename = f"buzz_response_{session_count}"
#             # Style-Bert-VITS2が利用可能な場合はそちらを使用
#             robot.speak_with_sbv2(response, output_filename)
            
#             # 次のセッションまで少し間を置く
#             time.sleep(2)
            
#     except KeyboardInterrupt:
#         print("\n\nスターコマンドに帰還します。さようなら、宇宙飛行士！")




if __name__ == "__main__":
    # BuzzLightyearRobotのインスタンスを作成
    robot = BuzzLightyearRobot()
    
    # インタラクティブセッションをクラスメソッドとして実行
    robot.interactive_session()
