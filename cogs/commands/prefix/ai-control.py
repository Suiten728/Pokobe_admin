import discord
from discord.ext import commands

class TalkControlCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # TalkCog が最初から稼働状態であることを保証
        if not hasattr(self.bot, "talk_enabled"):
            self.bot.talk_enabled = True

    @commands.command(name="ai_status")
    async def ai_status(self, ctx):
        status = "🟢 **稼働中**" if self.bot.talk_enabled else "🔴 **緊急停止中**"
        await ctx.reply(f"現在のAI状態：{status}", mention_author=False)

    @commands.command(name="ai_off")
    @commands.has_permissions(administrator=True)
    async def ai_off(self, ctx):
        self.bot.talk_enabled = False
        await ctx.reply("⚠️ **AIを緊急停止しました。**", mention_author=False)

    @commands.command(name="ai_on")
    @commands.has_permissions(administrator=True)
    async def ai_on(self, ctx):
        self.bot.talk_enabled = True
        await ctx.reply("🔄 **AIを再始動しました。**", mention_author=False)


async def setup(bot):
    await bot.add_cog(TalkControlCog(bot))
