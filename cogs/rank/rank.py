# ============================================
# rank.py
# Rank System Core (Clean Final Version)
# ============================================

import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import os
import io
import requests
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

# =====================
# ENV & PATH
# =====================
load_dotenv("ci/.env")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_PATH = os.path.join(BASE_DIR, "../../data/rank/rank.db")
RANK_BG_PATH = os.path.join(BASE_DIR, "../../assets/rankbg/rank_bg.png")

FONT_BOLD = os.path.join(BASE_DIR, "../../assets/font/NotoSansJP-Bold.ttf")
FONT_MED  = os.path.join(BASE_DIR, "../../assets/font/NotoSansJP-Medium.ttf")
FONT_REG  = os.path.join(BASE_DIR, "../../assets/font/NotoSansJP-Regular.ttf")

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

def calc_level(exp: int) -> int:
    lvl = 0
    while exp >= total_exp_for_level(lvl + 1):
        lvl += 1
    return lvl

# =====================
# IMAGE UTILS
# =====================
def load_icon(url: str, size: int) -> Image.Image:
    res = requests.get(url)
    img = Image.open(io.BytesIO(res.content)).convert("RGBA")
    return img.resize((size, size))

def circle_crop(img: Image.Image, size: int) -> Image.Image:
    mask = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(mask)
    d.ellipse((0, 0, size, size), fill=255)
    out = Image.new("RGBA", (size, size))
    out.paste(img, (0, 0), mask)
    return out

# =====================
# IMAGE GENERATION
# =====================
def generate_rank_card(
    interaction: discord.Interaction,
    user: discord.Member,
    level: int,
    exp: int,
    server_rank: int,
    weekly_rank: int,
    weekly_exp: int
) -> str:

    img = Image.open(RANK_BG_PATH).convert("RGBA")
    draw = ImageDraw.Draw(img)

    # Fonts
    font_big = ImageFont.truetype(FONT_BOLD, 44)
    font_mid = ImageFont.truetype(FONT_MED, 28)
    font_small = ImageFont.truetype(FONT_REG, 22)

    # Icons
    user_icon = circle_crop(
        load_icon(user.display_avatar.url, 96), 96
    )

    guild_icon = None
    if interaction.guild.icon:
        guild_icon = circle_crop(
            load_icon(interaction.guild.icon.url, 42), 42
        )

    # Paste icons
    img.paste(user_icon, (70, 55), user_icon)
    if guild_icon:
        img.paste(guild_icon, (55, 35), guild_icon)

    # Username
    draw.text((190, 40), user.display_name, font=font_big, fill=(0, 0, 0))

    # Level
    draw.text((980, 40), f"{level:02}", font=font_big, fill=(30, 233, 182))

    # Labels
    draw.text((190, 115), "SERVER RANK", font=font_small, fill=(90, 90, 90))
    draw.text((350, 115), "WEEKLY RANK", font=font_small, fill=(90, 90, 90))
    draw.text((530, 115), "WEEKLY EXP", font=font_small, fill=(90, 90, 90))

    # Values
    draw.text((190, 145), f"#{server_rank}", font=font_mid, fill=(30, 233, 182))
    draw.text((350, 145), f"#{weekly_rank}", font=font_mid, fill=(30, 233, 182))
    draw.text((530, 145), f"{weekly_exp}", font=font_mid, fill=(30, 233, 182))

    # EXP Bar
    next_exp = total_exp_for_level(level + 1)
    ratio = min(exp / next_exp, 1) if next_exp else 0

    bar_x, bar_y = 190, 205
    bar_w, bar_h = 720, 18

    draw.rectangle(
        (bar_x, bar_y, bar_x + bar_w, bar_y + bar_h),
        fill=(200, 200, 200)
    )
    draw.rectangle(
        (bar_x, bar_y, bar_x + int(bar_w * ratio), bar_y + bar_h),
        fill=(30, 233, 182)
    )

    draw.text(
        (190, 175),
        f"EXP : {exp}/{next_exp}",
        font=font_small,
        fill=(0, 0, 0)
    )

    out = f"/tmp/rank_{user.id}.png"
    img.save(out)
    return out

# =====================
# COG
# =====================
class Rank(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        init_db()

    rank = app_commands.Group(name="rank", description="ランク関連コマンド")

    # /rank show
    @rank.command(name="show", description="ランクを表示")
    async def rank_show(
        self,
        interaction: discord.Interaction,
        user: discord.Member | None = None
    ):
        user = user or interaction.user

        members = [m for m in interaction.guild.members if not m.bot]
        total = len(members)

        with sqlite3.connect(DB_PATH) as con:
            cur = con.cursor()

            cur.execute("SELECT exp FROM users WHERE user_id=?", (user.id,))
            row = cur.fetchone()
            exp = row[0] if row else 0
            level = calc_level(exp)

            cur.execute("SELECT user_id FROM users WHERE exp>0 ORDER BY exp DESC")
            ranked = [r[0] for r in cur.fetchall()]
            server_rank = ranked.index(user.id) + 1 if user.id in ranked else total

            cur.execute("SELECT user_id FROM weekly_exp WHERE exp>0 ORDER BY exp DESC")
            wranked = [r[0] for r in cur.fetchall()]
            weekly_rank = wranked.index(user.id) + 1 if user.id in wranked else total

            cur.execute("SELECT exp FROM weekly_exp WHERE user_id=?", (user.id,))
            w = cur.fetchone()
            weekly_exp = w[0] if w else 0

        card = generate_rank_card(
            interaction,
            user,
            level,
            exp,
            server_rank,
            weekly_rank,
            weekly_exp
        )

        await interaction.response.send_message(
            file=discord.File(card)
        )

# =====================
# SETUP
# =====================
async def setup(bot: commands.Bot):
    await bot.add_cog(Rank(bot))