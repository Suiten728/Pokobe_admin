import discord
from discord.ext import commands, tasks
from TikTokApi import TikTokApi
import aiohttp
import json
import os

WEBHOOK_URL = "https://discord.com/api/webhooks/1412831660185096333/xUSZbCxCNtCL-e1s5uRsS_7JzigzMYN0sLSU9w9XBrqv474n5v-CpOkI84vPUv_p68bq"
USERNAME = "kazamairoha_hololive"
STATE_FILE = "last_video.json"

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
