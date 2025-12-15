import discord
from discord.ext import commands
from dotenv import load_dotenv
import os

load_dotenv(dotenv_path="ci/.env") # .envファイルをすべて読み込む
TARGET_CHANNEL_ID = int(os.getenv("EMOJI_ADD_CHANNEL_ID"))
EMOJIS = ["<:Welcome:1428991245107331235>", "👍"]  

class Emoji(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):

        channel = self.bot.get_channel(TARGET_CHANNEL_ID)
        if not channel:
            print("❌ チャンネルが見つかりません。")
            return

        try:
            async for message in channel.history(limit=50):
                if message.author.bot:
                    continue
                for emoji in EMOJIS:
                    already_reacted = False
                    for reaction in message.reactions:
                        if str(reaction.emoji) == emoji:
                            async for user in reaction.users():
                                if user.id == self.bot.user.id:
                                    already_reacted = True
                                    break
                    if not already_reacted:
                        await message.add_reaction(emoji)
                        print(f"🕘 リアクション追加 [{emoji}] -> {message.content[:30]}...")
        except Exception as e:
            print(f"❌ 過去メッセージへのリアクション失敗: {e}")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        if message.channel.id == TARGET_CHANNEL_ID:
            for emoji in EMOJIS:
                try:
                    await message.add_reaction(emoji)
                    print(f"➕ 新メッセージにリアクション [{emoji}] -> {message.content[:30]}...")
                except discord.HTTPException as e:
                    print(f"❌ リアクション失敗 [{emoji}]: {e}")

async def setup(bot):
    await bot.add_cog(Emoji(bot))
