#!/bin/bash
# CUDA モジュールの遅延ロードを有効にして起動

export CUDA_MODULE_LOADING=LAZY
export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH

echo "CUDA_MODULE_LOADING: $CUDA_MODULE_LOADING"
echo "LD_LIBRARY_PATH: $LD_LIBRARY_PATH"

echo "Starting server with CUDA lazy loading..."
python buzz_robot_fastest_fixed.py