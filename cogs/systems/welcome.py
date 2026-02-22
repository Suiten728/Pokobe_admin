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
RULE_CHANNEL_ID    = int(os.getenv("RULE_CHANNEL_ID"))
AUTH_CHANNEL_ID    = int(os.getenv("AUTH_CHANNEL_ID"))
INTRO_CHANNEL_ID   = int(os.getenv("INTRO_CHANNEL_ID"))

# =========================
# Files
# =========================
LANG_BY_GUILD    = "data/lang_by_guild.json"
LANG_MASTER_FILE = "data_public/languages.json"

os.makedirs("data", exist_ok=True)

with open(LANG_MASTER_FILE, "r", encoding="utf-8") as f:
    LANG_MASTER = json.load(f)

if not os.path.exists(LANG_BY_GUILD):
    with open(LANG_BY_GUILD, "w", encoding="utf-8") as f:
        json.dump({}, f, ensure_ascii=False, indent=4)

def load_guild_lang() -> dict:
    with open(LANG_BY_GUILD, "r", encoding="utf-8") as f:
        return json.load(f)

def save_guild_lang(data: dict) -> None:
    with open(LANG_BY_GUILD, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# =========================
# Content Builder
# =========================
def build_contents_for_lang(lang_code: str) -> dict:
    lang = LANG_MASTER.get(lang_code, LANG_MASTER["jp"])
    return {
        "title":     lang["title"],
        "desc":      lang["desc"],
        "auth":      lang["auth"].format(auth=AUTH_CHANNEL_ID),
        "intro":     lang["intro"].format(intro=INTRO_CHANNEL_ID),
        "warn":      lang["warn"],
        "rule_btn":  lang["rule_btn"],
        "auth_btn":  lang["auth_btn"],
        "intro_btn": lang["intro_btn"],
        "lang_label": lang["lang_label"],
    }

# =========================
# Buttons（リンクボタン / サブクラス化）
# ノート: LayoutView ではデコレータ不可 → Button をサブクラス化して ActionRow に入れる
# リンクボタンは url を渡すだけ、callback 不要・custom_id 不可
# =========================
class RuleButton(ui.Button):
    def __init__(self, label: str, guild_id: int):
        super().__init__(
            label=label,
            style=discord.ButtonStyle.link,
            url=f"https://discord.com/channels/{guild_id}/{RULE_CHANNEL_ID}",
        )

class AuthButton(ui.Button):
    def __init__(self, label: str, guild_id: int):
        super().__init__(
            label=label,
            style=discord.ButtonStyle.link,
            url=f"https://discord.com/channels/{guild_id}/{AUTH_CHANNEL_ID}",
        )

class IntroButton(ui.Button):
    def __init__(self, label: str, guild_id: int):
        super().__init__(
            label=label,
            style=discord.ButtonStyle.link,
            url=f"https://discord.com/channels/{guild_id}/{INTRO_CHANNEL_ID}",
        )

# =========================
# Language Select（サブクラス化）
# ノート: Select をサブクラス化して callback を定義、ActionRow に入れる
# custom_id はギルド単位で固定 → 永続化対応
# =========================
class GuildLanguageSelect(ui.Select):
    def __init__(self, guild_id: int):
        self.guild_id = guild_id
        options = [
            discord.SelectOption(label="日本語",             value="jp",    emoji="🇯🇵"),
            discord.SelectOption(label="English",            value="en",    emoji="🇺🇸"),
            discord.SelectOption(label="中文",               value="zh",    emoji="🇨🇳"),
            discord.SelectOption(label="한국어",              value="ko",    emoji="🇰🇷"),
            discord.SelectOption(label="Français",           value="fr",    emoji="🇫🇷"),
            discord.SelectOption(label="Deutsch",            value="de",    emoji="🇩🇪"),
            discord.SelectOption(label="Bahasa Indonesia",   value="id",    emoji="🇮🇩"),
            discord.SelectOption(label="Español",            value="es",    emoji="🇪🇸"),
            discord.SelectOption(label="Português (Brasil)", value="pt_BR", emoji="🇧🇷"),
        ]
        super().__init__(
            placeholder="🌐 言語を選択 / Select Language",
            options=options,
            min_values=1,
            max_values=1,
            custom_id=f"welcome_lang_select:{guild_id}",  # ← 永続化のため固定
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        selected = self.values[0]

        # 言語設定を保存
        data = load_guild_lang()
        data[str(self.guild_id)] = selected
        save_guild_lang(data)

        # メッセージを新しい言語の View で更新
        new_view = WelcomeView(self.guild_id, selected)
        await interaction.response.defer()
        await interaction.edit_original_response()

# =========================
# WelcomeView（LayoutView）
# ノート: Container / TextDisplay / Separator / ActionRow で構成
#        Embed との共存不可 → Embed は使わず Container に統合
#        timeout=None 必須（永続化）
#        動的コンテンツのため __init__ 内で self.container を組み立てる
# =========================
class WelcomeView(ui.LayoutView):
    def __init__(self, guild_id: int, lang_code: str = "jp"):
        super().__init__(timeout=None)
        c = build_contents_for_lang(lang_code)

        self.container = ui.Container(
            # タイトル・説明
            ui.TextDisplay(f"## {c['title']}"),
            ui.TextDisplay(c["desc"]),
            ui.Separator(spacing=discord.SeparatorSpacing.large),
            # チャンネル案内
            ui.TextDisplay(c["auth"]),
            ui.TextDisplay(c["intro"]),
            ui.Separator(spacing=discord.SeparatorSpacing.small),
            # 注意書き
            ui.TextDisplay(c["warn"]),
            ui.Separator(spacing=discord.SeparatorSpacing.large),
            # チャンネルリンクボタン（1行にまとめる）
            ui.ActionRow(
                RuleButton(c["rule_btn"],  guild_id),
                AuthButton(c["auth_btn"],  guild_id),
                IntroButton(c["intro_btn"], guild_id),
            ),
            # 言語セレクト
            ui.TextDisplay(f"-# {c['lang_label']}"),
            ui.ActionRow(GuildLanguageSelect(guild_id)),
            accent_colour=discord.Colour.blurple(),
        )

# =========================
# Cog
# =========================
class WelcomeCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        print(f"[DEBUG] on_member_join 発火: {member} / guild: {member.guild.id}")
        ch = member.guild.get_channel(WELCOME_CHANNEL_ID)
        print(f"[DEBUG] チャンネル取得結果: {ch}")
        print(f"[DEBUG] WELCOME_CHANNEL_ID: {WELCOME_CHANNEL_ID}")
        if ch is None:
            print("[DEBUG] チャンネルが None のため return")
            return

        lang = load_guild_lang().get(str(member.guild.id), "jp")
        view = WelcomeView(member.guild.id, lang)
        
        print(f"[DEBUG] 言語: {lang}")
        try:
             await self.bot.http.request(
                 discord.http.Route("POST", "/channels/{channel_id}/messages", channel_id=ch.id),
                 json={
                     "flags": 1 << 15,
                     "components": view.to_components(),
                 }
             )
            print("[DEBUG] 送信成功")
        except Exception as e:
            print(f"[DEBUG] 送信エラー: {e}")

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        # 永続化: Bot 再起動後もセレクトが反応するよう全ギルド分登録
        # ノート: custom_id を固定 + timeout=None + on_ready で add_view
        lang_data = load_guild_lang()
        for guild in self.bot.guilds:
            lang = lang_data.get(str(guild.id), "jp")
            self.bot.add_view(WelcomeView(guild.id, lang))

# =========================
# setup
# =========================
async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(WelcomeCog(bot))




