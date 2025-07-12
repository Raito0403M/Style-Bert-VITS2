"""
ESP32デバイス管理システム
- デバイスの登録・識別
- 接続履歴の記録
- デバイス情報の管理
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import logging

class DeviceManager:
    def __init__(self, data_dir: str = "device_data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # デバイス登録ファイル
        self.registry_file = self.data_dir / "device_registry.json"
        self.history_file = self.data_dir / "connection_history.json"
        
        # メモリ内キャッシュ
        self.devices = self._load_registry()
        self.connection_history = self._load_history()
        
        logging.info(f"DeviceManager initialized with {len(self.devices)} registered devices")
    
    def _load_registry(self) -> Dict:
        """デバイス登録情報を読み込む"""
        if self.registry_file.exists():
            with open(self.registry_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def _save_registry(self):
        """デバイス登録情報を保存"""
        with open(self.registry_file, 'w', encoding='utf-8') as f:
            json.dump(self.devices, f, ensure_ascii=False, indent=2)
    
    def _load_history(self) -> List:
        """接続履歴を読み込む"""
        if self.history_file.exists():
            with open(self.history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    
    def _save_history(self):
        """接続履歴を保存（最新1000件のみ保持）"""
        # 最新1000件のみ保持
        self.connection_history = self.connection_history[-1000:]
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(self.connection_history, f, ensure_ascii=False, indent=2)
    
    def register_device(self, mac_address: str, device_name: str, 
                       location: Optional[str] = None) -> Dict:
        """
        デバイスを登録または更新
        
        Args:
            mac_address: MACアドレス (例: "D8:0F:99:D8:00:96")
            device_name: デバイス名 (例: "リビングESP32")
            location: 設置場所 (例: "1F リビングルーム")
        
        Returns:
            登録されたデバイス情報
        """
        device_info = {
            "mac_address": mac_address.upper(),
            "device_name": device_name,
            "location": location or "未設定",
            "first_seen": self.devices.get(mac_address, {}).get("first_seen", datetime.now().isoformat()),
            "last_seen": datetime.now().isoformat(),
            "total_connections": self.devices.get(mac_address, {}).get("total_connections", 0) + 1
        }
        
        self.devices[mac_address.upper()] = device_info
        self._save_registry()
        
        logging.info(f"Device registered/updated: {device_name} ({mac_address})")
        return device_info
    
    def get_device_info(self, mac_address: str) -> Optional[Dict]:
        """デバイス情報を取得"""
        return self.devices.get(mac_address.upper())
    
    def record_connection(self, mac_address: str, device_name: str, 
                         client_ip: str, additional_info: Optional[Dict] = None) -> Dict:
        """
        接続を記録
        
        Args:
            mac_address: MACアドレス
            device_name: デバイス名
            client_ip: 接続元IPアドレス
            additional_info: 追加情報
        
        Returns:
            接続記録
        """
        # デバイスが未登録なら自動登録
        if mac_address.upper() not in self.devices:
            self.register_device(mac_address, device_name)
        
        connection_record = {
            "timestamp": datetime.now().isoformat(),
            "mac_address": mac_address.upper(),
            "device_name": device_name,
            "client_ip": client_ip,
            "additional_info": additional_info or {}
        }
        
        self.connection_history.append(connection_record)
        self._save_history()
        
        # デバイスの最終接続時刻を更新
        if mac_address.upper() in self.devices:
            self.devices[mac_address.upper()]["last_seen"] = connection_record["timestamp"]
            self.devices[mac_address.upper()]["total_connections"] += 1
            self._save_registry()
        
        return connection_record
    
    def get_device_display_name(self, mac_address: str, device_name: str) -> str:
        """
        表示用のデバイス名を生成
        
        Args:
            mac_address: MACアドレス
            device_name: デバイス名
        
        Returns:
            表示名 (例: "リビングESP32 (D8:00:96)")
        """
        # MACアドレスの最後8文字を取得
        short_mac = mac_address.replace(":", "")[-6:] if mac_address else "??????"
        formatted_short_mac = f"{short_mac[0:2]}:{short_mac[2:4]}:{short_mac[4:6]}"
        
        # 登録済みデバイスの場合は登録名を優先
        device_info = self.get_device_info(mac_address)
        if device_info:
            name = device_info["device_name"]
            location = device_info["location"]
            if location and location != "未設定":
                return f"{name} @ {location} ({formatted_short_mac})"
            return f"{name} ({formatted_short_mac})"
        
        # 未登録デバイスの場合
        return f"{device_name} ({formatted_short_mac})"
    
    def get_active_devices(self, hours: int = 24) -> List[Dict]:
        """
        指定時間内にアクティブだったデバイスのリスト
        
        Args:
            hours: 過去何時間以内か（デフォルト: 24時間）
        
        Returns:
            アクティブなデバイスのリスト
        """
        cutoff_time = datetime.now().timestamp() - (hours * 3600)
        active_devices = []
        
        for mac, device in self.devices.items():
            last_seen = datetime.fromisoformat(device["last_seen"]).timestamp()
            if last_seen > cutoff_time:
                active_devices.append({
                    **device,
                    "hours_ago": round((datetime.now().timestamp() - last_seen) / 3600, 1)
                })
        
        return sorted(active_devices, key=lambda x: x["last_seen"], reverse=True)
    
    def get_device_statistics(self) -> Dict:
        """デバイス統計情報を取得"""
        total_devices = len(self.devices)
        active_24h = len(self.get_active_devices(24))
        active_7d = len(self.get_active_devices(24 * 7))
        
        # 最も活発なデバイス
        most_active = max(self.devices.values(), 
                         key=lambda x: x["total_connections"]) if self.devices else None
        
        return {
            "total_registered": total_devices,
            "active_last_24h": active_24h,
            "active_last_7d": active_7d,
            "total_connections": sum(d["total_connections"] for d in self.devices.values()),
            "most_active_device": most_active
        }


# シングルトンインスタンス
_device_manager_instance = None

def get_device_manager() -> DeviceManager:
    """DeviceManagerのシングルトンインスタンスを取得"""
    global _device_manager_instance
    if _device_manager_instance is None:
        _device_manager_instance = DeviceManager()
    return _device_manager_instance


# テスト用のメイン関数
if __name__ == "__main__":
    # ログ設定
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
    
    # デバイスマネージャーのテスト
    dm = DeviceManager()
    
    # デバイス登録テスト
    dm.register_device("D8:0F:99:D8:00:96", "リビングESP32", "1F リビングルーム")
    dm.register_device("AC:67:B2:36:FC:D8", "寝室ESP32", "2F 寝室")
    
    # 接続記録テスト
    dm.record_connection("D8:0F:99:D8:00:96", "リビングESP32", "192.168.1.100")
    
    # 表示名テスト
    display_name = dm.get_device_display_name("D8:0F:99:D8:00:96", "リビングESP32")
    print(f"Display name: {display_name}")
    
    # 統計情報
    stats = dm.get_device_statistics()
    print(f"Statistics: {json.dumps(stats, indent=2, ensure_ascii=False)}")