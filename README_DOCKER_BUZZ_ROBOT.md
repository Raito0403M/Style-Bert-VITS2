# Buzz Robot Docker環境

このDockerイメージは、Style-Bert-VITS2のBuzz Robot（デカ子）サーバーをcuDNNエラーなしで動作させるための環境です。

## 特徴

- CUDA 11.8 + cuDNN 9.1.0 (PyTorchと互換性のあるバージョン)
- Whisper（音声認識）とTTS（音声合成）の両方が正常動作
- デバイス管理と会話記憶機能付き
- cuDNNライブラリの競合を解決済み

## 必要な環境

- NVIDIA GPUを搭載したマシン
- Docker 20.10以上
- docker-compose 1.28以上
- NVIDIA Container Toolkit

## セットアップ

### 1. NVIDIA Container Toolkitのインストール
```bash
# Ubuntu/Debian
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
```

### 2. 環境変数の設定
`.env`ファイルを作成：
```bash
OPENAI_API_KEY=your-api-key-here
USE_GPU=true
WHISPER_MODEL=base
```

### 3. モデルファイルの準備
必要なモデルファイルを以下のディレクトリに配置：
- `model_assets/amitaro/` - TTSモデル
- `bert/` - BERTモデル

## 使用方法

### イメージのビルドと起動
```bash
# ビルドと起動
docker-compose -f docker-compose.buzz_robot.yml up --build -d

# ログの確認
docker-compose -f docker-compose.buzz_robot.yml logs -f

# 停止
docker-compose -f docker-compose.buzz_robot.yml down
```

### 異なるサーバーを起動する場合
```bash
# buzz_robot_fastest_fixed.pyを起動
docker-compose -f docker-compose.buzz_robot.yml run --rm buzz-robot buzz_robot_fastest_fixed.py

# シェルに入る
docker-compose -f docker-compose.buzz_robot.yml run --rm buzz-robot bash
```

## エンドポイント

### Buzz Robot (ポート8080)
- `POST /audio` - 音声ファイルを受信し、応答を返す
- `GET /proactive` - 自発的メッセージを生成
- `GET /devices` - デバイス管理ダッシュボード
- `GET /devices/api` - デバイス情報API

### その他のサーバー
異なるサーバーも起動可能：

```bash
# Gradio UI (ポート7860)
docker-compose -f docker-compose.buzz_robot.yml run --rm -p 7860:7860 buzz-robot python app.py --inbrowser

# エディターUI (ポート7860)
docker-compose -f docker-compose.buzz_robot.yml run --rm -p 7860:7860 buzz-robot python server_editor.py --inbrowser

# FastAPI サーバー (ポート8000)
docker-compose -f docker-compose.buzz_robot.yml run --rm -p 8000:8000 buzz-robot python server_fastapi.py

# Jupyter Notebook (ポート8888)
docker-compose -f docker-compose.buzz_robot.yml run --rm -p 8888:8888 buzz-robot jupyter notebook --ip=0.0.0.0 --allow-root
```

## トラブルシューティング

### cuDNNエラーが発生する場合
コンテナ内で以下を実行：
```bash
docker exec -it buzz-robot-server bash
/app/setup_cudnn_links.sh
```

### GPUが認識されない場合
```bash
# ホストで確認
nvidia-smi

# コンテナ内で確認
docker exec -it buzz-robot-server nvidia-smi
```

## データの永続化

以下のディレクトリがホストとマウントされ、データが永続化されます：
- `conversation_memory_v2/` - 会話履歴
- `device_data/` - デバイス情報
- `audio_archive/` - 音声アーカイブ
- `static/` - 生成された音声ファイル
- `recordings/` - 録音ファイル

## 技術的な詳細

### cuDNN問題の解決方法

1. PyTorchのcuDNNライブラリパスを優先的に使用
2. 必要なシンボリックリンクを自動作成（9.1.0 → 9）
3. `LD_LIBRARY_PATH`を適切に設定

### 環境変数
- `LD_LIBRARY_PATH` - cuDNNライブラリの検索パス
- `CUDA_MODULE_LOADING=LAZY` - CUDAモジュールの遅延ロード
- `USE_GPU=true` - GPU使用の有効化
- `WHISPER_MODEL=base` - Whisperモデルサイズ