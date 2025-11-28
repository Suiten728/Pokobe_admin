import json
import aiohttp
import discord
from discord.ext import commands
from data.config import (
    GEMINI_API_KEY, TARGET_CHANNEL_ID,
    WEBHOOK_URL, WEBHOOK_NAME,
    USER_MAX_LENGTH, GEMINI_MAX_LENGTH,
    DEFAULT_CHARACTER
)
import asyncio
import traceback

class TalkCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def ask_gemini(self, prompt: str) -> str:
        url = "https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent"

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ],
            "generationConfig": {
                "maxOutputTokens": GEMINI_MAX_LENGTH
            }
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    params={"key": GEMINI_API_KEY},
                    json=payload,
                    timeout=30
                ) as resp:

                    text = await resp.text()

                    if resp.status != 200:
                        return f"【Gemini API エラー】status={resp.status}\n{text}"

                    data = json.loads(text)

                    try:
                        return data["candidates"][0]["content"]["parts"][0]["text"]
                    except Exception:
                        return "（Gemini の応答パースに失敗しました）"

        except asyncio.TimeoutError:
            return "（通信タイムアウト：Gemini への接続が遅延しました）"

        except Exception as e:
            return f"（通信エラー：{e})"

    async def post_webhook_reply(self, message: discord.Message, content: str) -> bool:
        """
        Webhook エンドポイントに直接 POST して、message_reference を付けて Reply 表示させる。
        戻り値: True = 成功, False = 失敗
        """
        # content は長すぎないように制限
        payload = {
            "content": content,
            # username を与えると webhook 側のデフォルト名を上書きする（これがユーザーの要望）
            "username": WEBHOOK_NAME,
            # アイコンは送らない => Discord に設定した webhook 側のアイコンが使われる
            # "avatar_url": None,
            "allowed_mentions": {"parse": []},
            # message_reference を付けて「reply」として振る舞わせる
            "message_reference": {
                "message_id": str(message.id),
                "channel_id": str(message.channel.id)
                # guild_id を入れてもよいが不要なことが多い
            }
        }

        headers = {"Content-Type": "application/json"}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(WEBHOOK_URL, json=payload, headers=headers, timeout=15) as resp:
                    # Discord は 200 か 204 を返すことがある。200なら JSON 返却（メッセージオブジェクト）
                    if resp.status in (200, 204):
                        return True
                    else:
                        text = await resp.text()
                        # ログ出力
                        print(f"Webhook POST failed: status={resp.status} text={text}")
                        return False
        except Exception as e:
            print("Webhook POST exception:", e)
            traceback.print_exc()
            return False

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # 基本ガード
        if message.author.bot:
            return

        # チャンネルガード
        if message.channel.id != TARGET_CHANNEL_ID:
            return

        # 文字数ガード
        if not message.content or message.content.strip() == "":
            return  # 空メッセージは無視
        if len(message.content) > USER_MAX_LENGTH:
            try:
                await message.reply(f"⛔ メッセージが長すぎます（{USER_MAX_LENGTH}文字以内）", mention_author=False)
            except Exception:
                pass
            return

        # キャラ設定を読み込む（毎回読み直すことで、ファイル差し替えが即反映される）
        try:
            with open(DEFAULT_CHARACTER, "r", encoding="utf-8") as f:
                character_prompt = f.read().strip()
        except Exception as e:
            print("キャラ読み込み失敗:", e)
            character_prompt = "あなたは親切なAIです。"

        full_prompt = f"{character_prompt}\n\nユーザー: {message.content}\nAI:"
        # Gemini に投げる
        reply_text = await self.ask_gemini(full_prompt)
        if not reply_text:
            reply_text = "（応答が空でした）"

        # 長さ制限
        if len(reply_text) > GEMINI_MAX_LENGTH:
            reply_text = reply_text[:GEMINI_MAX_LENGTH] + "…"

        # まず Webhook で Reply を試す
        ok = await self.post_webhook_reply(message, reply_text)
        if not ok:
            # フォールバック：Bot 自身で reply を返す（確実にユーザーに返信が届く）
            try:
                await message.reply(f"(Webhook 送信失敗のため代替返信)\n{reply_text}", mention_author=False)
            except Exception as e:
                # 最終的にログ出力して黙る（ここまで来たら環境依存の問題）
                print("代替 reply 失敗:", e)
                traceback.print_exc()


async def setup(bot):
    await bot.add_cog(TalkCog(bot))
