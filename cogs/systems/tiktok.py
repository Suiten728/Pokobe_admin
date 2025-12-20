import discord
from discord.ext import commands, tasks
import json
import aiohttp
from datetime import datetime, timezone
import pytz
import os
from dotenv import load_dotenv
load_dotenv(dotenv_path="ci/.env")

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
TIKTOK_API_URL = os.getenv("TIKTOK_API_URL")
TIKTOK_API_HOST = os.getenv("TIKTOK_API_HOST")
TIKTOK_USERNAME = os.getenv("TIKTOK_USERNAME")
TIKTOK_WEBHOOK_URL = os.getenv("TIKTOK_WEBHOOK_URL")

TIKTOK_MENTION_ROLE_ID = int(os.getenv("TIKTOK_MENTION_ROLE_ID"))
JST = pytz.timezone("Asia/Tokyo")

# ======================
# Cog 本体
# ======================
class TikTokNotifyCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.latest_file = "data/latest_video.json"

        # data ディレクトリ保証
        os.makedirs("data", exist_ok=True)

    # ------------------
    # Cog ロード時に開始
    # ------------------
    async def cog_load(self):
        print("✅ TikTokNotifyCog loaded")
        self.check_tiktok.start()

    # ------------------
    # 最新動画 ID 保存 / 読み込み
    # ------------------
    def load_last_video_id(self):
        if not os.path.exists(self.latest_file):
            return None

        try:
            with open(self.latest_file, "r", encoding="utf-8") as f:
                return json.load(f).get("video_id")
        except Exception as e:
            print("❌ latest_video.json 読み込み失敗:", e)
            return None

    def save_last_video_id(self, video_id: str):
        with open(self.latest_file, "w", encoding="utf-8") as f:
            json.dump(
                {"video_id": video_id},
                f,
                ensure_ascii=False,
                indent=2
            )

    # ------------------
    # TikTok API 呼び出し
    # ------------------
    async def fetch_latest_video(self):
        headers = {
            "x-rapidapi-key": RAPIDAPI_KEY,
            "x-rapidapi-host": TIKTOK_API_HOST
        }

        params = {
            "unique_id": TIKTOK_USERNAME,
            "count": 1
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(
                TIKTOK_API_URL,
                headers=headers,
                params=params
            ) as r:
                try:
                    data = await r.json()
                except Exception as e:
                    print("❌ JSON 解析失敗:", e)
                    return None

        try:
            # ※ RapidAPI の仕様差異に対応しやすい書き方
            video = data["data"]["videos"][0]

            video_id = video.get("video_id")

            return {
                "id": video_id,
                "url": f"https://www.tiktok.com/@{TIKTOK_USERNAME}/video/{video_id}",
                "desc": video.get("title", "（説明なし）"),
                "thumbnail": video.get("cover") or video.get("origin_cover")
            }

        except Exception as e:
            print("❌ TikTok API フォーマットエラー:", e)
            return None

    # ------------------
    # Discord Webhook 送信
    # ------------------
    async def send_discord_notification(self, video: dict):
        payload = {
            "content": f"<@&{TIKTOK_MENTION_ROLE_ID}>",
            "embeds": [
                {
                    "color": 0x0000ff, # 青色
                    "author": {
                        "name": "TikTokで最新動画が投稿されました！",
                    "url": f"https://www.tiktok.com/@{TIKTOK_USERNAME}"
                },
                "title": video["desc"] or "新しい動画",
                "url": video["url"],
                "image": {
                    "url": video.get("thumbnail")
                },
                "footer": {
                    "text": "Published",
                    "icon_url": "https://sapph.xyz/images/socials/sapphire_tiktok.png"
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        ]
    }

        async with aiohttp.ClientSession() as session:
            async with session.post(TIKTOK_WEBHOOK_URL, json=payload) as r:
                print("📨 Webhook status:", r.status)
    # ------------------
    # 定期チェック
    # ------------------
    @tasks.loop(seconds=60)
    async def check_tiktok(self):
        now = datetime.now(JST)
        hour = now.hour
        minute = now.minute

        interval = self.get_interval_seconds(hour)

        # 前回チェック時刻を記録しておく
        if not hasattr(self, "last_check"):
         self.last_check = None

        if self.last_check:
            diff = (now - self.last_check).total_seconds()
            if diff < interval:
                return

        self.last_check = now
        latest = await self.fetch_latest_video()
        if latest is None or latest.get("id") is None:
            return

        last_saved = self.load_last_video_id()
        if latest["id"] != last_saved:
            await self.send_discord_notification(latest)
            self.save_last_video_id(latest["id"])

    @check_tiktok.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()

    def get_interval_seconds(self, hour: int) -> int:
        # 朝 09–15
        if 9 <= hour <= 15:
            return 2700   # 45分

        # 昼 16–20
        if 16 <= hour <= 20:
            return 900    # 15分

        # 夜 21–8
        return 7200       # 2時間

async def setup(bot: commands.Bot):
    await bot.add_cog(TikTokNotifyCog(bot))
