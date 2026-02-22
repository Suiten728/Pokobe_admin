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
        "title":      lang["title"],
        "desc":       lang["desc"],
        "auth":       lang["auth"].format(auth=AUTH_CHANNEL_ID),
        "intro":      lang["intro"].format(intro=INTRO_CHANNEL_ID),
        "warn":       lang["warn"],
        "rule_btn":   lang["rule_btn"],
        "auth_btn":   lang["auth_btn"],
        "intro_btn":  lang["intro_btn"],
        "lang_label": lang["lang_label"],
    }

# =========================
# Component v2 JSON Builder
# LayoutView の self.container をインスタンス変数で組むと
# to_components() が空を返すため、JSON を直接組み立てて HTTP 送信する
# =========================
def build_components_json(guild_id: int, lang_code: str = "jp") -> list:
    c = build_contents_for_lang(lang_code)
    return [
        {
            "type": 17,                # Container
            "accent_color": 0x5865F2,  # blurple
            "components": [
                # タイトル・説明
                {"type": 10, "content": f"## {c['title']}"},
                {"type": 10, "content": c["desc"]},
                {"type": 14, "spacing": 2},   # Separator large
                # チャンネル案内
                {"type": 10, "content": c["auth"]},
                {"type": 10, "content": c["intro"]},
                {"type": 14, "spacing": 1},   # Separator small
                # 注意書き
                {"type": 10, "content": c["warn"]},
                {"type": 14, "spacing": 2},   # Separator large
                # チャンネルリンクボタン
                {
                    "type": 1,  # ActionRow
                    "components": [
                        {
                            "type": 2, "style": 5,
                            "label": c["rule_btn"],
                            "url": f"https://discord.com/channels/{guild_id}/{RULE_CHANNEL_ID}",
                        },
                        {
                            "type": 2, "style": 5,
                            "label": c["auth_btn"],
                            "url": f"https://discord.com/channels/{guild_id}/{AUTH_CHANNEL_ID}",
                        },
                        {
                            "type": 2, "style": 5,
                            "label": c["intro_btn"],
                            "url": f"https://discord.com/channels/{guild_id}/{INTRO_CHANNEL_ID}",
                        },
                    ],
                },
                # 言語セレクトラベル
                {"type": 10, "content": f"-# {c['lang_label']}"},
                # 言語セレクト
                {
                    "type": 1,  # ActionRow
                    "components": [
                        {
                            "type": 3,  # StringSelect
                            "custom_id": f"welcome_lang_select:{guild_id}",
                            "placeholder": "🌐 言語を選択 / Select Language",
                            "min_values": 1,
                            "max_values": 1,
                            "options": [
                                {"label": "日本語",             "value": "jp",    "emoji": {"name": "🇯🇵"}},
                                {"label": "English",            "value": "en",    "emoji": {"name": "🇺🇸"}},
                                {"label": "中文",               "value": "zh",    "emoji": {"name": "🇨🇳"}},
                                {"label": "한국어",              "value": "ko",    "emoji": {"name": "🇰🇷"}},
                                {"label": "Français",           "value": "fr",    "emoji": {"name": "🇫🇷"}},
                                {"label": "Deutsch",            "value": "de",    "emoji": {"name": "🇩🇪"}},
                                {"label": "Bahasa Indonesia",   "value": "id",    "emoji": {"name": "🇮🇩"}},
                                {"label": "Español",            "value": "es",    "emoji": {"name": "🇪🇸"}},
                                {"label": "Português (Brasil)", "value": "pt_BR", "emoji": {"name": "🇧🇷"}},
                            ],
                        }
                    ],
                },
            ],
        }
    ]

# =========================
# Language Select（永続化用）
# add_view に渡すためだけに定義。
# callback 内では interaction.client.http で直接 PATCH する。
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
            custom_id=f"welcome_lang_select:{guild_id}",  # 永続化のため固定
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        selected = self.values[0]

        # 言語設定を保存
        data = load_guild_lang()
        data[str(self.guild_id)] = selected
        save_guild_lang(data)

        # まず defer（応答しないと "インタラクションに失敗しました" になる）
        await interaction.response.defer()

        # Component v2 フラグ付きで PATCH
        await interaction.client.http.request(
            discord.http.Route(
                "PATCH",
                "/channels/{channel_id}/messages/{message_id}",
                channel_id=interaction.channel_id,
                message_id=interaction.message.id,
            ),
            json={
                "flags": 1 << 15,
                "components": build_components_json(self.guild_id, selected),
            }
        )


class PersistentSelectView(ui.View):
    """add_view 登録専用。GuildLanguageSelect の callback を有効にするためだけに存在する。"""
    def __init__(self, guild_id: int):
        super().__init__(timeout=None)
        self.add_item(GuildLanguageSelect(guild_id))


# =========================
# Cog
# =========================
class WelcomeCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        # 永続化: Bot 再起動後もセレクトが反応するよう全ギルド分登録
        lang_data = load_guild_lang()
        for guild in self.bot.guilds:
            lang = lang_data.get(str(guild.id), "jp")
            self.bot.add_view(PersistentSelectView(guild.id))
            print(f"[INFO] add_view 登録: guild={guild.id} lang={lang}")

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        print(f"[DEBUG] on_member_join 発火: {member} / guild: {member.guild.id}")

        ch = member.guild.get_channel(WELCOME_CHANNEL_ID)
        if ch is None:
            print(f"[DEBUG] チャンネルが見つかりません: {WELCOME_CHANNEL_ID}")
            return

        lang = load_guild_lang().get(str(member.guild.id), "jp")
        print(f"[DEBUG] 言語: {lang}")

        try:
            await self.bot.http.request(
                discord.http.Route(
                    "POST",
                    "/channels/{channel_id}/messages",
                    channel_id=ch.id,
                ),
                json={
                    "flags": 1 << 15,       # IS_COMPONENTS_V2
                    "components": build_components_json(member.guild.id, lang),
                }
            )
            print("[DEBUG] 送信成功")
        except Exception as e:
            print(f"[DEBUG] 送信エラー: {e}")


# =========================
# setup
# =========================
async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(WelcomeCog(bot))
