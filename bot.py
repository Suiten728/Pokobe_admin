import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import asyncio

# .envからトークン読み込み
load_dotenv(dotenv_path="ci/.env")
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
if TOKEN is None:
    raise ValueError("DISCORD_BOT_TOKEN が見つかりません")

# Intents
intents = discord.Intents.all()

# 読み込むCog一覧
initial_cogs = [
    "cogs.ping",
    "cogs.eval",
    "cogs.add-emoji",
]

# Bot本体クラス
class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="P!",
            intents=intents,
            help_command=None
        )

    async def setup_hook(self):
        for cog in initial_cogs:
            try:
                await self.load_extension(cog)
                print(f"✅ Cogロード成功: {cog}")
            except Exception as e:
                print(f"❌ Cogロード失敗: {cog}\n{e}")
        synced = await self.tree.sync()
        print(f"✅ スラッシュコマンド登録数: {len(synced)}")

    async def on_ready(self):
        print(f"✅ ログイン完了: {self.user}")

# --- 起動処理 ---
async def main():
    bot = MyBot()
    await bot.start(TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Botを手動で停止しました。")