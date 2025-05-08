import sounddevice as sd
import numpy as np
import soundfile as sf
import time

def test_microphone():
    """マイクの接続とテスト録音を行い、結果を保存する"""
    
    # 使用可能なオーディオデバイスを確認
    print("使用可能なオーディオデバイス:")
    print(sd.query_devices())
    
    # 録音設定
    sample_rate = 44100  # サンプリングレート
    channels = 1         # モノラル録音
    duration = 5         # 録音時間（秒）
    
    try:
        print(f"マイクテスト: {duration}秒間の録音を開始します...")
        print("何か話してください...")
        
        # 録音実行
        recording = sd.rec(
            int(duration * sample_rate),
            samplerate=sample_rate,
            channels=channels
        )
        
        # 進行状況の表示
        for i in range(duration):
            print(f"録音中: {i+1}/{duration}秒")
            time.sleep(1)
            
        sd.wait()  # 録音完了まで待機
        
        # 音量レベルの確認
        max_amplitude = np.max(np.abs(recording))
        print(f"最大音量レベル: {max_amplitude}")
        
        if max_amplitude < 0.01:
            print("警告: 音量が非常に小さいです。マイクが正しく接続されているか確認してください。")
        
        # 録音データの正規化
        normalized_recording = recording / np.max(np.abs(recording)) if max_amplitude > 0 else recording
        
        # WAVファイルとして保存
        filename = "mic_test_recording.wav"
        sf.write(filename, normalized_recording, sample_rate)
        print(f"録音が完了し、{filename}として保存されました")
        
        # 録音を再生して確認
        print("録音した音声を再生します...")
        sd.play(normalized_recording, sample_rate)
        sd.wait()
        print("再生完了")
        
        return True, filename
        
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        print("マイクの接続に問題があるか、オーディオ設定が正しくない可能性があります")
        return False, None

if __name__ == "__main__":
    success, filename = test_microphone()
    if success:
        print("マイクのテストが成功しました！Docker環境内でオーディオデバイスが正常に動作しています。")
    else:
        print("マイクのテストに失敗しました。設定を確認してください。")