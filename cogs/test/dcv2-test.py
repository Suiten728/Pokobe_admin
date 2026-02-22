import discord
from discord.ext import commands
from discord import ui

class TestButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="embed内View",
            style=discord.ButtonStyle.primary,
            row=0  # レイアウト位置
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "送信に成功しました！",
            ephemeral=True
        )
        
class TestView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)

        # add_itemで部品を追加
        self.add_item(TestButton())

class Dcv2(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="dcv2")
    async def dcv2(self, ctx):

        embed = discord.Embed(
            title="dcv2テスト",
            description="これはテストです\n\n▼ 下のボタンを押してください"
        )

        await ctx.send(
            embed=embed,
            view=TestView()
        )


async def setup(bot):
    await bot.add_cog(Dcv2(bot))