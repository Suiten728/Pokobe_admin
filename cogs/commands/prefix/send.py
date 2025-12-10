import discord
from discord.ext import commands

class SendMessage(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="send")
    @commands.has_permissions(administrator=True)
    async def send(self, ctx, massage_id: int ,content: str):
        """指定したチャンネルにメッセージを送信します（管理者専用）"""
        try:
            channel = ctx.channel
            await channel.send(massage_id)
            await ctx.send(f"✅ メッセージを {channel.mention} に送信しました。", ephemeral=True)
        except Exception as e:
            await ctx.send(f"⛔ メッセージの送信に失敗しました: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(SendMessage(bot))