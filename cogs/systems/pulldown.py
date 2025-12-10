import discord
from discord.ext import commands
import json
import os

# JSONロード関数
def load_posts() -> dict:
    with open("ci/data/texts.json", "r", encoding="utf-8") as f:
        return json.load(f)

# --- 言語選択メニュー ---
class LanguageSelect(discord.ui.Select):
    def __init__(self, item_data: dict):
        self.item_data = item_data
        options = [
            discord.SelectOption(label="English", value="en", emoji="🇺🇸"),
            discord.SelectOption(label="中文", value="zh", emoji="🇨🇳"),
            discord.SelectOption(label="한국어", value="ko", emoji="🇰🇷"),
            discord.SelectOption(label="Bahasa Indonesia", value="id", emoji="🇮🇩"),
            discord.SelectOption(label="Español", value="es", emoji="🇪🇸"),
            discord.SelectOption(label="العربية", value="ar", emoji="🇸🇦"),
        ]
        super().__init__(
            placeholder="🌐 言語を変更 | Change Language",
            options=options,
            custom_id="dynamic_lang_select"
        )

    async def callback(self, interaction: discord.Interaction):
        lang = self.values[0]
        text = self.item_data.get(lang, "❌ この言語は未設定です。")
        await interaction.response.send_message(text, ephemeral=True)

# --- 永続View ---
class PostView(discord.ui.View):
    def __init__(self, item_data: dict):
        super().__init__(timeout=None)
        self.add_item(LanguageSelect(item_data))

# --- Cog ---
class DynamicPostCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.data = load_posts()

    @commands.command(name="post")
    async def post(self, ctx: commands.Context, item_name: str):
        """
        JSON内の任意の項目を送信するコマンド。
        例: !post rules
        """
        item = self.data.get(item_name)

        if item is None:
            await ctx.send(f"❌ `{item_name}` は JSON に存在しません。")
            return

        # 日本語がなければランダム or 最初の言語でもOK
        text = item.get("ja") or next(iter(item.values()))

        await ctx.send(text, view=PostView(item))

    @commands.Cog.listener()
    async def on_ready(self):
        # 再起動後のため全 View を登録
        for item_data in self.data.values():
            self.bot.add_view(PostView(item_data))

async def setup(bot: commands.Bot):
    await bot.add_cog(DynamicPostCog(bot))
