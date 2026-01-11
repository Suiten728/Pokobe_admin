# ========================================
# rank.py - Rank System 
# Spec v1.14.0 
# ========================================

import discord
from discord.ext import commands
from discord import app_commands
from PIL import Image, ImageDraw, ImageFont
import os
import json
import math
import io

# ========================================
# ENV SAFE LOAD
# ========================================

def getenv_int(key: str):
    v = os.getenv(key)
    return int(v) if v and v.isdigit() else None

LOG_CHANNEL_ID = getenv_int("RANK_LOG_CHANNEL_ID")
OWNER_ID = getenv_int("SERVER_OWNER_ID")
RANK_NOTIFICATION_CHANNEL_ID = getenv_int("RANK_NOTIFICATION_CHANNEL_ID")

# ========================================
# PATH / SETTINGS
# ========================================

DATA_PATH = "data/rank/rank_data.json"
FONT_PATH = "assets/font/NotoSansJP-Bold.otf"
CARD_SIZE = (600, 180)

RANK_BG_TABLE = {
    0: "assets/rankbg/bg_0.png",
    20: "assets/rankbg/bg_20.png",
    40: "assets/rankbg/bg_40.png",
    60: "assets/rankbg/bg_60.png",
    100: "assets/rankbg/bg_100.png",
}

RANK_ROLES = {
    1: "🔰｜見習い訓練兵",
    5: "🌸｜慣れてきた隊士",
    10: "🌱｜馴染んできた隊士",
    20: "🛡｜一人前の隊士",
    30: "⚔｜リラックスした隊士",
    40: "🏅｜すべてを熟知している隊士",
    50: "👑｜凄腕のベテラン隊士",
    75: "🌟｜戦場を生き抜いた隊士",
    100: "👑｜熟練した隊長",
}
RANK_TRIGGER_LEVELS = sorted(RANK_ROLES.keys())

# ========================================
# DATA
# ========================================

def load_data():
    if not os.path.exists(DATA_PATH):
        return {}
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# ========================================
# LEVEL CALC
# ========================================

def calc_level(total_exp: int) -> int:
    return int((math.sqrt(1 + total_exp / 10) - 1) / 2)

def next_level_exp(level: int) -> int:
    return 40 * (level + 1)

def select_bg(level: int) -> str:
    bg = RANK_BG_TABLE[0]
    for lv in sorted(RANK_BG_TABLE):
        if level >= lv:
            bg = RANK_BG_TABLE[lv]
    return bg

# ========================================
# IMAGE GENERATION
# ========================================

async def generate_rank_card(member: discord.Member, data: dict) -> discord.File:
    uid = str(member.id)
    exp = data.get(uid, {}).get("exp", 0)
    level = calc_level(exp)

    base = Image.open(select_bg(level)).convert("RGBA").resize(CARD_SIZE)
    draw = ImageDraw.Draw(base)

    font_big = ImageFont.truetype(FONT_PATH, 32)
    font_mid = ImageFont.truetype(FONT_PATH, 18)
    font_small = ImageFont.truetype(FONT_PATH, 14)

    # avatar
    avatar_bytes = await member.display_avatar.read()
    avatar = Image.open(io.BytesIO(avatar_bytes)).resize((96, 96)).convert("RGBA")
    mask = Image.new("L", (96, 96), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, 96, 96), fill=255)
    base.paste(avatar, (20, 20), mask)

    # text
    draw.text((140, 20), member.display_name, font=font_big, fill="black")

    draw.text((140, 65), "SERVER RANK", font=font_small, fill="black")
    draw.text((260, 65), "#00", font=font_small, fill="#00cfa1")

    draw.text((140, 90), "WEEKLY RANK", font=font_small, fill="black")
    draw.text((260, 90), "#00", font=font_small, fill="#00cfa1")

    draw.text((140, 115), "WEEKLY EXP", font=font_small, fill="black")
    draw.text((260, 115), "000", font=font_small, fill="#00cfa1")

    draw.text((480, 25), f"LEVEL\n{level:02}", font=font_mid, fill="#00cfa1", align="center")

    # exp bar
    need = next_level_exp(level)
    cur = exp % need
    ratio = cur / need if need else 0

    bar_x, bar_y = 140, 150
    bar_w, bar_h = 420, 12

    draw.rectangle((bar_x, bar_y, bar_x + bar_w, bar_y + bar_h), fill="#cccccc")
    draw.rectangle(
        (bar_x, bar_y, bar_x + int(bar_w * ratio), bar_y + bar_h),
        fill="#00cfa1"
    )
    draw.text((140, 135), f"EXP : {cur} / {need}", font=font_small, fill="black")

    buf = io.BytesIO()
    base.save(buf, "PNG")
    buf.seek(0)
    return discord.File(buf, filename="rank.png")

# ========================================
# RANK COG
# ========================================

class Rank(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data = load_data()

    # ================================
    # ROLE & NOTIFY
    # ================================

    async def apply_rank_roles(self, member: discord.Member, before_lv: int, after_lv: int):
        for lv in RANK_TRIGGER_LEVELS:
            if before_lv < lv <= after_lv:
                await self._give_rank_role(member, lv)
                await self._rankup_notify(member, lv)
                await self._log_rank(member, lv)

    async def _give_rank_role(self, member: discord.Member, level: int):
        guild = member.guild
        role_name = RANK_ROLES[level]

        try:
            role = discord.utils.get(guild.roles, name=role_name)
            if role is None:
                role = await guild.create_role(
                    name=role_name,
                    colour=discord.Colour.light_grey(),
                    reason="Rank role auto create"
                )

            for r in guild.roles:
                if r.name in RANK_ROLES.values() and r in member.roles:
                    await member.remove_roles(r)

            await member.add_roles(role, reason="Rank up")

        except discord.Forbidden:
            await self._permission_error(guild)

    async def _rankup_notify(self, member: discord.Member, level: int):
        if not RANK_NOTIFICATION_CHANNEL_ID:
            return

        ch = member.guild.get_channel(RANK_NOTIFICATION_CHANNEL_ID)
        if not ch:
            return

        uid = str(member.id)
        self.data.setdefault(uid, {"exp": 0, "mention": True})
        mention = member.mention if self.data[uid].get("mention", True) else member.display_name

        await ch.send(f"{mention} さんが **Lv.{level}** に到達しました！🎉")

    async def _log_rank(self, member: discord.Member, level: int):
        if not LOG_CHANNEL_ID:
            return

        ch = member.guild.get_channel(LOG_CHANNEL_ID)
        if not ch:
            return

        embed = discord.Embed(
            title="ランクロール変更ログ",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="ユーザー", value=member.mention)
        embed.add_field(name="到達Lv", value=f"Lv.{level}")
        embed.add_field(name="付与ロール", value=RANK_ROLES[level])
        embed.add_field(name="理由", value="ランク到達による自動付与", inline=False)
        await ch.send(embed=embed)

    async def _permission_error(self, guild: discord.Guild):
        if not LOG_CHANNEL_ID:
            return

        ch = guild.get_channel(LOG_CHANNEL_ID)
        if not ch:
            return

        embed = discord.Embed(
            title="⚠ 権限不足",
            description="ランクロール操作権限がありません。",
            color=discord.Color.red()
        )

        if OWNER_ID:
            owner = guild.get_member(OWNER_ID)
            if owner:
                embed.add_field(name="通知先", value=owner.mention)

        await ch.send(embed=embed)

    # ================================
    # EXP ADD (外部から呼ぶ)
    # ================================

    async def add_exp(self, member: discord.Member, amount: int):
        uid = str(member.id)
        self.data.setdefault(uid, {"exp": 0, "mention": True})

        before_exp = self.data[uid]["exp"]
        before_lv = calc_level(before_exp)

        self.data[uid]["exp"] += amount
        after_lv = calc_level(self.data[uid]["exp"])

        save_data(self.data)

        if after_lv > before_lv:
            await self.apply_rank_roles(member, before_lv, after_lv)

    # ================================
    # GROUP COMMAND
    # ================================

    rank = app_commands.Group(
        name="rank",
        description="ランク関連コマンド"
    )

    @rank.command(name="show")
    async def rank_show(self, interaction: discord.Interaction, user: discord.Member | None = None):
        user = user or interaction.user
        file = await generate_rank_card(user, self.data)
        await interaction.response.send_message(file=file)

    @rank.command(name="mention")
    async def rank_mention(self, interaction: discord.Interaction, enable: bool):
        uid = str(interaction.user.id)
        self.data.setdefault(uid, {"exp": 0, "mention": True})
        self.data[uid]["mention"] = enable
        save_data(self.data)

        await interaction.response.send_message(
            f"ランクアップ通知メンションを **{'ON' if enable else 'OFF'}** にしました"
        )

    @rank.command(name="leaderboard")
    async def rank_leaderboard(self, interaction: discord.Interaction):
        await interaction.response.send_message("leaderboard 実装予定")

# ========================================
# SETUP
# ========================================

async def setup(bot):
    await bot.add_cog(Rank(bot))

