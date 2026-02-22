import discord
from discord.ext import commands


# --- LayoutView本体 ---
class ContactView(discord.ui.LayoutView):

    def __init__(self):
        super().__init__()

        # タイトル
        title = discord.ui.TextDisplay(
            "## お問い合わせ"
        )

        # 説明文
        description = discord.ui.TextDisplay(
            "このサーバーに関する質問などはこちらから選択してください。"
        )

        # セレクトメニュー
        select = discord.ui.Select(
            placeholder="カテゴリを選択してください",
            options=[
                discord.SelectOption(label="質問", description="サーバーに関する質問"),
                discord.SelectOption(label="バグ報告", description="不具合の報告"),
            ],
        )

        # コンテナ（緑カード部分）
        container = discord.ui.Container(
            title,
            description,
            select,
            accent_color=discord.Color.green()
        )

        # Viewに追加
        self.add_item(container)


# --- Cog ---
class Dcv2(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="dcv2")
    async def dcv2(self, ctx):
        await ctx.send(view=ContactView())


async def setup(bot):
    await bot.add_cog(Dcv2(bot))
