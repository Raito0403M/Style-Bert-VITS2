"""
会話分析とステータス生成システム
- 会話履歴から話題、パターン、時間帯を分析
- デバイスごとの統計情報を生成
- 定期的な更新とリアルタイム分析に対応
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
from datetime import datetime, timedelta
from collections import Counter, defaultdict
import logging
from dataclasses import dataclass, asdict
try:
    import MeCab  # 日本語形態素解析用
except ImportError:
    MeCab = None

@dataclass
class ConversationStats:
    """会話統計データクラス"""
    device_id: str
    device_name: str
    mac_address: str
    total_conversations: int
    first_conversation: str
    last_conversation: str
    update_timestamp: str
    
    # 話題分析
    favorite_topics: List[str]
    topic_frequencies: Dict[str, int]
    keyword_cloud: Dict[str, int]
    
    # 時間パターン
    hourly_distribution: Dict[str, int]
    daily_distribution: Dict[str, int]
    peak_hours: List[int]
    average_conversations_per_day: float
    
    # 会話パターン
    common_greetings: List[str]
    question_types: Dict[str, int]
    average_message_length: float
    user_vocabulary_size: int
    
    # 感情・トーン分析
    sentiment_distribution: Dict[str, float]
    interaction_style: str  # "casual", "formal", "playful", etc.
    
    # デバイス特有のパターン
    location_based_topics: Dict[str, List[str]]
    time_based_topics: Dict[str, List[str]]
    
    def to_dict(self) -> dict:
        """データクラスを辞書に変換"""
        return asdict(self)


class ConversationAnalyzer:
    """会話履歴を分析し統計情報を生成するクラス"""
    
    def __init__(self, memory_dir: str = "conversation_memory_v2"):
        self.memory_dir = Path(memory_dir)
        self.devices_dir = self.memory_dir / "devices"
        self.stats_dir = self.memory_dir / "stats"
        self.stats_dir.mkdir(exist_ok=True)
        
        # 日本語形態素解析器（MeCab）の初期化
        try:
            self.mecab = MeCab.Tagger()
        except:
            self.mecab = None
            logging.warning("MeCab not available, using simple keyword extraction")
        
        # トピックキーワード辞書
        self.topic_keywords = {
            "宇宙": ["宇宙", "星", "惑星", "銀河", "ロケット", "宇宙船", "宇宙飛行"],
            "冒険": ["冒険", "探検", "旅", "挑戦", "チャレンジ"],
            "食べ物": ["食べ", "料理", "ごはん", "おいしい", "デカコーン", "スナック"],
            "天気": ["天気", "晴れ", "雨", "暑い", "寒い", "気温"],
            "挨拶": ["おはよう", "こんにちは", "こんばんは", "ありがとう", "さようなら"],
            "質問": ["どう", "なに", "いつ", "どこ", "なぜ", "教えて"],
            "感情": ["楽しい", "嬉しい", "悲しい", "怖い", "好き", "嫌い"],
            "時間": ["今日", "明日", "昨日", "朝", "昼", "夜", "時間"],
            "場所": ["ここ", "そこ", "どこ", "家", "部屋", "外"],
            "デバイス": ["ESP32", "ロボット", "スピーカー", "マイク"]
        }
        
        # 感情キーワード辞書
        self.sentiment_keywords = {
            "positive": ["楽しい", "嬉しい", "ありがとう", "素敵", "良い", "好き", "最高"],
            "negative": ["悲しい", "つらい", "嫌い", "ダメ", "怖い", "心配"],
            "neutral": ["そう", "なるほど", "わかった", "はい", "いいえ"]
        }
    
    def extract_keywords_japanese(self, text: str) -> List[str]:
        """日本語テキストからキーワードを抽出"""
        keywords = []
        
        if self.mecab:
            # MeCabを使用した形態素解析
            node = self.mecab.parseToNode(text)
            while node:
                features = node.feature.split(',')
                # 名詞、動詞、形容詞を抽出
                if features[0] in ['名詞', '動詞', '形容詞']:
                    if node.surface and len(node.surface) > 1:
                        keywords.append(node.surface)
                node = node.next
        else:
            # 簡易的なキーワード抽出
            # 既知のキーワードを検索
            for topic, topic_words in self.topic_keywords.items():
                for word in topic_words:
                    if word in text:
                        keywords.append(word)
        
        return keywords
    
    def identify_topics(self, messages: List[str]) -> Tuple[List[str], Dict[str, int]]:
        """メッセージリストから話題を特定"""
        topic_counts = Counter()
        
        for message in messages:
            # 各トピックカテゴリをチェック
            for topic, keywords in self.topic_keywords.items():
                for keyword in keywords:
                    if keyword in message:
                        topic_counts[topic] += 1
                        break
        
        # 上位トピックを取得
        top_topics = [topic for topic, _ in topic_counts.most_common(5)]
        topic_frequencies = dict(topic_counts)
        
        return top_topics, topic_frequencies
    
    def analyze_time_patterns(self, conversations: List[Dict]) -> Dict:
        """会話の時間パターンを分析"""
        hourly_dist = defaultdict(int)
        daily_dist = defaultdict(int)
        
        for conv in conversations:
            timestamp = datetime.fromisoformat(conv["timestamp"])
            hourly_dist[timestamp.hour] += 1
            daily_dist[timestamp.strftime("%A")] += 1
        
        # ピーク時間を特定
        peak_hours = sorted(hourly_dist.items(), key=lambda x: x[1], reverse=True)[:3]
        peak_hours = [hour for hour, _ in peak_hours]
        
        # 1日あたりの平均会話数
        if conversations:
            first_date = datetime.fromisoformat(conversations[0]["timestamp"])
            last_date = datetime.fromisoformat(conversations[-1]["timestamp"])
            days_diff = (last_date - first_date).days + 1
            avg_per_day = len(conversations) / days_diff
        else:
            avg_per_day = 0.0
        
        return {
            "hourly_distribution": dict(hourly_dist),
            "daily_distribution": dict(daily_dist),
            "peak_hours": peak_hours,
            "average_conversations_per_day": round(avg_per_day, 2)
        }
    
    def analyze_conversation_patterns(self, conversations: List[Dict]) -> Dict:
        """会話パターンを分析"""
        user_messages = [conv["user_message"] for conv in conversations]
        
        # 挨拶パターンを検出
        greetings = []
        greeting_patterns = ["おはよう", "こんにちは", "こんばんは", "やあ", "ハロー"]
        for msg in user_messages:
            for pattern in greeting_patterns:
                if pattern in msg and pattern not in greetings:
                    greetings.append(pattern)
        
        # 質問タイプを分類
        question_types = Counter()
        question_markers = {
            "what": ["なに", "何", "どんな"],
            "when": ["いつ", "何時"],
            "where": ["どこ", "どちら"],
            "why": ["なぜ", "どうして"],
            "how": ["どう", "どのように"],
            "who": ["だれ", "誰"]
        }
        
        for msg in user_messages:
            for q_type, markers in question_markers.items():
                if any(marker in msg for marker in markers):
                    question_types[q_type] += 1
        
        # 平均メッセージ長
        avg_length = sum(len(msg) for msg in user_messages) / len(user_messages) if user_messages else 0
        
        # ユーザー語彙サイズ
        all_keywords = []
        for msg in user_messages:
            all_keywords.extend(self.extract_keywords_japanese(msg))
        vocabulary_size = len(set(all_keywords))
        
        return {
            "common_greetings": greetings[:5],
            "question_types": dict(question_types),
            "average_message_length": round(avg_length, 1),
            "user_vocabulary_size": vocabulary_size,
            "keyword_cloud": dict(Counter(all_keywords).most_common(20))
        }
    
    def analyze_sentiment(self, conversations: List[Dict]) -> Tuple[Dict[str, float], str]:
        """会話の感情を分析"""
        sentiment_counts = defaultdict(int)
        
        for conv in conversations:
            msg = conv["user_message"]
            for sentiment, keywords in self.sentiment_keywords.items():
                if any(keyword in msg for keyword in keywords):
                    sentiment_counts[sentiment] += 1
        
        # パーセンテージに変換
        total = sum(sentiment_counts.values()) or 1
        sentiment_dist = {
            sent: round(count / total * 100, 1) 
            for sent, count in sentiment_counts.items()
        }
        
        # インタラクションスタイルを判定
        if sentiment_dist.get("positive", 0) > 60:
            style = "cheerful"
        elif any("?" in conv["user_message"] for conv in conversations):
            style = "inquisitive"
        elif len(conversations) > 20:
            style = "chatty"
        else:
            style = "casual"
        
        return sentiment_dist, style
    
    def analyze_location_time_patterns(self, conversations: List[Dict]) -> Tuple[Dict, Dict]:
        """場所と時間に基づくトピックパターンを分析"""
        location_topics = defaultdict(list)
        time_topics = defaultdict(list)
        
        for conv in conversations:
            location = conv["device_info"].get("location", "unknown")
            timestamp = datetime.fromisoformat(conv["timestamp"])
            hour = timestamp.hour
            
            # 時間帯を分類
            if 5 <= hour < 12:
                time_period = "morning"
            elif 12 <= hour < 17:
                time_period = "afternoon"
            elif 17 <= hour < 21:
                time_period = "evening"
            else:
                time_period = "night"
            
            # メッセージからキーワードを抽出
            keywords = self.extract_keywords_japanese(conv["user_message"])
            
            # 場所別トピック
            location_topics[location].extend(keywords)
            
            # 時間帯別トピック
            time_topics[time_period].extend(keywords)
        
        # 各カテゴリで最も頻出のトピックを保持
        for key in location_topics:
            if location_topics[key]:
                top_words = Counter(location_topics[key]).most_common(3)
                location_topics[key] = [word for word, _ in top_words]
        
        for key in time_topics:
            if time_topics[key]:
                top_words = Counter(time_topics[key]).most_common(3)
                time_topics[key] = [word for word, _ in top_words]
        
        return dict(location_topics), dict(time_topics)
    
    def generate_device_stats(self, device_id: str, mac_address: str, 
                            device_name: str) -> Optional[ConversationStats]:
        """デバイスの統計情報を生成"""
        device_file = self.devices_dir / f"{device_id}.json"
        
        if not device_file.exists():
            logging.warning(f"No conversation history found for {device_id}")
            return None
        
        try:
            with open(device_file, 'r', encoding='utf-8') as f:
                conversations = json.load(f)
            
            if not conversations:
                return None
            
            # 各種分析を実行
            user_messages = [conv["user_message"] for conv in conversations]
            
            # トピック分析
            favorite_topics, topic_frequencies = self.identify_topics(user_messages)
            
            # 時間パターン分析
            time_patterns = self.analyze_time_patterns(conversations)
            
            # 会話パターン分析
            conv_patterns = self.analyze_conversation_patterns(conversations)
            
            # 感情分析
            sentiment_dist, interaction_style = self.analyze_sentiment(conversations)
            
            # 場所・時間別パターン
            location_topics, time_topics = self.analyze_location_time_patterns(conversations)
            
            # 統計情報を作成
            stats = ConversationStats(
                device_id=device_id,
                device_name=device_name,
                mac_address=mac_address,
                total_conversations=len(conversations),
                first_conversation=conversations[0]["timestamp"],
                last_conversation=conversations[-1]["timestamp"],
                update_timestamp=datetime.now().isoformat(),
                favorite_topics=favorite_topics,
                topic_frequencies=topic_frequencies,
                keyword_cloud=conv_patterns["keyword_cloud"],
                hourly_distribution=time_patterns["hourly_distribution"],
                daily_distribution=time_patterns["daily_distribution"],
                peak_hours=time_patterns["peak_hours"],
                average_conversations_per_day=time_patterns["average_conversations_per_day"],
                common_greetings=conv_patterns["common_greetings"],
                question_types=conv_patterns["question_types"],
                average_message_length=conv_patterns["average_message_length"],
                user_vocabulary_size=conv_patterns["user_vocabulary_size"],
                sentiment_distribution=sentiment_dist,
                interaction_style=interaction_style,
                location_based_topics=location_topics,
                time_based_topics=time_topics
            )
            
            return stats
            
        except Exception as e:
            logging.error(f"Failed to generate stats for {device_id}: {e}")
            return None
    
    def save_device_stats(self, stats: ConversationStats):
        """統計情報をファイルに保存"""
        stats_file = self.stats_dir / f"{stats.device_id}_stats.json"
        
        try:
            with open(stats_file, 'w', encoding='utf-8') as f:
                json.dump(stats.to_dict(), f, ensure_ascii=False, indent=2)
            
            # conversation_memory_v2のdevicesディレクトリにもコピー（互換性のため）
            compat_file = self.devices_dir / f"{stats.device_id}_stats.json"
            with open(compat_file, 'w', encoding='utf-8') as f:
                json.dump(stats.to_dict(), f, ensure_ascii=False, indent=2)
            
            logging.info(f"Saved stats for {stats.device_name}")
            
        except Exception as e:
            logging.error(f"Failed to save stats for {stats.device_id}: {e}")
    
    def update_all_device_stats(self):
        """すべてのデバイスの統計情報を更新"""
        updated_count = 0
        
        for device_file in self.devices_dir.glob("*.json"):
            # _stats.jsonファイルはスキップ
            if "_stats" in device_file.name:
                continue
            
            device_id = device_file.stem
            
            # デバイス情報を取得
            try:
                with open(device_file, 'r', encoding='utf-8') as f:
                    conversations = json.load(f)
                
                if conversations:
                    device_info = conversations[0]["device_info"]
                    mac_address = device_info["mac_address"]
                    device_name = device_info["device_name"]
                    
                    stats = self.generate_device_stats(device_id, mac_address, device_name)
                    if stats:
                        self.save_device_stats(stats)
                        updated_count += 1
                        
            except Exception as e:
                logging.error(f"Failed to update stats for {device_id}: {e}")
        
        logging.info(f"Updated stats for {updated_count} devices")
        return updated_count
    
    def get_device_stats(self, device_id: str) -> Optional[Dict]:
        """保存された統計情報を読み込む"""
        stats_file = self.stats_dir / f"{device_id}_stats.json"
        
        if stats_file.exists():
            try:
                with open(stats_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logging.error(f"Failed to load stats for {device_id}: {e}")
        
        return None
    
    def should_update_stats(self, device_id: str, threshold_minutes: int = 30) -> bool:
        """統計情報の更新が必要かチェック"""
        stats = self.get_device_stats(device_id)
        
        if not stats:
            return True
        
        last_update = datetime.fromisoformat(stats["update_timestamp"])
        if datetime.now() - last_update > timedelta(minutes=threshold_minutes):
            return True
        
        return False


# 統計更新タスクの実装例
class StatsUpdateScheduler:
    """統計情報の定期更新スケジューラ"""
    
    def __init__(self, analyzer: ConversationAnalyzer, 
                 update_interval_minutes: int = 60):
        self.analyzer = analyzer
        self.update_interval = update_interval_minutes
        self.last_update = datetime.now()
    
    def check_and_update(self):
        """定期更新チェック"""
        if datetime.now() - self.last_update > timedelta(minutes=self.update_interval):
            logging.info("Running scheduled stats update...")
            updated = self.analyzer.update_all_device_stats()
            self.last_update = datetime.now()
            return updated
        return 0
    
    def update_device_if_needed(self, device_id: str, mac_address: str, 
                              device_name: str):
        """特定デバイスの統計を必要に応じて更新"""
        if self.analyzer.should_update_stats(device_id):
            stats = self.analyzer.generate_device_stats(device_id, mac_address, device_name)
            if stats:
                self.analyzer.save_device_stats(stats)
                return True
        return False


# 使用例とテスト
if __name__ == "__main__":
    # ロギング設定
    logging.basicConfig(level=logging.INFO)
    
    # アナライザーを初期化
    analyzer = ConversationAnalyzer()
    
    # すべてのデバイスの統計を更新
    print("Updating all device statistics...")
    updated = analyzer.update_all_device_stats()
    print(f"Updated {updated} device statistics")
    
    # 特定デバイスの統計を表示
    test_device_id = "D80F99D80096_LivingRoom-ESP32"
    stats = analyzer.get_device_stats(test_device_id)
    
    if stats:
        print(f"\nStatistics for {stats['device_name']}:")
        print(f"- Total conversations: {stats['total_conversations']}")
        print(f"- Favorite topics: {', '.join(stats['favorite_topics'])}")
        print(f"- Peak hours: {stats['peak_hours']}")
        print(f"- Interaction style: {stats['interaction_style']}")
        print(f"- Average conversations per day: {stats['average_conversations_per_day']}")