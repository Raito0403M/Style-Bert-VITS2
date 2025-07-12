"""
既存のbuzz_robot_fastest_fixed.pyに統合する際の実装例
"""

from fastapi import Request
from device_manager import get_device_manager
import logging

# デバイスマネージャーのインスタンス取得
device_manager = get_device_manager()

# 既存のエンドポイントに追加する処理の例
async def process_with_device_tracking(request: Request):
    """デバイス追跡機能を含む音声処理"""
    
    # 1. デバイス情報をヘッダーから取得
    mac_address = request.headers.get('x-device-mac', 'unknown')
    device_name = request.headers.get('x-device-name', 'Unknown Device')
    device_location = request.headers.get('x-device-location', None)
    client_ip = request.client.host if request.client else 'unknown'
    
    # 2. デバイスを登録/更新
    if mac_address != 'unknown':
        device_manager.register_device(mac_address, device_name, device_location)
    
    # 3. 接続を記録
    connection_info = device_manager.record_connection(
        mac_address=mac_address,
        device_name=device_name,
        client_ip=client_ip,
        additional_info={
            "user_agent": request.headers.get('user-agent', ''),
            "content_type": request.headers.get('content-type', '')
        }
    )
    
    # 4. 表示用の名前を生成
    display_name = device_manager.get_device_display_name(mac_address, device_name)
    
    # 5. ログに出力
    logging.info(f"[Device] 接続: {display_name}")
    logging.info(f"[Device] IP: {client_ip}")
    logging.info(f"[Device] 総接続回数: {device_manager.get_device_info(mac_address).get('total_connections', 0)}")
    
    # 6. レスポンスにデバイス情報を含める
    device_info = {
        "mac_address": mac_address,
        "device_name": device_name,
        "display_name": display_name,
        "location": device_location,
        "ip": client_ip,
        "connection_count": device_manager.get_device_info(mac_address).get('total_connections', 0),
        "first_seen": device_manager.get_device_info(mac_address).get('first_seen', None),
        "last_seen": connection_info["timestamp"]
    }
    
    return device_info


# 管理用エンドポイントの例
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

@app.get("/devices", response_class=HTMLResponse)
async def get_device_dashboard():
    """デバイス管理ダッシュボード"""
    devices = device_manager.get_active_devices(24 * 7)  # 過去7日間
    stats = device_manager.get_device_statistics()
    
    html = f"""
    <html>
    <head>
        <title>ESP32 Device Dashboard</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #4CAF50; color: white; }}
            tr:nth-child(even) {{ background-color: #f2f2f2; }}
            .stats {{ background-color: #e7f3ff; padding: 15px; margin-bottom: 20px; border-radius: 5px; }}
        </style>
    </head>
    <body>
        <h1>ESP32 デバイス管理ダッシュボード</h1>
        
        <div class="stats">
            <h2>統計情報</h2>
            <ul>
                <li>登録デバイス数: {stats['total_registered']}</li>
                <li>24時間以内のアクティブ: {stats['active_last_24h']}</li>
                <li>7日以内のアクティブ: {stats['active_last_7d']}</li>
                <li>総接続回数: {stats['total_connections']}</li>
            </ul>
        </div>
        
        <h2>登録デバイス一覧</h2>
        <table>
            <thead>
                <tr>
                    <th>デバイス名</th>
                    <th>MACアドレス</th>
                    <th>場所</th>
                    <th>最終接続</th>
                    <th>接続回数</th>
                    <th>初回登録</th>
                </tr>
            </thead>
            <tbody>
    """
    
    for device in devices:
        html += f"""
                <tr>
                    <td>{device['device_name']}</td>
                    <td>{device['mac_address']}</td>
                    <td>{device['location']}</td>
                    <td>{device['last_seen']} ({device['hours_ago']}時間前)</td>
                    <td>{device['total_connections']}</td>
                    <td>{device['first_seen']}</td>
                </tr>
        """
    
    html += """
            </tbody>
        </table>
        
        <script>
            // 30秒ごとに自動更新
            setTimeout(() => location.reload(), 30000);
        </script>
    </body>
    </html>
    """
    
    return html


@app.get("/devices/api")
async def get_devices_api():
    """デバイス情報をJSON形式で取得"""
    return {
        "devices": device_manager.devices,
        "active_devices": device_manager.get_active_devices(24),
        "statistics": device_manager.get_device_statistics()
    }


# ESP32側のヘッダー設定例（コメント）
"""
ESP32側では以下のようにヘッダーを設定：

// MACアドレスを取得
uint8_t mac[6];
esp_wifi_get_mac(WIFI_IF_STA, mac);
char mac_string[18];
sprintf(mac_string, "%02X:%02X:%02X:%02X:%02X:%02X", 
        mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);

// デバイス名（NVSから読み込むか、デフォルト値を使用）
const char* device_name = "リビングESP32";  // または nvs_get_str("device_name")
const char* device_location = "1F リビングルーム";

// HTTPヘッダーに設定
esp_http_client_set_header(client, "X-Device-MAC", mac_string);
esp_http_client_set_header(client, "X-Device-Name", device_name);
esp_http_client_set_header(client, "X-Device-Location", device_location);
"""