import discord
from discord.ext import commands
import json
import os

# JSONロード関数
def load_rules() -> dict:
    with open("data/rules.json", "r", encoding="utf-8") as f:
        return json.load(f)

# --- 言語選択メニュー ---
class RuleLanguageSelect(discord.ui.Select):
    def __init__(self, rules_data: dict):
        self.rules_data = rules_data
        options = [
            discord.SelectOption(label="日本語", value="ja", emoji="🇯🇵"),
            discord.SelectOption(label="English", value="en", emoji="🇺🇸"),
            discord.SelectOption(label="中文", value="zh", emoji="🇨🇳"),
            discord.SelectOption(label="한국어", value="ko", emoji="🇰🇷"),
            discord.SelectOption(label="Bahasa Indonesia", value="id", emoji="🇮🇩"),
        ]
        super().__init__(
            placeholder="🌐 言語を選択 / Select Language",
            options=options,
            custom_id="rules_lang_select"
        )

    async def callback(self, interaction: discord.Interaction):
        lang = self.values[0]
        text = self.rules_data.get(lang, "❌ この言語のルールは未設定です。")
        await interaction.response.send_message(text, ephemeral=True)

# --- 永続化View ---
class RulesView(discord.ui.View):
    def __init__(self, rules_data: dict):
        super().__init__(timeout=None)
        self.add_item(RuleLanguageSelect(rules_data))

# --- Cog ---
class RulesCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.rules_data = load_rules()

    @commands.command(name="post_rules")
    async def post_rules(self, ctx: commands.Context):
        """ルールを投稿するコマンド"""
        await ctx.send(self.rules_data["ja"], view=RulesView(self.rules_data))

    @commands.Cog.listener()
    async def on_ready(self):
        # 再起動後も動作するようにViewを登録
        self.bot.add_view(RulesView(self.rules_data))

async def setup(bot: commands.Bot):
    await bot.add_cog(RulesCog(bot))