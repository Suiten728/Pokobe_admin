# ======================================================
# cogs/welcome.py  （完全版）
# ======================================================

import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import io
from PIL import Image, ImageDraw, ImageFont
import aiohttp

from ci.welcome_set import (
    WELCOME_CHANNEL_ID,
    RULE_CHANNEL_ID ,
    AUTH_CHANNEL_ID ,
    INTRO_CHANNEL_ID,
    BG_PATH,
    FONT_PATH
    )


LANG_FILE = "data/language.json"
os.makedirs("data", exist_ok=True)

# 言語データ：翻訳テキスト（前メッセージであなたと作った内容）
LANGUAGES = {
    "ja": {
        "title": "🪄 Welcome to KazamaTai no Tudoinoba",
        "desc": "🎉 サーバーにようこそ！隊士が集うこの場でたくさんの思い出を作りましょう！",
        "auth": "🏵 まずは <#{auth}> で認証をしてサーバーに参加しましょう！",
        "intro": "📝 自己紹介は <#{intro}> へどうぞ！",
        "warn": "⚠️ 安全上、このサーバーに入ってから10分しなければメッセージは送信できません！",
        "rule_btn": "📖 サーバールールを確認",
        "auth_btn": "🏵 認証を始める",
        "intro_btn": "📝 自己紹介はこちら",
        "lang_label": "言語変更 / Change Language"
    },
    "en": {
        "title": "🪄 Welcome to KazamaTai no Tudoinoba",
        "desc": "🎉 Welcome to the server! Make lots of great memories together with fellow members!",
        "auth": "🏵 First, please complete the verification in <#{auth}>!",
        "intro": "📝 Introduce yourself in <#{intro}>!",
        "warn": "⚠️ For safety reasons, you cannot send messages for 10 minutes after joining.",
        "rule_btn": "📖 View Server Rules",
        "auth_btn": "🏵 Start Verification",
        "intro_btn": "📝 Go to Introduction",
        "lang_label": "Change Language"
    },
    "ko": {
        "title": "🪄 KazamaTai no Tudoinoba 서버에 오신 것을 환영합니다!",
        "desc": "🎉 이곳은 대사들이 모이는 공간입니다. 함께 멋진 추억을 만들어가요!",
        "auth": "🏵 먼저 <#{auth}> 채널에서 인증을 완료해주세요!",
        "intro": "📝 자기소개는 <#{intro}> 에 작성해주세요!",
        "warn": "⚠️ 보안상, 참여 후 10분간 메시지를 보낼 수 없습니다.",
        "rule_btn": "📖 서버 규칙 확인",
        "auth_btn": "🏵 인증 시작하기",
        "intro_btn": "📝 자기소개하러 가기",
        "lang_label": "언어 변경"
    },
    "zh": {
        "title": "🪄 欢迎来到 KazamaTai no Tudoinoba!",
        "desc": "🎉 欢迎加入服务器！愿你与这里的成员们一起创造许多美好回忆！",
        "auth": "🏵 请先在 <#{auth}> 完成认证！",
        "intro": "📝 自我介绍请前往 <#{intro}>！",
        "warn": "⚠️ 出于安全原因，加入后需要等待 10 分钟才能发送消息。",
        "rule_btn": "📖 查看服务器规则",
        "auth_btn": "🏵 开始认证",
        "intro_btn": "📝 前往自我介绍",
        "lang_label": "语言选择"
    },
    "id": {
        "title": "🪄 Selamat datang di KazamaTai no Tudoinoba!",
        "desc": "🎉 Selamat datang di server! Mari buat banyak kenangan indah bersama!",
        "auth": "🏵 Silakan lakukan verifikasi di <#{auth}>!",
        "intro": "📝 Perkenalkan diri di <#{intro}>!",
        "warn": "⚠️ Demi keamanan, kamu tidak bisa mengirim pesan selama 10 menit pertama.",
        "rule_btn": "📖 Lihat Peraturan Server",
        "auth_btn": "🏵 Mulai Verifikasi",
        "intro_btn": "📝 Pergi ke Perkenalan",
        "lang_label": "Ganti Bahasa"
    }
}


def load_lang():
    if not os.path.exists(LANG_FILE):
        with open(LANG_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f, ensure_ascii=False, indent=4)
    with open(LANG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_lang(data):
    with open(LANG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


# ================================
# 画像合成: 背景 + 新規ユーザーのアイコン
# ================================
async def create_welcome_image(user: discord.Member):
    bg = Image.open(BG_PATH).convert("RGBA")

    async with aiohttp.ClientSession() as session:
        async with session.get(user.avatar.url) as resp:
            avatar_data = await resp.read()

    avatar = Image.open(io.BytesIO(avatar_data)).convert("RGBA")
    avatar = avatar.resize((260, 260))

    # 中央へ配置
    ax = (bg.width - avatar.width) // 2
    ay = 50
    bg.paste(avatar, (ax, ay), avatar)

    # ユーザー名を描画
    draw = ImageDraw.Draw(bg)
    font = ImageFont.truetype(FONT_PATH, 48)
    text_w = draw.textlength(user.name, font=font)
    draw.text(((bg.width - text_w) / 2, 330), user.name, font=font, fill="white")

    out_path = f"pngdata/welcome_{user.id}.png"
    bg.save(out_path)
    return out_path


# ================================
# Language Select UI
# ================================
class LanguageSelect(discord.ui.Select):
    def __init__(self, guild_id):
        options = [
            discord.SelectOption(label="日本語", value="ja",emoji="🇯🇵"),
            discord.SelectOption(label="English", value="en",emoji="🇺🇸"),
            discord.SelectOption(label="한국어", value="ko",emoji="🇰🇷"),
            discord.SelectOption(label="中文", value="zh",emoji="🇨🇳"),
            discord.SelectOption(label="Bahasa Indonesia", value="id",emoji="🇮🇩"),
        ]

        super().__init__(placeholder="🌐 言語を変更 | Change Language", options=options)
        self.guild_id = guild_id

    async def callback(self, interaction: discord.Interaction):
        lang_data = load_lang()
        lang_data[str(self.guild_id)] = self.values[0]
        save_lang(lang_data)

        await interaction.response.edit_message(
            embed=create_welcome_embed(self.values[0]),
            view=WelcomeView(self.guild_id)
        )


class WelcomeView(discord.ui.View):
    def __init__(self, guild_id):
        super().__init__(timeout=None)
        self.guild_id = guild_id

        lang_data = load_lang()
        lang = lang_data.get(str(guild_id), "ja")
        lang_text = LANGUAGES[lang]

        self.add_item(discord.ui.Button(
            label=lang_text["rule_btn"],
            url=f"https://discord.com/channels/{guild_id}/{RULE_CHANNEL_ID}"
        ))
        self.add_item(discord.ui.Button(
            label=lang_text["auth_btn"],
            url=f"https://discord.com/channels/{guild_id}/{AUTH_CHANNEL_ID}"
        ))
        self.add_item(discord.ui.Button(
            label=lang_text["intro_btn"],
            url=f"https://discord.com/channels/{guild_id}/{INTRO_CHANNEL_ID}"
        ))
        self.add_item(LanguageSelect(guild_id))


# ================================
# ウェルカムEmbed作成
# ================================
def create_welcome_embed(lang="ja"):
    text = LANGUAGES[lang]

    embed = discord.Embed(
        title=text["title"],
        description=text["desc"],
        color=0x00bfff
    )
    embed.add_field(name="ーーー", value=text["auth"].format(auth=AUTH_CHANNEL_ID), inline=False)
    embed.add_field(name="ーーー", value=text["intro"].format(intro=INTRO_CHANNEL_ID), inline=False)
    embed.add_field(name="ーーー", value=text["warn"], inline=False)

    return embed


# ================================
# Cog本体
# ================================
class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):

        channel = member.guild.get_channel(WELCOME_CHANNEL_ID)

        # 画像生成
        img_path = await create_welcome_image(member)

        lang_data = load_lang()
        lang = lang_data.get(str(member.guild.id), "ja")

        embed = create_welcome_embed(lang)

        await channel.send(
            file=discord.File(img_path),
            embed=embed,
            view=WelcomeView(member.guild.id)
        )


async def setup(bot):
    await bot.add_cog(Welcome(bot))
