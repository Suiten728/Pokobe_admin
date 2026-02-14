import json
import aiohttp
import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import asyncio
import traceback
import sqlite3
from datetime import datetime

load_dotenv(dotenv_path="ci/.env")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TARGET_CHANNEL_ID = int(os.getenv("AI_TARGET_CHANNEL_ID"))
AI_WEBHOOK_URL = os.getenv("AI_WEBHOOK_URL")
WEBHOOK_URL = str(os.getenv("AI_WEBHOOK_URL"))
WEBHOOK_NAME = os.getenv("WEBHOOK_NAME")
USER_MAX_LENGTH = int(os.getenv("USER_MAX_LENGTH"))
GEMINI_MAX_LENGTH = int(os.getenv("GEMINI_MAX_LENGTH"))

# データファイルパス
PROFILE_JSON = "data/profile.json"
RELATIONSHIPS_JSON = "data/relationships.json"
JOKES_JSON = "data/jokes.json"
SYSTEM_PROMPT_TXT = "data/system_prompt.txt"

DB_PATH = "data/ai_memory.db"
MEMORY_LIMIT = 5  # 直近5往復分（v1.14仕様）

# 検索判定キーワード（v1.14仕様）
SEARCH_KEYWORDS = [
    "最新", "今日", "今", "ニュース", "株価", "価格", 
    "何年設立", "説明して", "いつ", "現在"
]


class TalkCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.init_db()
        
        # AI稼働状態の初期化
        if not hasattr(self.bot, "talk_enabled"):
            self.bot.talk_enabled = True

    # ===== DB =====
    def init_db(self):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id INTEGER,
                role TEXT,
                content TEXT,
                timestamp TEXT
            )
        """)
        conn.commit()
        conn.close()

    def save_memory(self, channel_id: int, role: str, content: str):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            "INSERT INTO memory (channel_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
            (channel_id, role, content, datetime.utcnow().isoformat())
        )
        conn.commit()
        conn.close()

    def load_memory(self, channel_id: int) -> str:
        """直近5往復分の会話履歴を取得"""
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            "SELECT role, content FROM memory WHERE channel_id=? ORDER BY id DESC LIMIT ?",
            (channel_id, MEMORY_LIMIT * 2)
        )
        rows = c.fetchall()
        conn.close()

        rows.reverse()
        lines = []
        for role, content in rows:
            prefix = "ユーザー" if role == "user" else "AI"
            lines.append(f"{prefix}: {content}")

        return "\n".join(lines)

    # ===== JSONデータ読み込み =====
    def load_profile(self):
        """profile.jsonを読み込み"""
        try:
            with open(PROFILE_JSON, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def load_relationships(self):
        """relationships.jsonを読み込み"""
        try:
            with open(RELATIONSHIPS_JSON, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def load_jokes(self):
        """jokes.jsonを読み込み"""
        try:
            with open(JOKES_JSON, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def load_system_prompt(self):
        """system_prompt.txtを読み込み"""
        try:
            with open(SYSTEM_PROMPT_TXT, "r", encoding="utf-8") as f:
                return f.read().strip()
        except FileNotFoundError:
            return "あなたは風真いろはです。語尾は「でござる」を使ってください。"

    # ===== 検索判定 =====
    def needs_search(self, text: str) -> bool:
        """検索が必要かどうかを判定"""
        for keyword in SEARCH_KEYWORDS:
            if keyword in text:
                return True
        return False

    # ===== 人物名解決 =====
    def resolve_person(self, text: str, relationships: dict):
        """テキストから人物名を解決"""
        for person_name in relationships.keys():
            if person_name in text:
                return person_name
        return None

    # ===== ネタ検出 =====
    def check_jokes(self, text: str, jokes: dict):
        """ネタキーワードをチェック"""
        for joke_key, joke_data in jokes.items():
            keywords = joke_data.get("keywords", [])
            for keyword in keywords:
                if keyword in text:
                    return joke_data
        return None

    # ===== Gemini =====
    async def ask_gemini(self, prompt: str) -> str:
        url = "https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash-lite:generateContent"

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"maxOutputTokens": GEMINI_MAX_LENGTH}
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                params={"key": GEMINI_API_KEY},
                json=payload,
                timeout=30
            ) as resp:

                text = await resp.text()
                if resp.status != 200:
                    return "（AI 応答エラー）"

                data = json.loads(text)
                return data["candidates"][0]["content"]["parts"][0]["text"]

    # ===== Webhook =====
    async def post_webhook_reply(self, message: discord.Message, content: str):
        payload = {
            "content": content,
            "username": WEBHOOK_NAME,
            "allowed_mentions": {"parse": []},
            "message_reference": {
                "message_id": str(message.id),
                "channel_id": str(message.channel.id)
            }
        }

        async with aiohttp.ClientSession() as session:
            await session.post(WEBHOOK_URL, json=payload)

    # ===== プロンプト構築 =====
    def build_prompt(self, user_input: str, channel_id: int, profile: dict, 
                     relationships: dict, jokes: dict, system_prompt: str):
        """v1.14仕様に沿ったプロンプトを構築"""
        
        # 会話履歴取得
        history = self.load_memory(channel_id)
        
        # プロフィール情報を文字列化
        profile_str = json.dumps(profile, ensure_ascii=False, indent=2)
        
        # ネタ検出（優先処理）
        joke_data = self.check_jokes(user_input, jokes)
        if joke_data:
            responses = joke_data.get("response", [])
            if responses:
                # ネタ反応がある場合は、それを優先的に使うように明示
                joke_instruction = f"""
🎯 【重要：ネタ反応モード】
ユーザーの入力にネタキーワードが含まれています！
以下の反応から1つを選んで、風真いろはらしくアレンジして返答してください：

{chr(10).join(f"- {r}" for r in responses)}

この反応を必ず使って、100文字前後で自然に返答してください。
"""
                prompt = f"""{system_prompt}

{joke_instruction}

【ユーザー入力】
{user_input}
"""
                return prompt
        
        # 人物名解決
        person_name = self.resolve_person(user_input, relationships)
        person_info = ""
        if person_name:
            rel_data = relationships[person_name]
            person_info = f"""
【認識した人物】
名前: {person_name}
呼び方: {rel_data.get('call', person_name)}
話し方: {rel_data.get('speech', 'casual')}

この人物について話す場合は、上記の呼び方と話し方を必ず使ってください。
"""
        
        # 検索判定
        search_info = ""
        if self.needs_search(user_input):
            search_info = """
⚠️ 【検索が必要な質問です】
この質問は「最新」「今日」などのキーワードを含んでいます。
現在の情報は持っていないので、「今はわからないでござる」「最新情報は確認できないでござる」
などと正直に伝えてください。
"""
        
        # 最終プロンプト（通常モード）
        prompt = f"""{system_prompt}

【プロフィール情報】
{profile_str}

【会話履歴】
{history if history else "（まだ履歴がありません）"}
{person_info}
{search_info}

【ユーザー入力】
{user_input}

上記の情報を踏まえて、風真いろはとして100〜200文字以内で返答してください。
"""
        return prompt

    # ===== Listener =====
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Bot自身のメッセージは無視
        if message.author.bot:
            return
        
        # 指定チャンネル以外は無視
        if message.channel.id != TARGET_CHANNEL_ID:
            return
        
        # 空メッセージは無視
        if not message.content.strip():
            return
        
        # AI停止中は無視
        if not self.bot.talk_enabled:
            return

        try:
            # データ読み込み
            profile = self.load_profile()
            relationships = self.load_relationships()
            jokes = self.load_jokes()
            system_prompt = self.load_system_prompt()
            
            # ユーザー入力を保存
            user_input = message.content[:USER_MAX_LENGTH]
            self.save_memory(message.channel.id, "user", user_input)
            
            # プロンプト構築
            prompt = self.build_prompt(
                user_input, 
                message.channel.id,
                profile, 
                relationships, 
                jokes, 
                system_prompt
            )
            
            # Geminiに問い合わせ
            reply = await self.ask_gemini(prompt)
            reply = reply[:GEMINI_MAX_LENGTH]
            
            # AI返答を保存
            self.save_memory(message.channel.id, "assistant", reply)
            
            # Webhookで返信
            await self.post_webhook_reply(message, reply)
            
        except Exception as e:
            print(f"エラー発生: {e}")
            traceback.print_exc()


async def setup(bot):
    await bot.add_cog(TalkCog(bot))