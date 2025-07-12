#!/bin/bash
# cuDNNライブラリパスを修正

# PyTorchのcuDNNライブラリディレクトリを最優先に
export LD_LIBRARY_PATH=/usr/local/lib/python3.10/dist-packages/nvidia/cudnn/lib:$LD_LIBRARY_PATH

# シンボリックリンクを作成（PyTorchのcuDNNディレクトリ内）
CUDNN_DIR="/usr/local/lib/python3.10/dist-packages/nvidia/cudnn/lib"
cd $CUDNN_DIR

# 9.1.0と9.1のシンボリックリンクを作成
if [ -f "libcudnn_ops.so.9" ]; then
    sudo ln -sf libcudnn_ops.so.9 libcudnn_ops.so.9.1.0
    sudo ln -sf libcudnn_ops.so.9 libcudnn_ops.so.9.1
    echo "シンボリックリンク作成完了"
fi

ls -la libcudnn_ops.so*

echo "LD_LIBRARY_PATH: $LD_LIBRARY_PATH"