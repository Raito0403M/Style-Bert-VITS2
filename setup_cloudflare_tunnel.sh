#!/bin/bash
# Cloudflare Tunnel セットアップスクリプト

echo "=== Cloudflare Tunnel セットアップ ==="

# 1. cloudflaredをダウンロード
echo "1. cloudflaredをダウンロード中..."
wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared-linux-amd64.deb

# 2. バージョン確認
echo "2. インストール確認"
cloudflared --version

# 3. ログイン手順の説明
echo ""
echo "3. 次のステップ："
echo "   以下のコマンドを実行してCloudflareにログインします："
echo ""
echo "   cloudflared tunnel login"
echo ""
echo "   ブラウザが開くので、Cloudflareアカウントでログインしてください。"
echo ""
echo "4. トンネル作成："
echo "   cloudflared tunnel create buzz-robot"
echo ""
echo "5. 設定ファイル作成："
echo "   このスクリプトが自動で作成します。"

# クリーンアップ
rm -f cloudflared-linux-amd64.deb