#!/bin/bash
# cuDNNパスを修正してサーバーを起動

# PyTorchのcuDNNライブラリを最優先に
export LD_LIBRARY_PATH=/usr/local/lib/python3.10/dist-packages/nvidia/cudnn/lib:/usr/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH

echo "Starting server with fixed cuDNN path..."
echo "LD_LIBRARY_PATH: $LD_LIBRARY_PATH"

# 引数でファイルを指定できるように
if [ $# -eq 0 ]; then
    python buzz_robot_with_memory.py
else
    python $1
fi