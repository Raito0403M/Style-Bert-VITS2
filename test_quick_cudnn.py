import os
print(f"LD_LIBRARY_PATH: {os.environ.get('LD_LIBRARY_PATH', 'Not set')}")

# シンボリックリンクの確認
import subprocess
result = subprocess.run(['ls', '-la', '/usr/local/lib/python3.10/dist-packages/nvidia/cudnn/lib/libcudnn_ops.so*'], 
                       capture_output=True, text=True, shell=True)
print("\nCuDNN files:")
print(result.stdout)

print("\nTesting import...")
try:
    from faster_whisper import WhisperModel
    print("✓ Whisper import successful")
except Exception as e:
    print(f"✗ Whisper import failed: {e}")
