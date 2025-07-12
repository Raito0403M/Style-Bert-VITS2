"""
デバイスごとの会話記憶システム（改良版）
- デバイスごとに個別のファイルで管理
- 短期記憶（直近の会話）
- デバイスごとの会話履歴
- コンテキストを考慮した応答生成
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import deque
import logging

class ConversationMemoryV2:
    def __init__(self, memory_dir: str = "conversation_memory_v2", 
                 max_history_per_device: int = 50,
                 short_term_minutes: int = 30):
        """
        Args:
            memory_dir: 会話履歴を保存するディレクトリ
            max_history_per_device: デバイスごとの最大履歴数
            short_term_minutes: 短期記憶として扱う時間（分）
        """
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(exist_ok=True)
        
        # デバイスごとのサブディレクトリを作成
        self.devices_dir = self.memory_dir / "devices"
        self.devices_dir.mkdir(exist_ok=True)
        
        self.max_history = max_history_per_device
        self.short_term_minutes = short_term_minutes
        
        # メモリ内キャッシュ（デバイスID -> 会話履歴）
        self.conversations: Dict[str, deque] = {}
        
        # 起動時に履歴を読み込む
        self._load_all_conversations()
        
        logging.info(f"ConversationMemoryV2 initialized with {len(self.conversations)} device histories")
    
    def _get_device_id(self, mac_address: str, device_name: str) -> str:
        """デバイスの一意なIDを生成"""
        return f"{mac_address}_{device_name}".replace(":", "").replace(" ", "_")
    
    def _get_device_file(self, device_id: str) -> Path:
        """デバイス固有のファイルパスを取得"""
        return self.devices_dir / f"{device_id}.json"
    
    def _load_device_conversations(self, device_id: str) -> deque:
        """特定デバイスの会話履歴を読み込む"""
        device_file = self._get_device_file(device_id)
        if device_file.exists():
            try:
                with open(device_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return deque(data, maxlen=self.max_history)
            except Exception as e:
                logging.error(f"Failed to load conversations for {device_id}: {e}")
        return deque(maxlen=self.max_history)
    
    def _load_all_conversations(self):
        """すべてのデバイスの会話履歴を読み込む"""
        # デバイスディレクトリ内のすべてのJSONファイルを読み込む
        for device_file in self.devices_dir.glob("*.json"):
            device_id = device_file.stem
            try:
                with open(device_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.conversations[device_id] = deque(data, maxlen=self.max_history)
            except Exception as e:
                logging.error(f"Failed to load {device_file}: {e}")
    
    def _save_device_conversations(self, device_id: str):
        """特定デバイスの会話履歴を保存"""
        device_file = self._get_device_file(device_id)
        try:
            with open(device_file, 'w', encoding='utf-8') as f:
                json.dump(list(self.conversations.get(device_id, [])), f, 
                         ensure_ascii=False, indent=2)
            logging.info(f"Saved conversations for {device_id}")
        except Exception as e:
            logging.error(f"Failed to save conversations for {device_id}: {e}")
    
    def add_conversation(self, mac_address: str, device_name: str, 
                        user_message: str, bot_response: str, 
                        location: Optional[str] = None):
        """会話を記録"""
        device_id = self._get_device_id(mac_address, device_name)
        
        # デバイスIDが初めての場合は初期化
        if device_id not in self.conversations:
            # 既存ファイルがあれば読み込む
            self.conversations[device_id] = self._load_device_conversations(device_id)
        
        # 会話を追加
        conversation = {
            "timestamp": datetime.now().isoformat(),
            "user_message": user_message,
            "bot_response": bot_response,
            "device_info": {
                "mac_address": mac_address,
                "device_name": device_name,
                "location": location
            }
        }
        
        self.conversations[device_id].append(conversation)
        
        # 個別ファイルに保存
        self._save_device_conversations(device_id)
        
        logging.info(f"Conversation added for {device_name} ({mac_address[:8]})")
    
    def get_recent_conversations(self, mac_address: str, device_name: str, 
                                count: int = 5) -> List[Dict]:
        """最近の会話を取得"""
        device_id = self._get_device_id(mac_address, device_name)
        
        if device_id not in self.conversations:
            # ファイルから読み込み試行
            self.conversations[device_id] = self._load_device_conversations(device_id)
        
        conversations = list(self.conversations.get(device_id, []))
        return conversations[-count:] if conversations else []
    
    def get_short_term_memory(self, mac_address: str, device_name: str) -> List[Dict]:
        """短期記憶（指定時間内の会話）を取得"""
        device_id = self._get_device_id(mac_address, device_name)
        cutoff_time = datetime.now() - timedelta(minutes=self.short_term_minutes)
        
        short_term = []
        for conv in self.conversations.get(device_id, []):
            conv_time = datetime.fromisoformat(conv["timestamp"])
            if conv_time > cutoff_time:
                short_term.append(conv)
        
        return short_term
    
    def create_personalized_prompt(self, mac_address: str, device_name: str, 
                                 user_message: str, location: Optional[str] = None) -> str:
        """デバイス固有のコンテキストを含むプロンプトを生成"""
        # 短期記憶を取得
        short_term = self.get_short_term_memory(mac_address, device_name)
        
        # デバイス情報を作成
        device_info = f"現在話しているのは「{device_name}」"
        if location:
            device_info += f"（{location}に設置）"
        
        # パーソナライズ用のコンテキスト作成
        context_parts = [f"◆ デバイス情報: {device_info}"]
        
        if short_term:
            context_parts.append(f"\n◆ 直近{len(short_term)}回の会話:")
            for i, conv in enumerate(short_term[-3:], 1):  # 直近3つまで
                context_parts.append(f"  {i}. ユーザー: {conv['user_message'][:50]}...")
                context_parts.append(f"     デカ子: {conv['bot_response'][:50]}...")
        
        # 統計情報ファイルがあれば読み込む
        stats_file = self.devices_dir / f"{self._get_device_id(mac_address, device_name)}_stats.json"
        if stats_file.exists():
            try:
                with open(stats_file, 'r', encoding='utf-8') as f:
                    stats = json.load(f)
                    if stats.get("favorite_topics"):
                        context_parts.append(f"\n◆ よく話す話題: {', '.join(stats['favorite_topics'][:3])}")
            except:
                pass
        
        return "\n".join(context_parts)
    
    def get_device_summary(self, mac_address: str, device_name: str) -> Dict:
        """デバイスの会話サマリーを取得"""
        device_id = self._get_device_id(mac_address, device_name)
        conversations = list(self.conversations.get(device_id, []))
        
        if not conversations:
            return {
                "total_conversations": 0,
                "short_term_count": 0,
                "last_conversation": None,
                "common_topics": []
            }
        
        # 短期記憶の数をカウント
        short_term = self.get_short_term_memory(mac_address, device_name)
        
        # 話題を分析（簡易版）
        all_messages = [c["user_message"] for c in conversations]
        
        return {
            "total_conversations": len(conversations),
            "short_term_count": len(short_term),
            "last_conversation": conversations[-1] if conversations else None,
            "common_topics": list(set(all_messages))[:5]  # 重複を除いた最初の5つ
        }
    
    def export_device_history(self, mac_address: str, device_name: str, 
                            output_path: Optional[Path] = None) -> Path:
        """デバイスの会話履歴をエクスポート"""
        device_id = self._get_device_id(mac_address, device_name)
        
        if output_path is None:
            output_path = self.memory_dir / f"export_{device_id}_{int(time.time())}.json"
        
        conversations = list(self.conversations.get(device_id, []))
        
        export_data = {
            "device_info": {
                "mac_address": mac_address,
                "device_name": device_name,
                "export_date": datetime.now().isoformat()
            },
            "conversations": conversations,
            "statistics": self.get_device_summary(mac_address, device_name)
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        logging.info(f"Exported history for {device_name} to {output_path}")
        return output_path


# シングルトンインスタンス
_conversation_memory_v2 = None

def get_conversation_memory_v2():
    """ConversationMemoryV2のシングルトンインスタンスを取得"""
    global _conversation_memory_v2
    if _conversation_memory_v2 is None:
        _conversation_memory_v2 = ConversationMemoryV2()
    return _conversation_memory_v2