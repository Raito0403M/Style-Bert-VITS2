#!/bin/bash
# cuDNNライブラリパスを設定してサーバーを起動

export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH
echo "LD_LIBRARY_PATH: $LD_LIBRARY_PATH"

# libcudnn_ops.soのチェック
echo "Checking libcudnn_ops.so..."
ls -la /usr/lib/x86_64-linux-gnu/libcudnn_ops.so* | head -3

# サーバー起動
echo "Starting server with memory features..."
python buzz_robot_with_memory.py