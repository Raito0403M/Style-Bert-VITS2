#!/bin/bash
# Cloudflare Tunnel 設定ファイル作成

echo "=== Cloudflare Tunnel 設定作成 ==="

# トンネルIDを取得
TUNNEL_ID=$(cloudflared tunnel list | grep buzz-robot | awk '{print $1}')

if [ -z "$TUNNEL_ID" ]; then
    echo "エラー: buzz-robotトンネルが見つかりません"
    echo "先に 'cloudflared tunnel create buzz-robot' を実行してください"
    exit 1
fi

echo "トンネルID: $TUNNEL_ID"

# 設定ディレクトリ作成
mkdir -p ~/.cloudflared

# 設定ファイル作成
cat > ~/.cloudflared/config.yml << EOF
tunnel: $TUNNEL_ID
credentials-file: /root/.cloudflared/$TUNNEL_ID.json

ingress:
  - service: http://localhost:8080
    originRequest:
      noTLSVerify: true
EOF

echo "設定ファイルを作成しました: ~/.cloudflared/config.yml"
echo ""
echo "次のステップ:"
echo "1. ドメインを設定:"
echo "   cloudflared tunnel route dns buzz-robot buzz-robot.yourdomain.com"
echo ""
echo "2. トンネルを起動:"
echo "   cloudflared tunnel run buzz-robot"
echo ""
echo "3. または、バックグラウンドで実行:"
echo "   nohup cloudflared tunnel run buzz-robot &"