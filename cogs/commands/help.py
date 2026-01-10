import discord
from discord.ext import commands
import json
from typing import Dict

HELP_LANGUAGE_FILE = "data_public/help-language.json"


# ---------- JSONロード ----------
def load_help_data() -> Dict[str, dict]:
    with open(HELP_LANGUAGE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------- 言語セレクト ----------
class LanguageSelect(discord.ui.Select):
    def __init__(self, help_data: dict):
        self.help_data = help_data

        options = [
            discord.SelectOption(label="日本語", value="ja", emoji="🇯🇵"),
            discord.SelectOption(label="English", value="en", emoji="🇺🇸"),
            discord.SelectOption(label="中文", value="zh", emoji="🇨🇳"),
            discord.SelectOption(label="한국어", value="ko", emoji="🇰🇷"),
            discord.SelectOption(label="Français", value="fr", emoji="🇫🇷"),
            discord.SelectOption(label="Deutsch", value="de", emoji="🇩🇪"),
            discord.SelectOption(label="Bahasa Indonesia", value="id", emoji="🇮🇩"),
            discord.SelectOption(label="Español", value="es", emoji="🇪🇸"),
            discord.SelectOption(label="Português (Brasil)", value="pt_BR", emoji="🇧🇷"),
        ]

        super().__init__(
            placeholder="🌐 言語を選択 | Select Language",
            options=options,
            custom_id="help_language_select"
        )

    async def callback(self, interaction: discord.Interaction):
        lang = self.values[0]
        data = self.help_data.get(lang)

        if not data:
            await interaction.response.send_message(
                "❌ この言語は未対応です。",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title=data["title"],
            description=data["description"],
            color=discord.Color.blue()
        )

        for field in data["fields"]:
            embed.add_field(
                name=field["name"],
                value=field["value"],
                inline=False
            )

        await interaction.response.edit_message(embed=embed)


# ---------- View ----------
class HelpView(discord.ui.View):
    def __init__(self, help_data: dict):
        super().__init__(timeout=None)
        self.add_item(LanguageSelect(help_data))


# ---------- Cog ----------
class Help(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.help_data = load_help_data()

    @commands.hybrid_command(
        name="help",
        description="ヘルプメニューを表示します"
    )
    async def help(self, ctx: commands.Context):
        # デフォルト言語：日本語
        data = self.help_data.get("ja")

        embed = discord.Embed(
            title=data["title"],
            description=data["description"],
            color=discord.Color.blue()
        )

        for field in data["fields"]:
            embed.add_field(
                name=field["name"],
                value=field["value"],
                inline=False
            )

        await ctx.send(
            embed=embed,
            view=HelpView(self.help_data)
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Help(bot))