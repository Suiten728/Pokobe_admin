# ============================================
# rank.py
# Rank System Core
# Spec v1.14.0 FULL COMPLIANCE
# ============================================

import discord
from discord.ext import commands, tasks
from discord import app_commands
import sqlite3
import os
import time
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

# =====================
# ENV
# =====================
load_dotenv("ci/.env")

LOG_CHANNEL_ID = int(os.getenv("RANK_LOG_CHANNEL_ID"))
OWNER_ID = int(os.getenv("SERVER_OWNER_ID"))
RANK_NOTIFICATION_CHANNEL_ID = int(os.getenv("RANK_NOTIFICATION_CHANNEL_ID"))

DB_PATH = "data/rank/rank.db"
RANK_BG_PATH = "assets/rankbg/rank_bg.png"
FONT_PATH = "assets/font/NotoSansJP-SemiBold.ttf"

# =====================
# RANK ROLE TABLE
# =====================
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

LOG_LEVELS = set(RANK_ROLES.keys())

# =====================
# DB INIT
# =====================
def init_db():
    with sqlite3.connect(DB_PATH) as con:
        cur = con.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            exp INTEGER DEFAULT 0,
            level INTEGER DEFAULT 0,
            mention INTEGER DEFAULT 1
        )
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS weekly_exp (
            user_id INTEGER PRIMARY KEY,
            exp INTEGER DEFAULT 0
        )
        """)

# =====================
# LEVEL CALC
# =====================
def total_exp_for_level(level: int) -> int:
    return 20 * level * (level + 1)

def calc_level(total_exp: int) -> int:
    level = 0
    while total_exp >= total_exp_for_level(level + 1):
        level += 1
    return level

# =====================
# IMAGE GENERATION
# =====================
def generate_rank_card(
    username: str,
    level: int,
    exp: int,
    next_exp: int,
    server_rank: int,
    weekly_rank: int,
    weekly_exp: int
) -> str:

    img = Image.open(RANK_BG_PATH).convert("RGBA")
    draw = ImageDraw.Draw(img)

    font_big = ImageFont.truetype(FONT_PATH, 48)
    font_mid = ImageFont.truetype(FONT_PATH, 30)
    font_small = ImageFont.truetype(FONT_PATH, 24)

    # USERNAME
    draw.text((160, 30), username, font=font_big, fill=(0, 0, 0))

    # LEVEL
    draw.text((900, 30), f"{level:02}", font=font_big, fill=(30, 233, 182))

    # SERVER RANK
    draw.text((160, 115), f"#{server_rank:02}", font=font_mid, fill=(30, 233, 182))

    # WEEKLY RANK
    draw.text((350, 115), f"#{weekly_rank:02}", font=font_mid, fill=(30, 233, 182))

    # WEEKLY EXP
    draw.text((550, 115), f"{weekly_exp:03}", font=font_mid, fill=(30, 233, 182))

    # EXP TEXT
    draw.text(
        (160, 190),
        f"EXP : {exp:04}/{next_exp:04}",
        font=font_small,
        fill=(0, 0, 0)
    )

    # PROGRESS BAR
    bar_x, bar_y = 160, 225
    bar_w, bar_h = 720, 18
    ratio = min(exp / next_exp, 1)
    fill_w = int(bar_w * ratio)

    draw.rectangle((bar_x, bar_y, bar_x + bar_w, bar_y + bar_h), fill=(200, 200, 200))
    draw.rectangle((bar_x, bar_y, bar_x + fill_w, bar_y + bar_h), fill=(30, 233, 182))

    out_path = f"/tmp/rank_{username}.png"
    img.save(out_path)
    return out_path

# =====================
# COG
# =====================
class Rank(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        init_db()

    # =====================
    # INTERNAL: ROLE UPDATE
    # =====================
    async def update_rank_role(self, member: discord.Member, old_level: int, new_level: int):
        guild = member.guild
        bot_top_role = guild.me.top_role

        for lvl, role_name in RANK_ROLES.items():
            if old_level < lvl <= new_level:
                role = discord.utils.get(guild.roles, name=role_name)
                if not role:
                    role = await guild.create_role(name=role_name, colour=discord.Colour.light_grey())
                    await role.edit(position=bot_top_role.position - 1)

                if role.position >= bot_top_role.position:
                    raise PermissionError("Role hierarchy error")

                await member.add_roles(role, reason="Rank level up")

                if lvl in LOG_LEVELS:
                    await self.log_rank_change(member, lvl)

    # =====================
    # LOG
    # =====================
    async def log_rank_change(self, member: discord.Member, level: int):
        ch = self.bot.get_channel(LOG_CHANNEL_ID)
        if not ch:
            return

        embed = discord.Embed(
            title="ランクロール変更ログ",
            description=f"{member.mention} が Lv.{level} に到達",
            colour=discord.Colour.green()
        )
        embed.add_field(name="付与ロール", value=RANK_ROLES[level])
        embed.timestamp = discord.utils.utcnow()
        await ch.send(embed=embed)

    # =====================
    # /rank GROUP
    # =====================
    rank = app_commands.Group(name="rank", description="ランク関連コマンド")

    # /rank show
    @rank.command(name="show", description="自分または指定ユーザーのランクを表示")
    async def rank_show(self, interaction: discord.Interaction, user: discord.Member | None = None):
        user = user or interaction.user

        with sqlite3.connect(DB_PATH) as con:
            cur = con.cursor()

            cur.execute("SELECT exp, level, mention FROM users WHERE user_id=?", (user.id,))
            row = cur.fetchone()
            if not row:
                exp, level, _ = 0, 0, 1
            else:
                exp, level, _ = row

            cur.execute("SELECT user_id FROM users WHERE exp>0 ORDER BY exp DESC")
            ranks = [r[0] for r in cur.fetchall()]
            server_rank = ranks.index(user.id) + 1 if user.id in ranks else 0

            cur.execute("SELECT user_id FROM weekly_exp WHERE exp>0 ORDER BY exp DESC")
            wranks = [r[0] for r in cur.fetchall()]
            weekly_rank = wranks.index(user.id) + 1 if user.id in wranks else 0

            cur.execute("SELECT exp FROM weekly_exp WHERE user_id=?", (user.id,))
            w = cur.fetchone()
            weekly_exp = w[0] if w else 0

        next_exp = total_exp_for_level(level + 1)
        card = generate_rank_card(
            user.display_name,
            level,
            exp,
            next_exp,
            server_rank,
            weekly_rank,
            weekly_exp
        )

        await interaction.response.send_message(file=discord.File(card))

    # /rank leaderboard
    @rank.command(name="leaderboard", description="ランキングを表示")
    @app_commands.describe(type="normal または weekly")
    async def rank_leaderboard(self, interaction: discord.Interaction, type: str):
        with sqlite3.connect(DB_PATH) as con:
            cur = con.cursor()
            if type == "weekly":
                cur.execute("SELECT user_id, exp FROM weekly_exp WHERE exp>0 ORDER BY exp DESC LIMIT 10")
            else:
                cur.execute("SELECT user_id, exp FROM users WHERE exp>0 ORDER BY exp DESC LIMIT 10")
            rows = cur.fetchall()

        embed = discord.Embed(title="🏆 ランキング", colour=discord.Colour.gold())
        for i, (uid, exp) in enumerate(rows, start=1):
            member = interaction.guild.get_member(uid)
            if member:
                embed.add_field(
                    name=f"{i}位",
                    value=f"{member.display_name} - {exp} EXP",
                    inline=False
                )

        await interaction.response.send_message(embed=embed)

    # /rank notify
    @rank.command(name="notify", description="ランクアップ通知のメンション切替")
    @app_commands.describe(mode="on / off")
    async def rank_notify(self, interaction: discord.Interaction, mode: str):
        val = 1 if mode == "on" else 0
        with sqlite3.connect(DB_PATH) as con:
            con.execute(
                "INSERT INTO users(user_id, mention) VALUES(?,?) "
                "ON CONFLICT(user_id) DO UPDATE SET mention=?",
                (interaction.user.id, val, val)
            )
        await interaction.response.send_message("✅ 設定を更新しました", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Rank(bot))

