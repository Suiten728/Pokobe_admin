# cogs/welcome.py
import discord
from discord.ext import commands
from discord import ui
import os
import io
import json
import aiohttp
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

# =========================
# Env / Config
# =========================
load_dotenv(dotenv_path="ci/.env")

WELCOME_CHANNEL_ID      = int(os.getenv("WELCOME_CHANNEL_ID"))
RULE_CHANNEL_ID         = int(os.getenv("RULE_CHANNEL_ID"))
AUTH_CHANNEL_ID         = int(os.getenv("AUTH_CHANNEL_ID"))
INTRO_CHANNEL_ID        = int(os.getenv("INTRO_CHANNEL_ID"))
GIDE_CHANNEL_ID         = int(os.getenv("GIDE_CHANNEL_ID")) 
VERIFY_SUPPORT_CHANNEL_ID = int(os.getenv("VERIFY_SUPPORT_CHANNEL_ID")) 

# =========================
# Files
# =========================
LANG_BY_GUILD    = "data/lang_by_guild.json"
LANG_MASTER_FILE = "data_public/languages.json"
WELCOME_BG_PATH  = "assets/welcome_bg.png"

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
def build_contents_for_lang(lang_code: str, guild_id: int) -> dict:
    lang = LANG_MASTER.get(lang_code, LANG_MASTER["jp"])
    return {
        "title":       lang["title"],
        "desc":        lang["desc"],
        "desc2":       lang["desc2"].format(
                           guild=guild_id,
                           rule=RULE_CHANNEL_ID,
                           guide=GIDE_CHANNEL_ID,
                       ),
        "desc3":       lang["desc3"].format(
                           auth=AUTH_CHANNEL_ID,
                           verify_support=VERIFY_SUPPORT_CHANNEL_ID,
                       ),
        "desc4":       lang["desc4"].format(intro=INTRO_CHANNEL_ID),
        "desc5_label": lang["desc5_label"],
        "desc6_label": lang["desc6_label"],
        "desc7_label": lang["desc7_label"],
        "rule_btn":    lang["rule_btn"],
        "auth_btn":    lang["auth_btn"],
        "intro_btn":   lang["intro_btn"],
        "lang_label":  lang["lang_label"],
        "lang_desc":   lang["lang_desc"],
    }

# =========================
# Welcome Card 画像生成（Pillow）
# assets/welcome_bg.png にユーザーアバター・ユーザー名を合成する
# =========================
def _get_font(size: int) -> ImageFont.FreeTypeFont:
    """日本語対応フォントを探してロードする。見つからなければデフォルト。"""
    candidates = [
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJKjp-Regular.otf",
        "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()

async def generate_welcome_card(member: discord.Member) -> bytes:
    """ウェルカムカード画像を生成して PNG bytes で返す"""
    # 背景画像
    bg = Image.open(WELCOME_BG_PATH).convert("RGBA")
    bg_w, bg_h = bg.size

    # アバター取得
    async with aiohttp.ClientSession() as session:
        async with session.get(str(member.display_avatar.url)) as resp:
            avatar_bytes = await resp.read()

    # アバターを円形に切り抜き
    avatar_size = min(bg_h // 2, 120)  # 背景サイズに合わせてスケール
    avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA").resize((avatar_size, avatar_size))
    mask = Image.new("L", (avatar_size, avatar_size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, avatar_size, avatar_size), fill=255)
    avatar.putalpha(mask)

    # アバター貼り付け位置（縦中央・左寄り）
    av_x = 30
    av_y = (bg_h - avatar_size) // 2
    bg.paste(avatar, (av_x, av_y), avatar)

    # ユーザー名テキスト描画
    draw = ImageDraw.Draw(bg)
    font_name = _get_font(32)
    font_tag  = _get_font(20)

    name_text = member.display_name
    tag_text  = f"@{member.name}"
    text_x    = av_x + avatar_size + 20
    name_y    = av_y + avatar_size // 2 - 28
    tag_y     = name_y + 42

    # 影
    draw.text((text_x + 2, name_y + 2), name_text, font=font_name, fill=(0, 0, 0, 160))
    draw.text((text_x + 2, tag_y  + 2), tag_text,  font=font_tag,  fill=(0, 0, 0, 120))
    # 本文
    draw.text((text_x, name_y), name_text, font=font_name, fill=(255, 255, 255, 255))
    draw.text((text_x, tag_y),  tag_text,  font=font_tag,  fill=(200, 200, 200, 220))

    output = io.BytesIO()
    bg.convert("RGBA").save(output, format="PNG")
    output.seek(0)
    return output.read()

# =========================
# Component v2 JSON Builder
# card_url=None  → attachment://welcome_card.png（初回送信時）
# card_url=<str> → CDN URL（言語切り替え時の既存添付ファイル参照）
# =========================
def build_components_json(guild_id: int, lang_code: str = "jp", card_url: str | None = None) -> list:
    c = build_contents_for_lang(lang_code, guild_id)

    image_url = card_url if card_url else "attachment://welcome_card.png"

    return [
        {
            "type": 17,                # Container
            "accent_color": 0x5865F2,  # blurple
            "components": [

                # ── ウェルカムカード画像 ──────────────────────────────
                {
                    "type": 12,  # MediaGallery
                    "items": [{"media": {"url": image_url}}],
                },

                # ── タイトル・説明 ────────────────────────────────────
                {"type": 10, "content": f"## {c['title']}"},
                {"type": 10, "content": c["desc"]},

                {"type": 14, "spacing": 2},  # Separator large

                # ── チャンネル案内（テキスト） ─────────────────────────
                {"type": 10, "content": c["desc2"]},
                {"type": 10, "content": c["desc3"]},
                {"type": 10, "content": c["desc4"]},

                {"type": 14, "spacing": 1},  # Separator small

                # ── ルールボタン（Section: 右端にボタン） ─────────────
                {
                    "type": 9,  # Section
                    "components": [
                        {"type": 10, "content": c["desc5_label"]},
                    ],
                    "accessory": {
                        "type": 2, "style": 5,
                        "label": c["rule_btn"],
                        "url": f"https://discord.com/channels/{guild_id}/{RULE_CHANNEL_ID}",
                    },
                },

                # ── 認証ボタン ────────────────────────────────────────
                {
                    "type": 9,  # Section
                    "components": [
                        {"type": 10, "content": c["desc6_label"]},
                    ],
                    "accessory": {
                        "type": 2, "style": 5,
                        "label": c["auth_btn"],
                        "url": f"https://discord.com/channels/{guild_id}/{AUTH_CHANNEL_ID}",
                    },
                },

                # ── 自己紹介ボタン ────────────────────────────────────
                {
                    "type": 9,  # Section
                    "components": [
                        {"type": 10, "content": c["desc7_label"]},
                    ],
                    "accessory": {
                        "type": 2, "style": 5,
                        "label": c["intro_btn"],
                        "url": f"https://discord.com/channels/{guild_id}/{INTRO_CHANNEL_ID}",
                    },
                },

                {"type": 14, "spacing": 2},  # Separator large

                # ── 言語選択 ──────────────────────────────────────────
                {"type": 10, "content": f"### {c['lang_label']}"},
                {"type": 10, "content": c["lang_desc"]},
                {
                    "type": 1,  # ActionRow
                    "components": [
                        {
                            "type": 3,  # StringSelect
                            "custom_id": f"welcome_lang_select:{guild_id}",
                            "placeholder": "🌐 Select Language / 改变语言",
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
            placeholder="🌐 Select Language / 改变语言",
            options=options,
            min_values=1,
            max_values=1,
            custom_id=f"welcome_lang_select:{guild_id}",
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        selected = self.values[0]

        # 言語設定を保存
        data = load_guild_lang()
        data[str(self.guild_id)] = selected
        save_guild_lang(data)

        await interaction.response.defer()

        # 既存の添付画像 URL を取得して MediaGallery に再利用する
        card_url = None
        if interaction.message and interaction.message.attachments:
            card_url = interaction.message.attachments[0].url

        await interaction.client.http.request(
            discord.http.Route(
                "PATCH",
                "/channels/{channel_id}/messages/{message_id}",
                channel_id=interaction.channel_id,
                message_id=interaction.message.id,
            ),
            json={
                "flags": 1 << 15,
                "components": build_components_json(self.guild_id, selected, card_url=card_url),
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
            # ウェルカムカード画像を生成
            img_bytes = await generate_welcome_card(member)

            # multipart で送信（画像 + Component v2）
            form = aiohttp.FormData()
            form.add_field(
                "payload_json",
                json.dumps({
                    "flags": 1 << 15,
                    "content": member.mention,
                    "attachments": [{"id": 0, "filename": "welcome_card.png"}],
                    "components": build_components_json(member.guild.id, lang),
                }),
                content_type="application/json",
            )
            form.add_field(
                "files[0]",
                img_bytes,
                filename="welcome_card.png",
                content_type="image/png",
            )

            await self.bot.http.request(
                discord.http.Route(
                    "POST",
                    "/channels/{channel_id}/messages",
                    channel_id=ch.id,
                ),
                data=form,
            )
            print("[DEBUG] 送信成功")

        except Exception as e:
            print(f"[DEBUG] 送信エラー: {e}")


# =========================
# setup
# =========================
async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(WelcomeCog(bot))
