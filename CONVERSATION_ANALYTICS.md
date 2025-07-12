# Conversation Analytics System

Style-Bert-VITS2の会話履歴を分析し、デバイスごとにパーソナライズされた応答を実現するシステムです。

## 概要

このシステムは、ESP32デバイスとの会話履歴を分析し、各デバイスの使用パターンや好みを学習します。統計情報を活用して、より自然で個別化された対話を提供します。

## 主要コンポーネント

### 1. ConversationAnalyzer (`conversation_analyzer.py`)
会話履歴を分析してstats.jsonを生成する分析エンジンです。

**分析内容：**
- **話題分析**: キーワードベースで好きな話題を抽出
- **時間パターン**: いつ話しかけられることが多いか
- **会話パターン**: 挨拶の種類、質問率、メッセージ長
- **インタラクションスタイル**: 感情傾向、エンゲージメントレベル

### 2. EnhancedMemorySystem (`enhanced_memory_system.py`)
統計分析機能を統合した強化版メモリシステムです。

**機能：**
- 会話追加時の自動統計更新（30分間隔）
- バックグラウンドでの定期更新（1時間ごと）
- 統計情報のキャッシュ管理
- パーソナライズされたプロンプト生成

## stats.jsonの構造

```json
{
  "device_id": "D80F99D80096_LivingRoom-ESP32",
  "total_conversations": 50,
  "favorite_topics": ["宇宙", "冒険", "技術"],
  "time_patterns": {
    "peak_hours": [20, 21, 22],
    "most_active_weekdays": [5, 6],
    "average_interval_hours": 2.5,
    "conversations_per_day": 5.2
  },
  "conversation_patterns": {
    "common_greetings": ["そこにいるかい", "やあ", "元気かな"],
    "question_ratio": 0.75,
    "average_message_length": 35.5,
    "vocabulary_diversity": "high"
  },
  "interaction_style": {
    "sentiment_tendency": "positive",
    "positive_ratio": 0.8,
    "engagement_level": "high"
  },
  "last_updated": "2025-01-08T10:30:00",
  "analysis_version": "1.0"
}
```

## パーソナライゼーションの仕組み

### 1. 動的プロンプト調整
統計情報に基づいてシステムプロンプトを動的に調整します：

```python
# 例：宇宙が好きな常連さんの場合
【このユーザーの特徴】
- このユーザーは特に宇宙, 冒険について話すのが好きだ。
- いつもの時間に来てくれたことを認識している。
- 質問が多いユーザーなので、詳しく答える。
- 最近よく話してくれる常連さんとして親しみを込めて話す。
- 「LivingRoom-ESP32」（1F-Living）からの呼びかけだ。
```

### 2. 応答スタイル修飾子
デバイスの特性に応じて応答スタイルを調整：

```python
{
  "response_length": "long",    # 長い会話を好む
  "formality": "casual",        # カジュアルな口調
  "emotion_level": "high",      # 感情豊かに
  "detail_level": "high"        # 詳細な説明
}
```

## 使用方法

### 既存システムへの統合

```python
from enhanced_memory_system import EnhancedMemorySystem

# システムの初期化
memory_system = EnhancedMemorySystem()

# パーソナライズされたコンテキストの生成
context = memory_system.create_personalized_response_context(
    mac_address="D8:0F:99:D8:00:96",
    device_name="LivingRoom-ESP32",
    user_message="今日も宇宙の話を聞かせて",
    location="1F-Living",
    base_prompt=base_system_prompt
)

# GPTに送信
response = openai_client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": context},
        {"role": "user", "content": user_message}
    ]
)

# 会話の記録と統計更新
memory_system.add_conversation_with_analysis(
    mac_address, device_name, user_message, bot_response, location
)
```

## ファイル構成

```
conversation_memory_v2/
├── devices/
│   ├── {device_id}.json          # 会話履歴
│   └── ...
├── stats/
│   ├── {device_id}_stats.json    # 統計情報
│   └── ...
└── ...
```

## 今後の拡張可能性

1. **高度な自然言語処理**
   - MeCabやJANOMEを使った形態素解析
   - より正確なトピック抽出

2. **機械学習の活用**
   - 応答パターンの学習
   - 好みの予測

3. **マルチモーダル分析**
   - 音声の感情分析
   - 使用時間帯による気分推定

4. **グループ分析**
   - 複数デバイスの関係性分析
   - 家族やグループの傾向把握

## まとめ

このシステムにより、各ESP32デバイスとの会話がより自然で個別化されたものになります。デバイスごとの使用パターンを学習し、それぞれに最適な応答を提供することで、ユーザー体験が大幅に向上します。