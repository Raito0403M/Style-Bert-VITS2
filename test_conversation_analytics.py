#!/usr/bin/env python3
"""
会話分析システムのテストスクリプト
既存の会話データを分析し、統計情報を生成・表示
"""

import json
import logging
from pathlib import Path
from conversation_analytics import ConversationAnalyzer
from conversation_memory_v3 import get_conversation_memory_v3

def main():
    # ロギング設定
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("=== Conversation Analytics Test ===\n")
    
    # アナライザーを初期化
    analyzer = ConversationAnalyzer()
    
    # すべてのデバイスの統計を更新
    print("1. Updating all device statistics...")
    updated_count = analyzer.update_all_device_stats()
    print(f"   ✓ Updated {updated_count} device statistics\n")
    
    # 各デバイスの統計を表示
    print("2. Device Statistics Summary:\n")
    
    devices_dir = Path("conversation_memory_v2/devices")
    for device_file in devices_dir.glob("*.json"):
        if "_stats" in device_file.name:
            continue
            
        device_id = device_file.stem
        stats = analyzer.get_device_stats(device_id)
        
        if stats:
            print(f"   Device: {stats['device_name']} ({stats['mac_address']})")
            print(f"   - Total Conversations: {stats['total_conversations']}")
            print(f"   - Date Range: {stats['first_conversation'][:10]} to {stats['last_conversation'][:10]}")
            print(f"   - Favorite Topics: {', '.join(stats['favorite_topics'][:3])}")
            print(f"   - Peak Hours: {stats['peak_hours']}")
            print(f"   - Interaction Style: {stats['interaction_style']}")
            print(f"   - Daily Average: {stats['average_conversations_per_day']} conversations")
            print()
    
    # V3メモリシステムのテスト
    print("3. Testing ConversationMemoryV3 Integration:\n")
    
    memory = get_conversation_memory_v3()
    
    # テストデバイスを選択（最初に見つかったデバイス）
    test_device = None
    for device_file in devices_dir.glob("*.json"):
        if "_stats" not in device_file.name:
            try:
                with open(device_file, 'r', encoding='utf-8') as f:
                    conversations = json.load(f)
                    if conversations:
                        device_info = conversations[0]["device_info"]
                        test_device = {
                            "mac_address": device_info["mac_address"],
                            "device_name": device_info["device_name"],
                            "location": device_info.get("location")
                        }
                        break
            except:
                continue
    
    if test_device:
        print(f"   Testing with device: {test_device['device_name']}")
        
        # パーソナライズされたプロンプトを生成
        prompt = memory.create_personalized_prompt(
            test_device["mac_address"],
            test_device["device_name"],
            "テストメッセージ",
            test_device["location"]
        )
        
        print("\n   Personalized Context:")
        print("   " + prompt.replace("\n", "\n   "))
        
        # 会話の洞察を取得
        insights = memory.get_conversation_insights(
            test_device["mac_address"],
            test_device["device_name"]
        )
        
        print("\n   Conversation Insights:")
        print(f"   - Days Active: {insights['conversation_summary']['days_active']}")
        print(f"   - Vocabulary Richness: {insights['personality_profile']['vocabulary_richness']}")
        print(f"   - Curiosity Level: {insights['personality_profile']['question_curiosity']}")
        
        if insights['recommendations']:
            print(f"\n   Recommendations:")
            for rec in insights['recommendations']:
                print(f"   • {rec}")
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    main()