# Style-Bert-VITS2 Docker 開発環境

このガイドでは、DockerとGPUサポートを使用してStyle-Bert-VITS2の開発環境をセットアップする方法を説明します。この環境を使用するには、シンプルなスクリプト、Docker Compose、またはVSCodeのRemote Containers拡張機能など、複数の方法があります。

## 前提条件

- ドライバーがインストールされたNVIDIA GPU
- DockerとDocker Compose
- NVIDIA Container Toolkit（必要に応じてスクリプトによって自動的にインストールされます）

## クイックスタート

開発環境を開始する最も簡単な方法は、提供されたスクリプトを使用することです：

```bash
./start-dev-env.sh
```

このスクリプトは以下を行います：
1. NVIDIA GPUが正しく検出されているか確認
2. DockerとDocker Composeがインストールされているか確認
3. DockerがGPUにアクセスできるかテスト
4. 必要に応じてNVIDIA Container Toolkitをインストール
5. Dockerコンテナをビルドして起動

## 手動セットアップ

手動で環境をセットアップする場合：

1. Dockerイメージをビルド：
   ```bash
   docker-compose build
   ```

2. コンテナを起動：
   ```bash
   docker-compose up -d
   ```

3. コンテナに入る：
   ```bash
   docker exec -it style-bert-vits2-dev bash
   ```

4. コンテナを停止：
   ```bash
   docker-compose down
   ```

## Jupyter Labの使用

コンテナ内からJupyter Labを起動するには：

```bash
jupyter lab --ip=0.0.0.0 --allow-root --no-browser
```

その後、ブラウザで `http://localhost:8888` にアクセスします。トークンはターミナルに表示されます。

## Web UIの使用

Gradio Web UIはポート7860で公開されています。コンテナ内で適切なサーバーを起動した後、`http://localhost:7860` でアクセスできます。

## VSCode Remote Containersの使用

このプロジェクトには、統合された開発体験を提供するVSCodeのRemote Containers拡張機能の設定が含まれています：

1. VSCodeに [Remote - Containers](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers) 拡張機能をインストール
2. VSCodeでプロジェクトフォルダを開く
3. VSCodeの左下隅にある緑色のボタンをクリック
4. 「Reopen in Container」を選択

VSCodeは自動的にDockerイメージをビルドしてコンテナを起動します。また以下も行います：
- ポート7860（Gradio）と8888（Jupyter）を転送
- Python開発用の便利なVSCode拡張機能をインストール
- Pythonのリンティングとフォーマットをセットアップ

## ファイル構造

- `Dockerfile.dev`: GPU対応の開発用Dockerfile
- `docker-compose.yml`: Docker Compose設定
- `start-dev-env.sh`: 環境をセットアップして起動するヘルパースクリプト
- `.devcontainer/`: VSCode Remote Containers用の設定

## トラブルシューティング

GPUアクセスに問題がある場合：

1. NVIDIAドライバーが正しくインストールされていることを確認：
   ```bash
   nvidia-smi
   ```

2. NVIDIA Container Toolkitがインストールされているか確認：
   ```bash
   dpkg -l | grep nvidia-container-toolkit
   ```

3. DockerがNVIDIA Container Toolkitを使用するように設定：
   ```bash
   sudo nvidia-ctk runtime configure --runtime=docker
   sudo systemctl restart docker
   ```

4. Docker内でGPUアクセスをテスト：
   ```bash
   docker run --rm --gpus all nvidia/cuda:11.0.3-base-ubuntu20.04 nvidia-smi
   ```
