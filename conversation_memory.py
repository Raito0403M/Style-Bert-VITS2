"""
デバイスごとの会話記憶システム
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

class ConversationMemory:
    def __init__(self, memory_dir: str = "conversation_memory", 
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
        
        self.max_history = max_history_per_device
        self.short_term_minutes = short_term_minutes
        
        # メモリ内キャッシュ（デバイスID -> 会話履歴）
        self.conversations: Dict[str, deque] = {}
        
        # 永続化ファイル
        self.memory_file = self.memory_dir / "conversations.json"
        
        # 起動時に履歴を読み込む
        self._load_conversations()
        
        logging.info(f"ConversationMemory initialized with {len(self.conversations)} device histories")
    
    def _get_device_id(self, mac_address: str, device_name: str) -> str:
        """デバイスの一意なIDを生成"""
        return f"{mac_address}_{device_name}".replace(":", "").replace(" ", "_")
    
    def _load_conversations(self):
        """保存された会話履歴を読み込む"""
        if self.memory_file.exists():
            try:
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for device_id, history in data.items():
                        self.conversations[device_id] = deque(history, maxlen=self.max_history)
            except Exception as e:
                logging.error(f"Failed to load conversations: {e}")
    
    def _save_conversations(self):
        """会話履歴を保存"""
        try:
            data = {
                device_id: list(history) 
                for device_id, history in self.conversations.items()
            }
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.error(f"Failed to save conversations: {e}")
    
    def add_conversation(self, mac_address: str, device_name: str, 
                        user_message: str, bot_response: str,
                        location: Optional[str] = None) -> Dict:
        """
        会話を記録
        
        Args:
            mac_address: デバイスのMACアドレス
            device_name: デバイス名
            user_message: ユーザーの発話
            bot_response: ボットの応答
            location: デバイスの場所（オプション）
        
        Returns:
            保存された会話記録
        """
        device_id = self._get_device_id(mac_address, device_name)
        
        # デバイスの履歴がなければ作成
        if device_id not in self.conversations:
            self.conversations[device_id] = deque(maxlen=self.max_history)
        
        # 会話記録を作成
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
        
        # 履歴に追加
        self.conversations[device_id].append(conversation)
        
        # 保存
        self._save_conversations()
        
        logging.info(f"Conversation added for {device_name} ({mac_address[-8:]})")
        return conversation
    
    def get_short_term_memory(self, mac_address: str, device_name: str) -> List[Dict]:
        """
        短期記憶（最近の会話）を取得
        
        Args:
            mac_address: デバイスのMACアドレス
            device_name: デバイス名
        
        Returns:
            指定時間内の会話履歴
        """
        device_id = self._get_device_id(mac_address, device_name)
        
        if device_id not in self.conversations:
            return []
        
        cutoff_time = datetime.now() - timedelta(minutes=self.short_term_minutes)
        short_term = []
        
        for conv in reversed(self.conversations[device_id]):
            conv_time = datetime.fromisoformat(conv["timestamp"])
            if conv_time > cutoff_time:
                short_term.append(conv)
            else:
                break
        
        return list(reversed(short_term))
    
    def get_conversation_context(self, mac_address: str, device_name: str, 
                               max_context: int = 5) -> str:
        """
        GPTに送るための会話コンテキストを生成
        
        Args:
            mac_address: デバイスのMACアドレス
            device_name: デバイス名
            max_context: 含める過去の会話数
        
        Returns:
            コンテキスト文字列
        """
        short_term = self.get_short_term_memory(mac_address, device_name)
        
        if not short_term:
            return ""
        
        # 最新のmax_context件を取得
        recent_convs = short_term[-max_context:]
        
        context_parts = []
        for conv in recent_convs:
            time_str = datetime.fromisoformat(conv["timestamp"]).strftime("%H:%M")
            context_parts.append(f"[{time_str}] ユーザー: {conv['user_message']}")
            context_parts.append(f"[{time_str}] デカ子: {conv['bot_response']}")
        
        return "\n".join(context_parts)
    
    def get_device_summary(self, mac_address: str, device_name: str) -> Dict:
        """
        デバイスの会話サマリーを取得
        
        Args:
            mac_address: デバイスのMACアドレス
            device_name: デバイス名
        
        Returns:
            サマリー情報
        """
        device_id = self._get_device_id(mac_address, device_name)
        
        if device_id not in self.conversations:
            return {
                "total_conversations": 0,
                "short_term_count": 0,
                "last_conversation": None,
                "common_topics": []
            }
        
        history = list(self.conversations[device_id])
        short_term = self.get_short_term_memory(mac_address, device_name)
        
        # 最後の会話
        last_conv = history[-1] if history else None
        
        # よく出る単語を簡易的に抽出（本格的にはMeCab等を使用）
        all_messages = " ".join([conv["user_message"] for conv in history])
        words = all_messages.split()
        word_freq = {}
        for word in words:
            if len(word) > 2:  # 2文字以上の単語のみ
                word_freq[word] = word_freq.get(word, 0) + 1
        
        common_topics = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            "total_conversations": len(history),
            "short_term_count": len(short_term),
            "last_conversation": last_conv,
            "common_topics": [topic[0] for topic in common_topics]
        }
    
    def create_personalized_prompt(self, mac_address: str, device_name: str, 
                                 user_message: str, location: Optional[str] = None) -> str:
        """
        デバイスの履歴を考慮したパーソナライズされたプロンプトを生成
        
        Args:
            mac_address: デバイスのMACアドレス
            device_name: デバイス名
            user_message: 現在のユーザーメッセージ
            location: デバイスの場所
        
        Returns:
            パーソナライズされたプロンプト
        """
        # 会話コンテキストを取得
        context = self.get_conversation_context(mac_address, device_name)
        
        # デバイスサマリーを取得
        summary = self.get_device_summary(mac_address, device_name)
        
        # 時間帯による挨拶の変更
        hour = datetime.now().hour
        time_greeting = ""
        if 4 <= hour < 10:
            time_greeting = "朝からやる気満々デカッ！"
        elif 10 <= hour < 17:
            time_greeting = "昼間もガンガン行くデカッ！"
        elif 17 <= hour < 22:
            time_greeting = "夜もまだまだこれからデカッ！"
        else:
            time_greeting = "深夜まで頑張ってるデカッ！"
        
        # パーソナライズされた情報
        personalization = []
        
        # 場所情報
        if location and location != "未設定":
            personalization.append(f"場所: {location}")
        
        # 会話回数による親密度
        if summary["total_conversations"] > 20:
            personalization.append("よく話す常連")
        elif summary["total_conversations"] > 5:
            personalization.append("顔見知り")
        else:
            personalization.append("新参者")
        
        # 短期記憶がある場合
        if summary["short_term_count"] > 0:
            personalization.append(f"直近{summary['short_term_count']}回の会話あり")
        
        # プロンプトを構築
        prompt = f"""現在の状況:
- デバイス: {device_name}
- {' / '.join(personalization)}
- {time_greeting}

"""
        
        if context:
            prompt += f"最近の会話履歴:\n{context}\n\n"
        
        prompt += f"現在のユーザーの発話: {user_message}"
        
        return prompt


# シングルトンインスタンス
_conversation_memory_instance = None

def get_conversation_memory() -> ConversationMemory:
    """ConversationMemoryのシングルトンインスタンスを取得"""
    global _conversation_memory_instance
    if _conversation_memory_instance is None:
        _conversation_memory_instance = ConversationMemory()
    return _conversation_memory_instance


# 使用例
def example_usage():
    """使用例"""
    memory = get_conversation_memory()
    
    # 会話を追加
    memory.add_conversation(
        mac_address="D8:0F:99:D8:00:96",
        device_name="リビングESP32",
        user_message="今日も頑張るぞ！",
        bot_response="その意気デカッ！でもまだまだ甘いデカッ！",
        location="1F リビングルーム"
    )
    
    # パーソナライズされたプロンプトを生成
    prompt = memory.create_personalized_prompt(
        mac_address="D8:0F:99:D8:00:96",
        device_name="リビングESP32",
        user_message="疲れたなあ",
        location="1F リビングルーム"
    )
    
    print("Generated prompt:")
    print(prompt)
    
    # サマリーを取得
    summary = memory.get_device_summary("D8:0F:99:D8:00:96", "リビングESP32")
    print(f"\nDevice summary: {json.dumps(summary, indent=2, ensure_ascii=False)}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    example_usage()