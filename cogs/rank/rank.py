# =====================================
# rank.py
# Rank System Core
# Spec v1.14.0 FULL COMPLY
# =====================================

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

DB = "data/rank/rank.db"
RANK_BG = "assets/rankbg/rank_bg.png"
FONT_PATH = "assets/font/font.ttf"

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

# =====================
# DB INIT
# =====================
def init_db():
    with sqlite3.connect(DB) as con:
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
# LEVEL FORMULA
# =====================
def calc_level(total_exp: int) -> int:
    level = 0
    while total_exp >= 20 * level * (level + 1):
        level += 1
    return max(level - 1, 0)

def next_level_exp(level: int) -> int:
    return 20 * (level + 1) * (level + 2)

# =====================
# RANK IMAGE
# =====================
def generate_rank_card(
    username: str,
    avatar_path: str,
    level: int,
    exp: int,
    next_exp: int,
    server_rank: int,
    weekly_rank: int,
    weekly_exp: int
) -> str:

    img = Image.open(RANK_BG).convert("RGBA")
    draw = ImageDraw.Draw(img)

    font_big = ImageFont.truetype(FONT_PATH, 48)
    font_mid = ImageFont.truetype(FONT_PATH, 32)
    font_small = ImageFont.truetype(FONT_PATH, 26)

    # USERNAME
    draw.text((180, 40), username, font=font_big, fill="black")

    # LEVEL
    draw.text((880, 40), f"{level:02}", font=font_big, fill="#1de9b6")

    # SERVER RANK
    draw.text((180, 120), f"#{server_rank:02}", font=font_mid, fill="#1de9b6")

    # WEEKLY RANK
    draw.text((350, 120), f"#{weekly_rank:02}", font=font_mid, fill="#1de9b6")

    # WEEKLY EXP
    draw.text((540, 120), f"{weekly_exp:03}", font=font_mid, fill="#1de9b6")

    # EXP TEXT
    draw.text((180, 190), f"EXP : {exp:04}/{next_exp:04}", font=font_small, fill="black")

    # PROGRESS BAR
    bar_x, bar_y = 180, 230
    bar_w = 700
    progress = int(bar_w * (exp / next_exp))
    draw.rectangle((bar_x, bar_y, bar_x + bar_w, bar_y + 20), fill="#cccccc")
    draw.rectangle((bar_x, bar_y, bar_x + progress, bar_y + 20), fill="#1de9b6")

    output = f"/tmp/rank_{username}.png"
    img.save(output)
    return output

# =====================
# COG
# =====================
class Rank(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        init_db()

    # =====================
    # /rank
    # =====================
    @app_commands.command(name="rank", description="ランクを表示")
    async def rank(self, interaction: discord.Interaction, user: discord.Member | None = None):
        user = user or interaction.user

        with sqlite3.connect(DB) as con:
            cur = con.cursor()
            cur.execute("SELECT exp, level FROM users WHERE user_id = ?", (user.id,))
            row = cur.fetchone()
            if not row:
                exp, level = 0, 0
            else:
                exp, level = row

            # SERVER RANK
            cur.execute("SELECT user_id FROM users ORDER BY exp DESC")
            ranks = [r[0] for r in cur.fetchall()]
            server_rank = ranks.index(user.id) + 1 if user.id in ranks else 0

            # WEEKLY
            cur.execute("SELECT user_id FROM weekly_exp ORDER BY exp DESC")
            wranks = [r[0] for r in cur.fetchall()]
            weekly_rank = wranks.index(user.id) + 1 if user.id in wranks else 0
            cur.execute("SELECT exp FROM weekly_exp WHERE user_id = ?", (user.id,))
            wexp = cur.fetchone()
            weekly_exp = wexp[0] if wexp else 0

        next_exp = next_level_exp(level)

        avatar = await user.display_avatar.read()
        avatar_path = f"/tmp/avatar_{user.id}.png"
        with open(avatar_path, "wb") as f:
            f.write(avatar)

        card = generate_rank_card(
            user.display_name,
            avatar_path,
            level,
            exp,
            next_exp,
            server_rank,
            weekly_rank,
            weekly_exp
        )

        await interaction.response.send_message(file=discord.File(card))

async def setup(bot):
    await bot.add_cog(Rank(bot))

