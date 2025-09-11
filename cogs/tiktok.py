import discord
from discord.ext import commands, tasks
from TikTokApi import TikTokApi
import aiohttp
import json
import os

from dotenv import load_dotenv

# .envからウェブフック読み込み
load_dotenv(dotenv_path="ci/.env")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
if WEBHOOK_URL is None:
    raise ValueError("WEBHOOK_URL が見つかりません")

USERNAME = "kazamairoha_hololive"
STATE_FILE = "data/last_video.json"

def get_last_video_id():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f).get("last_video_id")
    return None

def save_last_video_id(video_id):
    with open(STATE_FILE, "w") as f:
        json.dump({"last_video_id": video_id}, f)

class TikTokNotifier(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_tiktok.start()  # 起動時にタスク開始

    def cog_unload(self):
        self.check_tiktok.cancel()

    @tasks.loop(minutes=5)  # 5分ごとにチェック
    async def check_tiktok(self):
        async with aiohttp.ClientSession() as session:
            with TikTokApi() as api:
                try:
                    user = api.user(username=USERNAME)
                    videos = user.videos(count=1)
                    if not videos:
                        return

                    video = videos[0]
                    video_id = video.id
                    title = video.desc or "No title"
                    url = f"https://www.tiktok.com/@{USERNAME}/video/{video_id}"

                    last_video_id = get_last_video_id()

                    if video_id != last_video_id:  # 新しい動画なら送信
                        payload = {"content": f"📢 {USERNAME} がTikTokで新しい動画を投稿しました！\n**{title}**\n{url}"}
                        await session.post(WEBHOOK_URL, json=payload)
                        save_last_video_id(video_id)
                except Exception as e:
                    print(f"エラー: {e}")

async def setup(bot):
    await bot.add_cog(TikTokNotifier(bot))
