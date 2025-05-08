import sounddevice as sd
import numpy as np
import soundfile as sf
import time

def test_headset_mic():
    """G535ヘッドセットマイクを明示的にテスト"""
    # すべてのデバイスを表示
    devices = sd.query_devices()
    print("利用可能なすべてのオーディオデバイス:")
    for i, dev in enumerate(devices):
        print(f"{i}: {dev['name']} (入力: {dev['max_input_channels']}, 出力: {dev['max_output_channels']})")
    
    # G535ヘッドセットを探す
    headset_idx = None
    for i, dev in enumerate(devices):
        if 'G535' in dev['name'] or 'Headset' in dev['name'] or ('USB Audio' in dev['name'] and dev['max_input_channels'] > 0):
            headset_idx = i
            break
    
    if headset_idx is None:
        print("ヘッドセットが見つかりませんでした。カード2を指定します。")
        # カード2に対応するデバイスを探す
        for i, dev in enumerate(devices):
            if ('C2D0' in dev['name'] or 'card 2' in dev.get('name', '').lower()) and dev['max_input_channels'] > 0:
                headset_idx = i
                break
    
    if headset_idx is None:
        # 入力可能なデバイスをすべて試す
        input_devices = [i for i, dev in enumerate(devices) if dev['max_input_channels'] > 0]
        print(f"入力可能なデバイス: {input_devices}")
        if input_devices:
            headset_idx = input_devices[0]
        else:
            print("入力可能なデバイスが見つかりませんでした")
            return
    
    print(f"\n選択されたデバイス {headset_idx}: {devices[headset_idx]['name']}")
    
    # 録音パラメータ
    sample_rate = 44100
    channels = 1
    duration = 5
    
    print(f"\n{duration}秒間の録音を開始します。何か話してください...")
    
    # 録音
    recording = sd.rec(
        int(duration * sample_rate),
        samplerate=sample_rate,
        channels=channels,
        device=headset_idx
    )
    
    # 進行状況表示
    for i in range(duration):
        print(f"録音中: {i+1}/{duration}秒")
        time.sleep(1)
    
    sd.wait()  # 録音完了まで待機
    
    # 録音結果の分析
    max_amplitude = np.max(np.abs(recording))
    print(f"\n最大音量レベル: {max_amplitude}")
    
    # 結果の保存と再生
    if max_amplitude > 0.01:
        print("👍 音声が録音されました")
        filename = "headset_mic_test.wav"
        sf.write(filename, recording, sample_rate)
        print(f"録音を {filename} として保存しました")
        
        print("\n録音した音声を再生します...")
        sd.play(recording, sample_rate)
        sd.wait()
        print("再生完了")
    else:
        print("👎 録音レベルが非常に低いです。マイクが正しく機能していない可能性があります")

if __name__ == "__main__":
    test_headset_mic()