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

load_dotenv(dotenv_path="ci/.env") # .envファイルをすべて読み込む
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TARGET_CHANNEL_ID = int(os.getenv("AI_TARGET_CHANNEL_ID"))
AI_WEBHOOK_URL = os.getenv("AI_WEBHOOK_URL")
WEBHOOK_URL = str(os.getenv("AI_WEBHOOK_URL"))
WEBHOOK_NAME = os.getenv("WEBHOOK_NAME")
USER_MAX_LENGTH = int(os.getenv("USER_MAX_LENGTH"))
GEMINI_MAX_LENGTH = int(os.getenv("GEMINI_MAX_LENGTH"))

DEFAULT_CHARACTER = "data_public/ai-image.txt"
HOLO_JSON = "data_public/holomembers.json"

DB_PATH = "data/ai_memory.db"
MEMORY_LIMIT = 10  # 直近何往復分使うか


class TalkCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.init_db()

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

    # ===== Holomembers =====
    def load_holomembers(self):
        with open(HOLO_JSON, "r", encoding="utf-8") as f:
            return json.load(f)

    def resolve_name(self, text: str, members: dict):
        for official, aliases in members.items():
            if official in text:
                return official
            for a in aliases:
                if a in text:
                    return official
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

    # ===== Listener =====
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):

        if message.author.bot:
            return
        if message.channel.id != TARGET_CHANNEL_ID:
            return
        if not message.content.strip():
            return
        members = self.load_holomembers()
        found_name = self.resolve_name(message.content, members)

        with open(DEFAULT_CHARACTER, "r", encoding="utf-8") as f:
            system_prompt = f.read().strip()
        if not found_name:
            prompt = f"""
    {system_prompt}

    質問文に含まれる名前は、公式に確認できないでござる。
    JSONに存在する情報のみを元に、
    「分からないことは分からない」と優しく伝えてください。

    ユーザー: {message.content}
    """
        else:
            prompt = f"""
    {system_prompt}

    質問に含まれる人物は
    「{found_name}」でござる。

    JSONで確認できた正式名と一般的な呼び方を使い、
    風真いろはとして100〜200文字以内で答えてください。

    ユーザー: {message.content}
    """

        reply = await self.ask_gemini(prompt)
        reply = reply[:GEMINI_MAX_LENGTH]

        await self.post_webhook_reply(message, reply)



async def setup(bot):
    await bot.add_cog(TalkCog(bot))
