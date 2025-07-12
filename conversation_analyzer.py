"""
会話履歴の分析と統計情報の生成
"""
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter
from typing import Dict, List, Optional, Tuple
import re

class ConversationAnalyzer:
    """会話履歴を分析してstats.jsonを生成・更新"""
    
    def __init__(self, memory_dir: Path = Path("conversation_memory_v2")):
        self.memory_dir = memory_dir
        self.devices_dir = memory_dir / "devices"
        self.stats_dir = memory_dir / "stats"
        self.stats_dir.mkdir(parents=True, exist_ok=True)
        
        # キーワード辞書（日本語解析の簡易版）
        self.topic_keywords = {
            "宇宙": ["宇宙", "星", "銀河", "惑星", "ロケット", "NASA"],
            "冒険": ["冒険", "探検", "旅", "挑戦", "発見"],
            "技術": ["AI", "ロボット", "プログラム", "コンピュータ", "技術"],
            "日常": ["今日", "明日", "天気", "食事", "仕事", "学校"],
            "感情": ["嬉しい", "楽しい", "悲しい", "怒", "驚"],
        }
        
        # 挨拶パターン
        self.greeting_patterns = [
            r"おはよう", r"こんにちは", r"こんばんは",
            r"やあ", r"よう", r"そこにいるか",
            r"元気", r"調子はどう"
        ]
    
    def analyze_device_conversations(self, device_id: str) -> Dict:
        """デバイスの会話履歴を分析"""
        device_file = self.devices_dir / f"{device_id}.json"
        
        if not device_file.exists():
            return self._empty_stats()
        
        try:
            with open(device_file, 'r', encoding='utf-8') as f:
                conversations = json.load(f)
        except Exception as e:
            logging.error(f"Failed to load conversations for {device_id}: {e}")
            return self._empty_stats()
        
        # 分析実行
        stats = {
            "device_id": device_id,
            "total_conversations": len(conversations),
            "favorite_topics": self._analyze_topics(conversations),
            "time_patterns": self._analyze_time_patterns(conversations),
            "conversation_patterns": self._analyze_conversation_patterns(conversations),
            "interaction_style": self._analyze_interaction_style(conversations),
            "last_updated": datetime.now().isoformat(),
            "analysis_version": "1.0"
        }
        
        return stats
    
    def _analyze_topics(self, conversations: List[Dict]) -> List[str]:
        """話題の分析"""
        topic_scores = Counter()
        
        for conv in conversations:
            user_msg = conv.get("user_message", "").lower()
            
            # キーワードベースでトピックをスコアリング
            for topic, keywords in self.topic_keywords.items():
                for keyword in keywords:
                    if keyword.lower() in user_msg:
                        topic_scores[topic] += 1
        
        # 上位3つのトピックを返す
        return [topic for topic, _ in topic_scores.most_common(3)]
    
    def _analyze_time_patterns(self, conversations: List[Dict]) -> Dict:
        """時間パターンの分析"""
        hour_counter = Counter()
        weekday_counter = Counter()
        
        for conv in conversations:
            timestamp = datetime.fromisoformat(conv["timestamp"])
            hour_counter[timestamp.hour] += 1
            weekday_counter[timestamp.weekday()] += 1
        
        # ピーク時間帯（上位3時間）
        peak_hours = [hour for hour, _ in hour_counter.most_common(3)]
        
        # 平均会話間隔
        if len(conversations) > 1:
            timestamps = [datetime.fromisoformat(c["timestamp"]) for c in conversations]
            intervals = [(timestamps[i+1] - timestamps[i]).total_seconds() / 3600 
                        for i in range(len(timestamps)-1)]
            avg_interval_hours = sum(intervals) / len(intervals) if intervals else 0
        else:
            avg_interval_hours = 0
        
        return {
            "peak_hours": peak_hours,
            "most_active_weekdays": [day for day, _ in weekday_counter.most_common(2)],
            "average_interval_hours": round(avg_interval_hours, 1),
            "conversations_per_day": self._calculate_conversations_per_day(conversations)
        }
    
    def _analyze_conversation_patterns(self, conversations: List[Dict]) -> Dict:
        """会話パターンの分析"""
        greetings = []
        questions = []
        avg_message_length = 0
        
        for conv in conversations:
            user_msg = conv.get("user_message", "")
            
            # 挨拶の検出
            for pattern in self.greeting_patterns:
                if re.search(pattern, user_msg):
                    greetings.append(user_msg[:20])  # 最初の20文字
                    break
            
            # 質問の検出
            if "？" in user_msg or "?" in user_msg or "か？" in user_msg:
                questions.append(user_msg[:30])
            
            avg_message_length += len(user_msg)
        
        avg_message_length = avg_message_length / len(conversations) if conversations else 0
        
        # よく使う挨拶（上位3つ）
        greeting_counter = Counter(greetings)
        common_greetings = [g for g, _ in greeting_counter.most_common(3)]
        
        return {
            "common_greetings": common_greetings,
            "question_ratio": round(len(questions) / len(conversations) if conversations else 0, 2),
            "average_message_length": round(avg_message_length, 1),
            "vocabulary_diversity": self._calculate_vocabulary_diversity(conversations)
        }
    
    def _analyze_interaction_style(self, conversations: List[Dict]) -> Dict:
        """インタラクションスタイルの分析"""
        # 応答の感情トーンを簡易分析
        positive_words = ["嬉しい", "楽しい", "いいね", "素晴らしい", "最高"]
        negative_words = ["悲しい", "つらい", "ダメ", "困った", "大変"]
        
        positive_count = 0
        negative_count = 0
        
        for conv in conversations:
            user_msg = conv.get("user_message", "")
            for word in positive_words:
                if word in user_msg:
                    positive_count += 1
            for word in negative_words:
                if word in user_msg:
                    negative_count += 1
        
        total = len(conversations)
        
        return {
            "sentiment_tendency": "positive" if positive_count > negative_count else "neutral",
            "positive_ratio": round(positive_count / total if total else 0, 2),
            "engagement_level": self._calculate_engagement_level(conversations)
        }
    
    def _calculate_conversations_per_day(self, conversations: List[Dict]) -> float:
        """1日あたりの平均会話数を計算"""
        if not conversations:
            return 0
        
        timestamps = [datetime.fromisoformat(c["timestamp"]) for c in conversations]
        date_range = (timestamps[-1] - timestamps[0]).days + 1
        
        return round(len(conversations) / date_range if date_range > 0 else len(conversations), 1)
    
    def _calculate_vocabulary_diversity(self, conversations: List[Dict]) -> str:
        """語彙の多様性を計算"""
        all_words = []
        for conv in conversations:
            # 簡易的な単語分割（スペースと句読点で分割）
            words = re.findall(r'\w+', conv.get("user_message", ""))
            all_words.extend(words)
        
        if not all_words:
            return "low"
        
        unique_ratio = len(set(all_words)) / len(all_words)
        
        if unique_ratio > 0.7:
            return "high"
        elif unique_ratio > 0.4:
            return "medium"
        else:
            return "low"
    
    def _calculate_engagement_level(self, conversations: List[Dict]) -> str:
        """エンゲージメントレベルを計算"""
        if not conversations:
            return "low"
        
        # 最近の活動をチェック
        last_conv = datetime.fromisoformat(conversations[-1]["timestamp"])
        days_since_last = (datetime.now() - last_conv).days
        
        if days_since_last > 7:
            return "low"
        elif days_since_last > 3:
            return "medium"
        else:
            return "high"
    
    def _empty_stats(self) -> Dict:
        """空の統計情報"""
        return {
            "device_id": "",
            "total_conversations": 0,
            "favorite_topics": [],
            "time_patterns": {
                "peak_hours": [],
                "most_active_weekdays": [],
                "average_interval_hours": 0,
                "conversations_per_day": 0
            },
            "conversation_patterns": {
                "common_greetings": [],
                "question_ratio": 0,
                "average_message_length": 0,
                "vocabulary_diversity": "low"
            },
            "interaction_style": {
                "sentiment_tendency": "neutral",
                "positive_ratio": 0,
                "engagement_level": "low"
            },
            "last_updated": datetime.now().isoformat(),
            "analysis_version": "1.0"
        }
    
    def save_stats(self, device_id: str, stats: Dict) -> Path:
        """統計情報を保存"""
        stats_file = self.stats_dir / f"{device_id}_stats.json"
        
        try:
            with open(stats_file, 'w', encoding='utf-8') as f:
                json.dump(stats, f, ensure_ascii=False, indent=2)
            
            logging.info(f"Stats saved for {device_id}")
            return stats_file
        
        except Exception as e:
            logging.error(f"Failed to save stats for {device_id}: {e}")
            raise
    
    def update_device_stats(self, device_id: str) -> Dict:
        """デバイスの統計情報を更新"""
        stats = self.analyze_device_conversations(device_id)
        self.save_stats(device_id, stats)
        return stats
    
    def update_all_stats(self) -> Dict[str, Dict]:
        """全デバイスの統計情報を更新"""
        results = {}
        
        for device_file in self.devices_dir.glob("*.json"):
            if "_stats" not in device_file.stem:  # stats.jsonは除外
                device_id = device_file.stem
                try:
                    results[device_id] = self.update_device_stats(device_id)
                except Exception as e:
                    logging.error(f"Failed to update stats for {device_id}: {e}")
                    results[device_id] = {"error": str(e)}
        
        return results


# プロンプト生成の強化
def create_enhanced_prompt(base_prompt: str, stats: Dict, current_context: Dict) -> str:
    """統計情報を活用した強化プロンプトの生成"""
    
    enhancements = []
    
    # 1. トピックに基づく調整
    if stats.get("favorite_topics"):
        topics = stats["favorite_topics"]
        enhancements.append(f"このユーザーは特に{', '.join(topics)}について話すのが好きだ。")
    
    # 2. 時間パターンに基づく調整
    time_patterns = stats.get("time_patterns", {})
    current_hour = datetime.now().hour
    
    if current_hour in time_patterns.get("peak_hours", []):
        enhancements.append("いつもの時間に来てくれたことを認識している。")
    else:
        enhancements.append("普段と違う時間に来たことに気づいている。")
    
    # 3. 会話パターンに基づく調整
    conv_patterns = stats.get("conversation_patterns", {})
    
    if conv_patterns.get("question_ratio", 0) > 0.7:
        enhancements.append("質問が多いユーザーなので、詳しく答える。")
    
    if conv_patterns.get("vocabulary_diversity") == "high":
        enhancements.append("語彙が豊富なユーザーなので、より表現豊かに話す。")
    
    # 4. インタラクションスタイルに基づく調整
    interaction = stats.get("interaction_style", {})
    
    if interaction.get("engagement_level") == "high":
        enhancements.append("最近よく話してくれる常連さんとして親しみを込めて話す。")
    elif interaction.get("engagement_level") == "low":
        enhancements.append("久しぶりの会話なので、温かく迎える。")
    
    # 5. デバイス固有の記憶
    if current_context.get("device_name"):
        device_name = current_context["device_name"]
        location = current_context.get("location", "")
        enhancements.append(f"「{device_name}」{f'（{location}）' if location else ''}からの呼びかけだ。")
    
    # プロンプトの組み立て
    enhanced_prompt = base_prompt
    
    if enhancements:
        enhanced_prompt += "\n\n【このユーザーの特徴】\n"
        enhanced_prompt += "\n".join(f"- {e}" for e in enhancements)
    
    return enhanced_prompt