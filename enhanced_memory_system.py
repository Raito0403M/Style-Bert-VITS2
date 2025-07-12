"""
統計情報を活用した強化版メモリシステム
"""
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import threading
import time

from conversation_memory_v2 import ConversationMemoryV2
from conversation_analyzer import ConversationAnalyzer, create_enhanced_prompt

class EnhancedMemorySystem:
    """統計分析機能を統合したメモリシステム"""
    
    def __init__(self, memory_dir: Path = Path("conversation_memory_v2")):
        self.memory = ConversationMemoryV2(memory_dir)
        self.analyzer = ConversationAnalyzer(memory_dir)
        self.stats_cache = {}  # デバイスIDをキーとした統計情報のキャッシュ
        self.last_update = {}  # デバイスIDをキーとした最終更新時刻
        
        # バックグラウンド更新の設定
        self.update_interval = 3600  # 1時間ごと
        self.start_background_updater()
    
    def start_background_updater(self):
        """バックグラウンドで統計情報を定期更新"""
        def updater():
            while True:
                try:
                    logging.info("Starting background stats update...")
                    self.analyzer.update_all_stats()
                    logging.info("Background stats update completed")
                except Exception as e:
                    logging.error(f"Background update failed: {e}")
                
                time.sleep(self.update_interval)
        
        thread = threading.Thread(target=updater, daemon=True)
        thread.start()
    
    def add_conversation_with_analysis(self, mac_address: str, device_name: str,
                                     user_message: str, bot_response: str,
                                     location: Optional[str] = None):
        """会話を追加し、必要に応じて統計を更新"""
        # 通常の会話追加
        self.memory.add_conversation(mac_address, device_name, user_message, 
                                   bot_response, location)
        
        # 統計更新の判定（30分以上経過していたら更新）
        device_id = f"{mac_address}_{device_name}"
        last_update = self.last_update.get(device_id)
        
        if last_update is None or (datetime.now() - last_update) > timedelta(minutes=30):
            try:
                stats = self.analyzer.update_device_stats(device_id)
                self.stats_cache[device_id] = stats
                self.last_update[device_id] = datetime.now()
                logging.info(f"Stats updated for {device_name}")
            except Exception as e:
                logging.error(f"Failed to update stats: {e}")
    
    def get_device_stats(self, mac_address: str, device_name: str) -> Dict:
        """デバイスの統計情報を取得（キャッシュ優先）"""
        device_id = f"{mac_address}_{device_name}"
        
        # キャッシュをチェック
        if device_id in self.stats_cache:
            return self.stats_cache[device_id]
        
        # ファイルから読み込み
        stats_file = self.analyzer.stats_dir / f"{device_id}_stats.json"
        if stats_file.exists():
            try:
                with open(stats_file, 'r', encoding='utf-8') as f:
                    stats = json.load(f)
                    self.stats_cache[device_id] = stats
                    return stats
            except Exception as e:
                logging.error(f"Failed to load stats: {e}")
        
        # 統計情報がない場合は生成
        try:
            stats = self.analyzer.update_device_stats(device_id)
            self.stats_cache[device_id] = stats
            return stats
        except:
            return self.analyzer._empty_stats()
    
    def create_personalized_response_context(self, mac_address: str, device_name: str,
                                           user_message: str, location: Optional[str] = None,
                                           base_prompt: str = "") -> str:
        """統計情報を活用したパーソナライズされたコンテキストを生成"""
        
        # 基本的なパーソナライズ（短期記憶）
        basic_context = self.memory.create_personalized_prompt(
            mac_address, device_name, user_message, location
        )
        
        # 統計情報を取得
        stats = self.get_device_stats(mac_address, device_name)
        
        # 現在のコンテキスト
        current_context = {
            "device_name": device_name,
            "location": location,
            "user_message": user_message,
            "timestamp": datetime.now()
        }
        
        # 強化されたプロンプトを生成
        if base_prompt:
            enhanced_prompt = create_enhanced_prompt(base_prompt, stats, current_context)
        else:
            enhanced_prompt = ""
        
        # 全体のコンテキストを組み立て
        full_context = []
        
        if enhanced_prompt:
            full_context.append(enhanced_prompt)
        
        full_context.append("\n" + basic_context)
        
        # 統計ベースの追加情報
        if stats.get("total_conversations", 0) > 10:
            insights = self._generate_conversation_insights(stats)
            if insights:
                full_context.append("\n【会話の傾向】")
                full_context.extend(insights)
        
        return "\n".join(full_context)
    
    def _generate_conversation_insights(self, stats: Dict) -> List[str]:
        """統計情報から会話の洞察を生成"""
        insights = []
        
        # エンゲージメントレベルに基づく洞察
        engagement = stats.get("interaction_style", {}).get("engagement_level")
        if engagement == "high":
            insights.append("・毎日のように話しかけてくれる大切な友だち")
        elif engagement == "low":
            insights.append("・久しぶりの会話なので温かく迎えよう")
        
        # 会話パターンに基づく洞察
        conv_patterns = stats.get("conversation_patterns", {})
        if conv_patterns.get("question_ratio", 0) > 0.7:
            insights.append("・好奇心旺盛でよく質問をしてくれる")
        
        avg_length = conv_patterns.get("average_message_length", 0)
        if avg_length > 50:
            insights.append("・じっくりと話すのが好きなタイプ")
        elif avg_length < 20:
            insights.append("・短い会話を好むタイプ")
        
        # 時間パターンに基づく洞察
        time_patterns = stats.get("time_patterns", {})
        conv_per_day = time_patterns.get("conversations_per_day", 0)
        if conv_per_day > 5:
            insights.append("・とても頻繁に話しかけてくれる")
        
        return insights
    
    def get_response_style_modifiers(self, mac_address: str, device_name: str) -> Dict:
        """応答スタイルの修飾子を取得"""
        stats = self.get_device_stats(mac_address, device_name)
        
        modifiers = {
            "response_length": "normal",  # short, normal, long
            "formality": "casual",        # casual, normal, formal
            "emotion_level": "high",      # low, normal, high
            "detail_level": "normal"      # low, normal, high
        }
        
        # 統計に基づいて修飾子を調整
        conv_patterns = stats.get("conversation_patterns", {})
        
        # メッセージ長に基づく調整
        avg_length = conv_patterns.get("average_message_length", 0)
        if avg_length > 50:
            modifiers["response_length"] = "long"
            modifiers["detail_level"] = "high"
        elif avg_length < 20:
            modifiers["response_length"] = "short"
            modifiers["detail_level"] = "low"
        
        # 語彙の多様性に基づく調整
        if conv_patterns.get("vocabulary_diversity") == "high":
            modifiers["formality"] = "normal"
            modifiers["detail_level"] = "high"
        
        # エンゲージメントに基づく調整
        engagement = stats.get("interaction_style", {}).get("engagement_level")
        if engagement == "high":
            modifiers["emotion_level"] = "high"
            modifiers["formality"] = "casual"
        
        return modifiers


# 使用例
def demo_enhanced_system():
    """強化版メモリシステムのデモ"""
    system = EnhancedMemorySystem()
    
    # デバイス情報
    mac = "D8:0F:99:D8:00:96"
    name = "LivingRoom-ESP32"
    location = "1F-Living"
    
    # 基本プロンプト
    base_prompt = """
あなたはデカコーンハウスの守り神「デカ子」！
エネルギッシュで前向き、そして宇宙一デカい心を持ってるデカッ！
訪問者を元気づけるのが使命デカッ！
「デカッ！」を語尾につけることがあるデカッ！
返答は必ず日本語で簡潔に（2文以内）デカッ！
"""
    
    # パーソナライズされたコンテキストを生成
    user_message = "今日も宇宙の冒険の話を聞かせて！"
    
    context = system.create_personalized_response_context(
        mac, name, user_message, location, base_prompt
    )
    
    print("=== 生成されたコンテキスト ===")
    print(context)
    
    # 応答スタイルの修飾子を取得
    style_modifiers = system.get_response_style_modifiers(mac, name)
    print("\n=== 応答スタイル修飾子 ===")
    print(json.dumps(style_modifiers, indent=2))
    
    # 会話を追加（統計も自動更新）
    bot_response = "今日の宇宙の冒険は、デカコーン星雲を超えて新しい友達を見つける旅デカッ！君も一緒に行くデカッ！"
    
    system.add_conversation_with_analysis(
        mac, name, user_message, bot_response, location
    )
    
    print("\n=== 会話が追加され、統計が更新されました ===")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    demo_enhanced_system()