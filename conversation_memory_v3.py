"""
会話記憶システム V3 - 統計分析機能統合版
- V2の全機能を継承
- リアルタイム統計生成
- 統計情報に基づく高度なパーソナライゼーション
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import deque
import logging
from conversation_memory_v2 import ConversationMemoryV2
from conversation_analytics import ConversationAnalyzer, StatsUpdateScheduler

class ConversationMemoryV3(ConversationMemoryV2):
    """統計分析機能を統合した会話記憶システム"""
    
    def __init__(self, memory_dir: str = "conversation_memory_v2", 
                 max_history_per_device: int = 50,
                 short_term_minutes: int = 30,
                 stats_update_interval: int = 30):
        """
        Args:
            memory_dir: 会話履歴を保存するディレクトリ
            max_history_per_device: デバイスごとの最大履歴数
            short_term_minutes: 短期記憶として扱う時間（分）
            stats_update_interval: 統計更新間隔（分）
        """
        # 親クラスの初期化
        super().__init__(memory_dir, max_history_per_device, short_term_minutes)
        
        # 分析システムの初期化
        self.analyzer = ConversationAnalyzer(memory_dir)
        self.stats_scheduler = StatsUpdateScheduler(
            self.analyzer, 
            update_interval_minutes=stats_update_interval
        )
        
        # 初回統計更新
        self._initial_stats_update()
    
    def _initial_stats_update(self):
        """初回起動時の統計更新"""
        logging.info("Performing initial statistics update...")
        updated = self.analyzer.update_all_device_stats()
        logging.info(f"Initial stats update completed for {updated} devices")
    
    def add_conversation(self, mac_address: str, device_name: str, 
                        user_message: str, bot_response: str, 
                        location: Optional[str] = None):
        """会話を記録し、必要に応じて統計を更新"""
        # 親クラスの処理を実行
        super().add_conversation(mac_address, device_name, user_message, 
                               bot_response, location)
        
        # デバイスIDを取得
        device_id = self._get_device_id(mac_address, device_name)
        
        # 統計更新が必要かチェック
        if self.stats_scheduler.update_device_if_needed(device_id, mac_address, device_name):
            logging.info(f"Updated statistics for {device_name}")
        
        # 定期的な全体更新チェック
        self.stats_scheduler.check_and_update()
    
    def get_device_stats(self, mac_address: str, device_name: str) -> Optional[Dict]:
        """デバイスの統計情報を取得"""
        device_id = self._get_device_id(mac_address, device_name)
        return self.analyzer.get_device_stats(device_id)
    
    def create_personalized_prompt(self, mac_address: str, device_name: str, 
                                 user_message: str, location: Optional[str] = None) -> str:
        """統計情報を活用した高度なパーソナライズプロンプトを生成"""
        # 短期記憶を取得
        short_term = self.get_short_term_memory(mac_address, device_name)
        
        # デバイス情報を作成
        device_info = f"現在話しているのは「{device_name}」"
        if location:
            device_info += f"（{location}に設置）"
        
        # パーソナライズ用のコンテキスト作成
        context_parts = [f"◆ デバイス情報: {device_info}"]
        
        # 統計情報を取得
        stats = self.get_device_stats(mac_address, device_name)
        
        if stats:
            # 会話履歴サマリー
            context_parts.append(f"\n◆ 会話履歴:")
            context_parts.append(f"  - 総会話数: {stats['total_conversations']}回")
            context_parts.append(f"  - 1日平均: {stats['average_conversations_per_day']}回")
            
            # お気に入りの話題
            if stats['favorite_topics']:
                context_parts.append(f"\n◆ よく話す話題: {', '.join(stats['favorite_topics'][:3])}")
            
            # 時間帯パターン
            current_hour = datetime.now().hour
            if current_hour in stats.get('peak_hours', []):
                context_parts.append(f"\n◆ この時間帯によく会話します")
            
            # 時間帯別の話題
            time_period = self._get_time_period(current_hour)
            time_topics = stats.get('time_based_topics', {}).get(time_period, [])
            if time_topics:
                context_parts.append(f"\n◆ {time_period}の話題: {', '.join(time_topics[:2])}")
            
            # 場所別の話題
            if location:
                location_topics = stats.get('location_based_topics', {}).get(location, [])
                if location_topics:
                    context_parts.append(f"\n◆ {location}での話題: {', '.join(location_topics[:2])}")
            
            # インタラクションスタイル
            style = stats.get('interaction_style', 'casual')
            style_hints = {
                'cheerful': 'いつも明るく楽しい会話',
                'inquisitive': '好奇心旺盛で質問が多い',
                'chatty': 'おしゃべり好き',
                'casual': 'カジュアルな会話'
            }
            if style in style_hints:
                context_parts.append(f"\n◆ 会話スタイル: {style_hints[style]}")
        
        # 直近の会話
        if short_term:
            context_parts.append(f"\n◆ 直近{len(short_term)}回の会話:")
            for i, conv in enumerate(short_term[-3:], 1):
                context_parts.append(f"  {i}. ユーザー: {conv['user_message'][:50]}...")
                context_parts.append(f"     デカ子: {conv['bot_response'][:50]}...")
        
        return "\n".join(context_parts)
    
    def _get_time_period(self, hour: int) -> str:
        """時間帯を取得"""
        if 5 <= hour < 12:
            return "morning"
        elif 12 <= hour < 17:
            return "afternoon"
        elif 17 <= hour < 21:
            return "evening"
        else:
            return "night"
    
    def get_conversation_insights(self, mac_address: str, device_name: str) -> Dict:
        """会話の洞察情報を取得"""
        stats = self.get_device_stats(mac_address, device_name)
        
        if not stats:
            return {
                "has_data": False,
                "message": "まだ会話データがありません"
            }
        
        insights = {
            "has_data": True,
            "conversation_summary": {
                "total": stats['total_conversations'],
                "daily_average": stats['average_conversations_per_day'],
                "days_active": self._calculate_days_active(stats)
            },
            "personality_profile": {
                "favorite_topics": stats['favorite_topics'][:3],
                "interaction_style": stats['interaction_style'],
                "vocabulary_richness": self._assess_vocabulary_richness(stats),
                "question_curiosity": self._assess_curiosity_level(stats)
            },
            "patterns": {
                "most_active_hours": stats['peak_hours'][:2],
                "preferred_greetings": stats.get('common_greetings', []),
                "sentiment_balance": stats.get('sentiment_distribution', {})
            },
            "recommendations": self._generate_recommendations(stats)
        }
        
        return insights
    
    def _calculate_days_active(self, stats: Dict) -> int:
        """アクティブな日数を計算"""
        if stats['first_conversation'] and stats['last_conversation']:
            first = datetime.fromisoformat(stats['first_conversation'])
            last = datetime.fromisoformat(stats['last_conversation'])
            return (last - first).days + 1
        return 0
    
    def _assess_vocabulary_richness(self, stats: Dict) -> str:
        """語彙の豊富さを評価"""
        vocab_size = stats.get('user_vocabulary_size', 0)
        if vocab_size > 100:
            return "very_rich"
        elif vocab_size > 50:
            return "rich"
        elif vocab_size > 20:
            return "moderate"
        else:
            return "simple"
    
    def _assess_curiosity_level(self, stats: Dict) -> str:
        """好奇心レベルを評価"""
        question_types = stats.get('question_types', {})
        total_questions = sum(question_types.values())
        
        if total_questions > 20:
            return "very_curious"
        elif total_questions > 10:
            return "curious"
        elif total_questions > 5:
            return "moderate"
        else:
            return "reserved"
    
    def _generate_recommendations(self, stats: Dict) -> List[str]:
        """統計に基づく推奨事項を生成"""
        recommendations = []
        
        # 話題の推奨
        if "宇宙" in stats.get('favorite_topics', []):
            recommendations.append("宇宙や冒険の新しい話題を提供")
        
        # 時間帯の推奨
        current_hour = datetime.now().hour
        if current_hour not in stats.get('peak_hours', []):
            recommendations.append(f"普段と違う時間帯の会話を楽しんでください")
        
        # 感情バランスの推奨
        sentiment = stats.get('sentiment_distribution', {})
        if sentiment.get('positive', 0) < 30:
            recommendations.append("もっと楽しい話題で盛り上がりましょう")
        
        return recommendations[:3]
    
    def export_device_report(self, mac_address: str, device_name: str, 
                           output_path: Optional[Path] = None) -> Path:
        """デバイスの詳細レポートをエクスポート"""
        device_id = self._get_device_id(mac_address, device_name)
        
        if output_path is None:
            output_path = self.memory_dir / f"report_{device_id}_{int(time.time())}.json"
        
        # 会話履歴を取得
        conversations = list(self.conversations.get(device_id, []))
        
        # 統計情報を取得
        stats = self.get_device_stats(mac_address, device_name)
        
        # 洞察情報を取得
        insights = self.get_conversation_insights(mac_address, device_name)
        
        # レポートを作成
        report = {
            "device_info": {
                "mac_address": mac_address,
                "device_name": device_name,
                "report_date": datetime.now().isoformat()
            },
            "summary": {
                "total_conversations": len(conversations),
                "date_range": {
                    "first": conversations[0]["timestamp"] if conversations else None,
                    "last": conversations[-1]["timestamp"] if conversations else None
                }
            },
            "statistics": stats,
            "insights": insights,
            "recent_conversations": conversations[-10:] if conversations else []
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        logging.info(f"Exported detailed report for {device_name} to {output_path}")
        return output_path


# シングルトンインスタンス
_conversation_memory_v3 = None

def get_conversation_memory_v3():
    """ConversationMemoryV3のシングルトンインスタンスを取得"""
    global _conversation_memory_v3
    if _conversation_memory_v3 is None:
        _conversation_memory_v3 = ConversationMemoryV3()
    return _conversation_memory_v3


# 使用例
if __name__ == "__main__":
    # ロギング設定
    logging.basicConfig(level=logging.INFO)
    
    # メモリシステムを初期化
    memory = get_conversation_memory_v3()
    
    # テストデバイス
    test_mac = "D8:0F:99:D8:00:96"
    test_name = "LivingRoom-ESP32"
    test_location = "1F-Living"
    
    # パーソナライズされたプロンプトを生成
    prompt = memory.create_personalized_prompt(
        test_mac, test_name, "今日はどんな冒険をしようか？", test_location
    )
    print("Personalized Context:")
    print(prompt)
    print("\n" + "="*50 + "\n")
    
    # 会話の洞察を取得
    insights = memory.get_conversation_insights(test_mac, test_name)
    print("Conversation Insights:")
    print(json.dumps(insights, ensure_ascii=False, indent=2))
    
    # レポートをエクスポート
    report_path = memory.export_device_report(test_mac, test_name)
    print(f"\nDetailed report exported to: {report_path}")