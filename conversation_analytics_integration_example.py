#!/usr/bin/env python3
"""
会話分析システムの統合例
Style-Bert-VITS2のボイス合成システムに統合する方法を示す
"""

import asyncio
from typing import Optional
from conversation_memory_v3 import get_conversation_memory_v3

class VoiceAssistantWithAnalytics:
    """分析機能を統合したボイスアシスタント"""
    
    def __init__(self):
        # メモリシステムを初期化（統計機能付き）
        self.memory = get_conversation_memory_v3()
        
    async def process_message(self, 
                            mac_address: str,
                            device_name: str,
                            user_message: str,
                            location: Optional[str] = None) -> str:
        """
        メッセージを処理し、パーソナライズされた応答を生成
        
        Args:
            mac_address: デバイスのMACアドレス
            device_name: デバイス名
            user_message: ユーザーからのメッセージ
            location: デバイスの設置場所
            
        Returns:
            生成された応答
        """
        
        # 1. パーソナライズされたコンテキストを生成
        context = self.memory.create_personalized_prompt(
            mac_address, device_name, user_message, location
        )
        
        # 2. デバイスの統計情報を取得
        stats = self.memory.get_device_stats(mac_address, device_name)
        
        # 3. 統計に基づいて応答スタイルを調整
        response_style = self._determine_response_style(stats)
        
        # 4. プロンプトを構築
        system_prompt = self._build_system_prompt(context, response_style, stats)
        
        # 5. ここで実際のLLM/TTS処理を行う（擬似コード）
        bot_response = await self._generate_response(system_prompt, user_message)
        
        # 6. 会話を記録（統計は自動更新される）
        self.memory.add_conversation(
            mac_address, device_name, user_message, bot_response, location
        )
        
        return bot_response
    
    def _determine_response_style(self, stats: Optional[dict]) -> dict:
        """統計情報から応答スタイルを決定"""
        if not stats:
            return {
                "energy": "normal",
                "formality": "casual",
                "topics": []
            }
        
        style = {
            "energy": "normal",
            "formality": "casual",
            "topics": stats.get("favorite_topics", [])
        }
        
        # インタラクションスタイルに基づいて調整
        interaction_style = stats.get("interaction_style", "casual")
        if interaction_style == "cheerful":
            style["energy"] = "high"
        elif interaction_style == "inquisitive":
            style["energy"] = "curious"
        
        # 時間帯に基づいて調整
        import datetime
        current_hour = datetime.datetime.now().hour
        if current_hour in stats.get("peak_hours", []):
            style["energy"] = "high"  # アクティブな時間帯
        
        return style
    
    def _build_system_prompt(self, context: str, style: dict, 
                           stats: Optional[dict]) -> str:
        """システムプロンプトを構築"""
        prompt_parts = [
            "あなたは「デカ子」という名前のフレンドリーなAIアシスタントです。",
            "語尾に「デカッ！」をつけて話します。",
            context
        ]
        
        # スタイルに基づく指示を追加
        if style["energy"] == "high":
            prompt_parts.append("\n◆ 今日は特に元気よく、明るく応答してください。")
        elif style["energy"] == "curious":
            prompt_parts.append("\n◆ 好奇心旺盛に、質問を交えながら応答してください。")
        
        # お気に入りの話題を優先
        if style["topics"]:
            topics_str = "、".join(style["topics"][:2])
            prompt_parts.append(f"\n◆ 可能であれば{topics_str}に関連する話題を含めてください。")
        
        # 統計に基づく追加の指示
        if stats and stats.get("average_conversations_per_day", 0) > 5:
            prompt_parts.append("\n◆ 頻繁に会話するユーザーなので、親しみやすく応答してください。")
        
        return "\n".join(prompt_parts)
    
    async def _generate_response(self, system_prompt: str, 
                               user_message: str) -> str:
        """実際の応答生成（ここではダミー）"""
        # 実際のアプリケーションではここでLLM APIを呼び出す
        # 例: response = await openai_api.complete(system_prompt, user_message)
        
        # ダミー応答
        if "宇宙" in user_message:
            return "宇宙の冒険はいつでも待ってるデカッ！デカコーンの星を目指して一緒に飛び立とうデカッ！"
        elif "天気" in user_message:
            return "今日はきっと冒険日和デカッ！外に出て大きな夢を追いかけようデカッ！"
        else:
            return "それは面白い話デカッ！もっと聞かせてほしいデカッ！"
    
    def get_device_insights(self, mac_address: str, device_name: str) -> dict:
        """デバイスの洞察情報を取得"""
        return self.memory.get_conversation_insights(mac_address, device_name)
    
    def export_device_report(self, mac_address: str, device_name: str) -> str:
        """デバイスのレポートをエクスポート"""
        report_path = self.memory.export_device_report(mac_address, device_name)
        return str(report_path)


# FastAPIとの統合例
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()
assistant = VoiceAssistantWithAnalytics()

class MessageRequest(BaseModel):
    mac_address: str
    device_name: str
    message: str
    location: Optional[str] = None

class MessageResponse(BaseModel):
    response: str
    context_used: bool
    stats_available: bool

@app.post("/api/chat", response_model=MessageResponse)
async def chat_endpoint(request: MessageRequest):
    """チャットエンドポイント"""
    try:
        # 応答を生成
        response = await assistant.process_message(
            request.mac_address,
            request.device_name,
            request.message,
            request.location
        )
        
        # 統計情報の有無をチェック
        stats = assistant.memory.get_device_stats(
            request.mac_address,
            request.device_name
        )
        
        return MessageResponse(
            response=response,
            context_used=True,
            stats_available=bool(stats)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stats/{device_id}")
async def get_stats_endpoint(device_id: str):
    """デバイスの統計情報を取得"""
    stats = assistant.memory.analyzer.get_device_stats(device_id)
    if not stats:
        raise HTTPException(status_code=404, detail="Stats not found")
    return stats

@app.get("/api/insights/{mac_address}/{device_name}")
async def get_insights_endpoint(mac_address: str, device_name: str):
    """デバイスの洞察情報を取得"""
    insights = assistant.get_device_insights(mac_address, device_name)
    return insights

@app.post("/api/stats/update")
async def update_all_stats():
    """すべてのデバイスの統計を更新"""
    updated = assistant.memory.analyzer.update_all_device_stats()
    return {"updated_devices": updated}


# 使用例
async def main():
    # アシスタントを初期化
    assistant = VoiceAssistantWithAnalytics()
    
    # テストメッセージを処理
    response = await assistant.process_message(
        mac_address="AA:BB:CC:DD:EE:FF",
        device_name="TestDevice",
        message="今日はどんな冒険をしようか？",
        location="Living Room"
    )
    
    print(f"Response: {response}")
    
    # デバイスの洞察を表示
    insights = assistant.get_device_insights("AA:BB:CC:DD:EE:FF", "TestDevice")
    print(f"\nInsights: {insights}")

if __name__ == "__main__":
    # CLIモードで実行
    asyncio.run(main())