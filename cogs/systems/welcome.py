# cogs/welcome.py
import discord
from discord.ext import commands
from discord import ui
import os
import json
from dotenv import load_dotenv

# =========================
# Env / Config
# =========================
load_dotenv(dotenv_path="ci/.env")

WELCOME_CHANNEL_ID = int(os.getenv("WELCOME_CHANNEL_ID"))
RULE_CHANNEL_ID = int(os.getenv("RULE_CHANNEL_ID"))
AUTH_CHANNEL_ID = int(os.getenv("AUTH_CHANNEL_ID"))
INTRO_CHANNEL_ID = int(os.getenv("INTRO_CHANNEL_ID"))

# =========================
# Files
# =========================
LANG_BY_GUILD = "data/lang_by_guild.json"
LANG_MASTER_FILE = "data_public/languages.json"

os.makedirs("data", exist_ok=True)

with open(LANG_MASTER_FILE, "r", encoding="utf-8") as f:
    LANG_MASTER = json.load(f)

if not os.path.exists(LANG_BY_GUILD):
    with open(LANG_BY_GUILD, "w", encoding="utf-8") as f:
        json.dump({}, f, ensure_ascii=False, indent=4)

def load_guild_lang():
    with open(LANG_BY_GUILD, "r", encoding="utf-8") as f:
        return json.load(f)

def save_guild_lang(data: dict):
    with open(LANG_BY_GUILD, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# =========================
# Content Builder
# =========================
def build_contents_for_lang(lang_code: str):
    lang = LANG_MASTER.get(lang_code, LANG_MASTER["jp"])

    return {
        "title": lang["title"],
        "desc": lang["desc"],
        "auth": lang["auth"].format(auth=AUTH_CHANNEL_ID),
        "intro": lang["intro"].format(intro=INTRO_CHANNEL_ID),
        "warn": lang["warn"],
        "rule_btn": lang["rule_btn"],
        "auth_btn": lang["auth_btn"],
        "intro_btn": lang["intro_btn"],
        "lang_label": lang["lang_label"],
        "divider": lang.get("divider", "──────────────────────────")
    }

# =========================
# cv2 availability
# =========================
USE_LAYOUT = hasattr(ui, "LayoutView") and hasattr(ui, "Section") and hasattr(ui, "TextDisplay")

# =========================
# Language Select
# =========================
class GuildLanguageSelect(ui.Select):
    def __init__(self, guild_id: int):
        self.guild_id = guild_id

        options = [
            discord.SelectOption(label="日本語", value="jp", emoji="🇯🇵"),
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
            placeholder="🌐 言語を選択 / Select Language",
            options=options,
            min_values=1,
            max_values=1,
            custom_id=f"welcome_lang_select:{guild_id}",
        )

    async def callback(self, interaction: discord.Interaction):
        data = load_guild_lang()
        data[str(self.guild_id)] = self.values[0]
        save_guild_lang(data)

        new_view = build_view_for_guild(self.guild_id, self.values[0])
        await interaction.response.edit_message(view=new_view)

# =========================
# View Builder
# =========================
def build_view_for_guild(guild_id: int, lang_code: str = "jp"):
    if not USE_LAYOUT:
        # safety fallback（基本ここは通らない）
        return ui.View(timeout=None)

    content = build_contents_for_lang(lang_code)
    view = ui.LayoutView(timeout=None)
   
    view.add_item(
    ui.Section(
        ui.TextDisplay("WELCOME"),
        key="test"
    )
)

    # Language select
    view.add_item(GuildLanguageSelect(guild_id))

    return view

# =========================
# Cog
# =========================
class WelcomeCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        print("JOIN:", member)

        ch = member.guild.get_channel(WELCOME_CHANNEL_ID)
        print("CHANNEL:", ch)
        print("WELCOME_CHANNEL_ID =", WELCOME_CHANNEL_ID)
        print("GUILD CHANNELS =", [c.id for c in member.guild.channels])

        await ch.send(view=view)


# =========================
# setup
# =========================
async def setup(bot: commands.Bot):
    await bot.add_cog(WelcomeCog(bot))

    # persistent views
    for guild in bot.guilds:
        lang = load_guild_lang().get(str(guild.id), "jp")
        bot.add_view(build_view_for_guild(guild.id, lang))
