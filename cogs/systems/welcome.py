# cogs/welcome.py
import discord
from discord.ext import commands
from discord import ui
import aiohttp
from PIL import Image, ImageDraw, ImageFont
import io
import os
import json
import random
import logging
logger = logging.getLogger("welcome_cog")
from dotenv import load_dotenv

load_dotenv() # .envファイルを読み込む
secret_key = os.getenv(
    "WELCOME_CHANNEL_ID",
    "RULE_CHANNEL_ID",
    "AUTH_CHANNEL_ID",
    "INTRO_CHANNEL_ID",
    "BG_PATH",
    "FONT_PATH"
)

# 永続化ファイル
LANG_BY_GUILD = "data/lang_by_guild.json"
LANG_MASTER_FILE = "data/languages.json"
os.makedirs("data", exist_ok=True)

# load master language file
with open(LANG_MASTER_FILE, "r", encoding="utf-8") as f:
    LANG_MASTER = json.load(f)

# ensure guild lang file exists
if not os.path.exists(LANG_BY_GUILD):
    with open(LANG_BY_GUILD, "w", encoding="utf-8") as f:
        json.dump({}, f, ensure_ascii=False, indent=4)

def load_guild_lang():
    with open(LANG_BY_GUILD, "r", encoding="utf-8") as f:
        return json.load(f)

def save_guild_lang(d):
    with open(LANG_BY_GUILD, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=4)

# ---------- 画像合成 ----------
async def create_welcome_image(member: discord.Member):
    # 背景
    try:
        bg = Image.open(BG_PATH).convert("RGBA")
    except Exception:
        # fallback blank
        bg = Image.new("RGBA", (1024, 520), (24, 24, 24, 255))

    # avatar fetch (use display_avatar to get dynamic)
    avatar_url = str(member.display_avatar.url)
    async with aiohttp.ClientSession() as session:
        async with session.get(avatar_url) as resp:
            avatar_bytes = await resp.read()

    avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")

    # make circular and larger (360px)
    size = 360
    avatar = avatar.resize((size, size))
    mask = Image.new("L", (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.ellipse((0, 0, size, size), fill=255)
    avatar.putalpha(mask)

    bg_w, bg_h = bg.size
    pos_x = (bg_w - size) // 2
    pos_y = 30
    bg.paste(avatar, (pos_x, pos_y), avatar)

    # draw username under avatar
    try:
        font = ImageFont.truetype(FONT_PATH, 56)
    except Exception:
        font = ImageFont.load_default()

    draw = ImageDraw.Draw(bg)
    name = member.display_name
    # center text
    try:
        text_w = draw.textlength(name, font=font)
    except Exception:
        text_w = font.getsize(name)[0]

    text_x = (bg_w - text_w) / 2
    text_y = pos_y + size + 18
    # outline then fill
    for dx, dy in [(-2,-2),(2,-2),(-2,2),(2,2)]:
        draw.text((text_x+dx, text_y+dy), name, font=font, fill=(0,0,0))
    draw.text((text_x, text_y), name, font=font, fill=(255,255,255))

    # return BytesIO
    bio = io.BytesIO()
    bg.save(bio, "PNG")
    bio.seek(0)
    return bio

# ---------- Helpers to build embed-like content ----------
def build_contents_for_lang(lang_code: str, guild_id: int):
    lang = LANG_MASTER.get(lang_code, LANG_MASTER.get("ja"))
    # fill channel placeholders with actual IDs
    auth_txt = lang.get("auth", "").format(auth=AUTH_CHANNEL_ID)
    intro_txt = lang.get("intro", "").format(intro=INTRO_CHANNEL_ID)
    return {
        "title": lang.get("title"),
        "desc": lang.get("desc"),
        "auth": auth_txt,
        "intro": intro_txt,
        "warn": lang.get("warn"),
        "rule_btn": lang.get("rule_btn"),
        "auth_btn": lang.get("auth_btn"),
        "intro_btn": lang.get("intro_btn"),
        "lang_label": lang.get("lang_label"),
        "divider": lang.get("divider", "──────────────────────────")
    }

# ---------- LayoutView / embed-like UI ----------
# Use LayoutView and Section/TextDisplay when available (discord.py v2.6+)
USE_LAYOUT = hasattr(ui, "LayoutView") and hasattr(ui, "Section")

ParentView = ui.LayoutView if USE_LAYOUT else ui.View

class WelcomeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _do_send_welcome(self, member: discord.Member):
        """共通の送信処理。例外は呼び出し元でキャッチする"""
        # find channel
        ch = member.guild.get_channel(WELCOME_CHANNEL_ID)
        if ch is None:
            raise RuntimeError(f"WELCOME_CHANNEL not found (id={WELCOME_CHANNEL_ID}) in guild {member.guild.id}")

        # guild language
        guild_langs = load_guild_lang()
        lang_code = guild_langs.get(str(member.guild.id), "ja")

        # create image
        img_bio = await create_welcome_image(member)
        filename = f"welcome_{member.id}.png"

        # create embed (random color)
        content = build_contents_for_lang(lang_code, member.guild.id)
        color = random.randint(0, 0xFFFFFF)
        embed = discord.Embed(title=content["title"], description=content["desc"], color=color)
        embed.add_field(name="\u200b", value=content["divider"], inline=False)
        embed.add_field(name="\u200b", value=f"{content['auth']}\n{content['intro']}\n{content['warn']}", inline=False)
        embed.add_field(name="\u200b", value=content["divider"], inline=False)
        embed.add_field(name="\u200b", value=(
            f"📖 {content['rule_btn']} 　🔘\n"
            f"🏵 {content['auth_btn']} 　🔘\n"
            f"📝 {content['intro_btn']} 　🔘"
        ), inline=False)
        embed.add_field(name="\u200b", value=content["divider"], inline=False)
        embed.add_field(name=content["lang_label"], value="以下のプルダウンで言語を切替できます。", inline=False)

        embed.set_image(url=f"attachment://{filename}")

        view = build_view_for_guild(member.guild.id, lang_code)

        # send and return message
        return await ch.send(embed=embed, file=discord.File(fp=img_bio, filename=filename), view=view)


    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        # ignore bots
        if member.bot:
            logger.debug(f"Ignored bot member join: {member} ({member.id})")
            return

        logger.info(f"on_member_join fired for {member} ({member.id}) in guild {member.guild.id}")

        try:
            # quick permission check
            ch = member.guild.get_channel(WELCOME_CHANNEL_ID)
            if ch is None:
                logger.warning(f"WELCOME channel not found for guild {member.guild.id} (id {WELCOME_CHANNEL_ID})")
                return

            perms = ch.permissions_for(member.guild.me or member.guild.get_member(self.bot.user.id))
            logger.debug(f"Bot perms in channel {ch.id}: send_messages={perms.send_messages}, embed_links={perms.embed_links}, attach_files={perms.attach_files}")

            if not (perms.send_messages and perms.embed_links and perms.attach_files):
                logger.warning("Bot missing required permissions in the welcome channel.")
                return

            msg = await self._do_send_welcome(member)
            logger.info(f"Welcome message sent: {msg.id} in channel {ch.id}")

        except Exception as e:
            # Log exception with stack trace so you can paste it here
            logger.exception("Failed to send welcome message")

        # ---- 管理者用コマンド（同じ Cog 内に追加） ----
    @commands.command(name="force_welcome")
    @commands.has_permissions(administrator=True)
    async def force_welcome(self, ctx, member: discord.Member = None):
        """管理者向け：指定したメンバー（またはコマンド実行者）にテストでウェルカムを送る"""
        target = member or ctx.author
        try:
            await ctx.send("Sending test welcome...")
            msg = await self._do_send_welcome(target)
            await ctx.send(f"Test welcome sent: {msg.jump_url}")
        except Exception as e:
            await ctx.send(f"Failed to send test welcome: {e}")
            raise

        except Exception as e:
            print(f"Error in force_welcome: {e}")


# Custom select/listener with persistent custom_id per guild
class GuildLanguageSelect(ui.Select):
    def __init__(self, guild_id: int):
        options = [
            discord.SelectOption(label="日本語", value="ja",emoji="🇯🇵"),
            discord.SelectOption(label="English", value="en",emoji="🇺🇸"),
            discord.SelectOption(label="中文", value="zh",emoji="🇨🇳"),
            discord.SelectOption(label="한국어", value="ko",emoji="🇰🇷"),
            discord.SelectOption(label="Bahasa Indonesia", value="id",emoji="🇮🇩"),
            discord.SelectOption(label="Español", value="es",emoji="🇪🇸"),
            discord.SelectOption(label="العربية", value="ar",emoji="🇸🇦"),
        ]
        # custom_id includes guild to allow persistent multiple guilds
        custom_id = f"welcome_lang_select_{guild_id}"
        super().__init__(placeholder="🌐 言語を選択 / Select Language", min_values=1, max_values=1, options=options, custom_id=custom_id)
        self.guild_id = guild_id

    async def callback(self, interaction: discord.Interaction):
        # save selection
        data = load_guild_lang()
        data[str(self.guild_id)] = self.values[0]
        save_guild_lang(data)

        # rebuild embed-like content
        lang = data.get(str(self.guild_id), "ja")
        content = build_contents_for_lang(lang, self.guild_id)

        # create embed (with random color)
        color = random.randint(0, 0xFFFFFF)
        embed = discord.Embed(title=content["title"], description=content["desc"], color=color)
        embed.add_field(name="\u200b", value=content["divider"], inline=False)
        embed.add_field(name="\u200b", value=f"{content['auth']}\n{content['intro']}\n{content['warn']}", inline=False)
        embed.add_field(name="\u200b", value=content["divider"], inline=False)
        embed.add_field(name="\u200b", value=(
            f"📖 {content['rule_btn']} 　🔘\n"
            f"🏵 {content['auth_btn']} 　🔘\n"
            f"📝 {content['intro_btn']} 　🔘"
        ), inline=False)
        embed.add_field(name="\u200b", value=content["divider"], inline=False)
        embed.add_field(name=content["lang_label"], value="以下のプルダウンで言語を切替できます。", inline=False)

        # build new view (re-create to update labels)
        new_view = build_view_for_guild(self.guild_id, lang)
        await interaction.response.edit_message(embed=embed, view=new_view)

def build_view_for_guild(guild_id: int, lang_code: str = "ja"):
    """
    Build a LayoutView (or fallback View) with:
      - Section(s) representing the embed-like layout (if LayoutView available)
      - 3 URL Buttons (rules/auth/intro) that jump to channels
      - Language Select (persistent custom_id)
    """
    content = build_contents_for_lang(lang_code, guild_id)

    # If LayoutView + Section available, use those to make embed-like layout
    if USE_LAYOUT:
        view = ui.LayoutView(timeout=None)

        # top: text + image placeholder (actual image will be attachment)
        # ui.Section: holds text blocks (title/desc)
        view.add_item(ui.Section(
            content=ui.TextDisplay(content["title"] + "\n" + content["desc"]),
            key="header"
        ))

        # divider + auth/intro/warn block
        view.add_item(ui.Section(
            content=ui.TextDisplay(content["divider"] + "\n" + content["auth"] + "\n" + content["intro"] + "\n" + content["warn"]),
            key="middle"
        ))

        # button row section (we'll add 3 buttons)
        # Buttons in components are added via ui.Button items
        # Add rule button (URL)
        view.add_item(ui.Button(label=content["rule_btn"], style=discord.ButtonStyle.link,
                                url=f"https://discord.com/channels/{guild_id}/{RULE_CHANNEL_ID}",
                                key="rule_btn"))
        view.add_item(ui.Button(label=content["auth_btn"], style=discord.ButtonStyle.link,
                                url=f"https://discord.com/channels/{guild_id}/{AUTH_CHANNEL_ID}",
                                key="auth_btn"))
        view.add_item(ui.Button(label=content["intro_btn"], style=discord.ButtonStyle.link,
                                url=f"https://discord.com/channels/{guild_id}/{INTRO_CHANNEL_ID}",
                                key="intro_btn"))

        # final divider + language select
        view.add_item(ui.Section(content=ui.TextDisplay(content["divider"]), key="bottom_div"))
        select = GuildLanguageSelect(guild_id)
        view.add_item(select)
        return view
    else:
        # fallback to classic View: put Buttons (link) and Select below embed
        view = ui.View(timeout=None)
        view.add_item(ui.Button(label=content["rule_btn"], style=discord.ButtonStyle.link,
                                url=f"https://discord.com/channels/{guild_id}/{RULE_CHANNEL_ID}"))
        view.add_item(ui.Button(label=content["auth_btn"], style=discord.ButtonStyle.link,
                                url=f"https://discord.com/channels/{guild_id}/{AUTH_CHANNEL_ID}"))
        view.add_item(ui.Button(label=content["intro_btn"], style=discord.ButtonStyle.link,
                                url=f"https://discord.com/channels/{guild_id}/{INTRO_CHANNEL_ID}"))
        view.add_item(GuildLanguageSelect(guild_id))
        return view

# ---------- Cog ----------
class WelcomeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        # ignore bots
        if member.bot:
            return

        # find channel
        ch = member.guild.get_channel(WELCOME_CHANNEL_ID)
        if ch is None:
            return

        # guild language
        guild_langs = load_guild_lang()
        lang_code = guild_langs.get(str(member.guild.id), "ja")

        # create image
        img_bio = await create_welcome_image(member)
        filename = f"welcome_{member.id}.png"

        # create embed (random color)
        content = build_contents_for_lang(lang_code, member.guild.id)
        color = random.randint(0, 0xFFFFFF)
        embed = discord.Embed(title=content["title"], description=content["desc"], color=color)
        embed.add_field(name="\u200b", value=content["divider"], inline=False)
        embed.add_field(name="\u200b", value=f"{content['auth']}\n{content['intro']}\n{content['warn']}", inline=False)
        embed.add_field(name="\u200b", value=content["divider"], inline=False)
        embed.add_field(name="\u200b", value=(
            f"📖 {content['rule_btn']} 　🔘\n"
            f"🏵 {content['auth_btn']} 　🔘\n"
            f"📝 {content['intro_btn']} 　🔘"
        ), inline=False)
        embed.add_field(name="\u200b", value=content["divider"], inline=False)
        embed.add_field(name=content["lang_label"], value="以下のプルダウンで言語を切替できます。", inline=False)

        embed.set_image(url=f"attachment://{filename}")

        view = build_view_for_guild(member.guild.id, lang_code)

        await ch.send(embed=embed, file=discord.File(fp=img_bio, filename=filename), view=view)

# setup
async def setup(bot: commands.Bot):
    await bot.add_cog(WelcomeCog(bot))
    # Register persistent views for each guild the bot is in
    # LayoutView persistence requires registering the same structure (custom_id) at startup.
    # We'll register a per-guild view with the custom_ided select so persistence works.
    for guild in bot.guilds:
        try:
            bot.add_view(build_view_for_guild(guild.id, load_guild_lang().get(str(guild.id), "ja")))
        except Exception:
            # ignore failures (e.g., if LayoutView not available)
            pass

