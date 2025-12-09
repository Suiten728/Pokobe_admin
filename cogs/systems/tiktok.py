import discord
from discord.ext import commands, tasks
import json
import aiohttp
import os

from ci.setting import (
    RAPIDAPI_KEY,
    TIKTOK_API_URL,
    TIKTOK_USERNAME,
    DISCORD_WEBHOOK_URL,
    MENTION_ROLE_ID,
    CHECK_INTERVAL
)


class TikTokNotifyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.latest_file = "data/latest_video.json"
        self.check_tiktok.start()

    # ---- 最新動画 ID の保存/読み込み ----
    def load_last_video_id(self):
        if not os.path.exists(self.latest_file):
            return None
        with open(self.latest_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("video_id")

    def save_last_video_id(self, video_id):
        with open(self.latest_file, "w", encoding="utf-8") as f:
            json.dump({"video_id": video_id}, f, ensure_ascii=False, indent=2)

    # ---- TikTok API 呼び出し ----
    async def fetch_latest_video(self):
        headers = {
            "x-rapidapi-key": RAPIDAPI_KEY,
            "x-rapidapi-host": TIKTOK_API_URL.split("/")[2]
        }

        params = {"unique_id": TIKTOK_USERNAME, "count": 1}

        async with aiohttp.ClientSession() as session:
            async with session.get(TIKTOK_API_URL, headers=headers, params=params) as r:
                try:
                    data = await r.json()
                except:
                    print("❌ JSON 解析失敗")
                    return None

        try:
            # data → data → videos → 0
            video = data["data"]["videos"][0]

            return {
                "id": video["video_id"],
                "url": video["play"],   # 直接再生URL
                "desc": video["title"]
            }

        except Exception as e:
            print("❌ TikTok API フォーマットエラー:", data)
            return None

    # ---- Discord Webhook 送信 ----
    async def send_discord_notification(self, video):
        payload = {
            "username": "TikTok Notify",
            "content": (
                f"<@&{MENTION_ROLE_ID}> 新しい TikTok が投稿されました！\n"
                f"{video['desc']}\n{video['url']}"
            )
        }

        async with aiohttp.ClientSession() as session:
            await session.post(DISCORD_WEBHOOK_URL, json=payload)

    # ---- 定期実行ループ ----
    @tasks.loop(seconds=CHECK_INTERVAL)
    async def check_tiktok(self):
        print("🔍 TikTok チェック中…")
        latest = await self.fetch_latest_video()

        if latest is None:
            return

        last_saved = self.load_last_video_id()

        if latest["id"] != last_saved:
            print("📢 新しい動画を検出！Discordへ送信します")
            await self.send_discord_notification(latest)
            self.save_last_video_id(latest["id"])
        else:
            print("変化なし")

    @check_tiktok.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(TikTokNotifyCog(bot))
