# Conversation Analytics Design Documentation

## Overview

This document describes the design and implementation of the conversation analytics system for Style-Bert-VITS2. The system analyzes conversation history to generate meaningful statistics and insights for each device, enabling personalized interactions.

## Architecture

### Core Components

1. **ConversationAnalyzer** (`conversation_analytics.py`)
   - Main analytics engine
   - Performs topic extraction, pattern analysis, and sentiment analysis
   - Generates comprehensive statistics per device

2. **ConversationMemoryV3** (`conversation_memory_v3.py`)
   - Extends V2 with integrated analytics
   - Provides real-time stats updates
   - Enhanced personalization using statistical insights

3. **StatsUpdateScheduler**
   - Manages periodic and on-demand updates
   - Optimizes performance by avoiding unnecessary recalculations

## Metrics Tracked

### 1. Topic Analysis
- **Favorite Topics**: Top 5 most discussed topics
- **Topic Frequencies**: Count of each topic category
- **Keyword Cloud**: Most frequent keywords with counts
- **Location-based Topics**: Topics preferred in specific locations
- **Time-based Topics**: Topics discussed during different time periods

### 2. Time Patterns
- **Hourly Distribution**: Conversation frequency by hour
- **Daily Distribution**: Conversation frequency by day of week
- **Peak Hours**: Top 3 most active hours
- **Average Conversations per Day**: Daily conversation rate

### 3. Conversation Patterns
- **Common Greetings**: Frequently used greeting patterns
- **Question Types**: Classification of questions (what, when, where, etc.)
- **Average Message Length**: Character count statistics
- **User Vocabulary Size**: Unique keywords used

### 4. Sentiment Analysis
- **Sentiment Distribution**: Percentage of positive/negative/neutral messages
- **Interaction Style**: Overall conversation style (cheerful, inquisitive, etc.)

## Topic Extraction Methods

### Japanese Language Processing
1. **MeCab Integration**: Morphological analysis for accurate keyword extraction
2. **Fallback Method**: Pattern matching for systems without MeCab
3. **Topic Categories**: Predefined categories with associated keywords

### Keyword Extraction Pipeline
```python
1. Text Input → MeCab Analysis → Part-of-speech filtering
2. Extract nouns, verbs, and adjectives
3. Filter by length and relevance
4. Count frequencies and identify patterns
```

## Update Strategies

### 1. Real-time Updates
- Triggered after each conversation
- Only updates if last update > 30 minutes ago
- Minimal performance impact

### 2. Periodic Updates
- Scheduled every 60 minutes
- Updates all devices with new conversations
- Runs in background

### 3. On-demand Updates
- Manual trigger via API
- Force update regardless of last update time
- Used for immediate stat requirements

## File Structure

### Stats File Location
```
conversation_memory_v2/
├── devices/
│   ├── {device_id}.json          # Conversation history
│   └── {device_id}_stats.json    # Device statistics (legacy)
└── stats/
    └── {device_id}_stats.json    # Primary stats location
```

### Stats File Schema
```json
{
  "device_id": "string",
  "device_name": "string",
  "mac_address": "string",
  "total_conversations": "number",
  "first_conversation": "ISO 8601 timestamp",
  "last_conversation": "ISO 8601 timestamp",
  "update_timestamp": "ISO 8601 timestamp",
  
  "favorite_topics": ["array of top topics"],
  "topic_frequencies": {"topic": count},
  "keyword_cloud": {"keyword": count},
  
  "hourly_distribution": {"hour": count},
  "daily_distribution": {"day": count},
  "peak_hours": [array of hours],
  "average_conversations_per_day": "number",
  
  "common_greetings": ["array of greetings"],
  "question_types": {"type": count},
  "average_message_length": "number",
  "user_vocabulary_size": "number",
  
  "sentiment_distribution": {"sentiment": percentage},
  "interaction_style": "string",
  
  "location_based_topics": {"location": ["topics"]},
  "time_based_topics": {"time_period": ["topics"]}
}
```

## Implementation Example

### Basic Usage
```python
from conversation_memory_v3 import get_conversation_memory_v3

# Initialize system
memory = get_conversation_memory_v3()

# Add a conversation (stats update automatically)
memory.add_conversation(
    mac_address="AA:BB:CC:DD:EE:FF",
    device_name="Kitchen-ESP32",
    user_message="今日の天気はどう？",
    bot_response="今日は晴れデカッ！",
    location="Kitchen"
)

# Get device statistics
stats = memory.get_device_stats("AA:BB:CC:DD:EE:FF", "Kitchen-ESP32")

# Get personalized context
context = memory.create_personalized_prompt(
    mac_address="AA:BB:CC:DD:EE:FF",
    device_name="Kitchen-ESP32",
    user_message="新しいメッセージ"
)

# Get conversation insights
insights = memory.get_conversation_insights("AA:BB:CC:DD:EE:FF", "Kitchen-ESP32")
```

### Manual Stats Update
```python
from conversation_analytics import ConversationAnalyzer

analyzer = ConversationAnalyzer()
analyzer.update_all_device_stats()
```

## Performance Considerations

1. **Caching**: Stats are cached and only updated when necessary
2. **Incremental Updates**: Only processes new conversations
3. **Background Processing**: Long operations run asynchronously
4. **File I/O Optimization**: Batch reads/writes when possible

## Future Enhancements

1. **Machine Learning Integration**
   - Topic modeling using LDA or similar
   - Automatic conversation clustering
   - Predictive response suggestions

2. **Advanced Sentiment Analysis**
   - Emotion detection beyond positive/negative
   - Context-aware sentiment scoring
   - Multi-turn conversation sentiment tracking

3. **Conversation Quality Metrics**
   - Engagement scoring
   - Conversation depth analysis
   - Response relevance metrics

4. **Export Formats**
   - CSV export for data analysis
   - Visualization dashboard
   - Weekly/monthly reports

## API Endpoints (Proposed)

```python
# Get device statistics
GET /api/stats/{device_id}

# Force update statistics
POST /api/stats/{device_id}/update

# Get all devices summary
GET /api/stats/summary

# Export device report
GET /api/stats/{device_id}/export
```