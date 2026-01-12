# ============================================
# rank.py
# Rank System Core (No requests / Clean)
# ============================================

import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import os
import io
import aiohttp
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

# =====================
# ENV
# =====================
load_dotenv("ci/.env")

DB_PATH = "data/rank/rank.db"
RANK_BG_PATH = "assets/rankbg/rank-bg.png"
# rank-bg.png - 4000 × 1504 px 
FONT_BOLD = "assets/font/NotoSansJP-Bold.ttf"
FONT_MED  = "assets/font/NotoSansJP-Medium.ttf"
FONT_REG  = "assets/font/NotoSansJP-Regular.ttf"

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
async def load_icon(session: aiohttp.ClientSession, url: str, size: int) -> Image.Image:
    async with session.get(url) as resp:
        data = await resp.read()
    img = Image.open(io.BytesIO(data)).convert("RGBA")
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
async def generate_rank_card(
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

    font_big = ImageFont.truetype(FONT_BOLD, 44)
    font_mid = ImageFont.truetype(FONT_MED, 28)
    font_small = ImageFont.truetype(FONT_REG, 22)

    async with aiohttp.ClientSession() as session:
        user_icon = circle_crop(
            await load_icon(session, user.display_avatar.url, 730), 730
        )

        guild_icon = None
        if interaction.guild.icon:
            guild_icon = circle_crop(
                await load_icon(session, interaction.guild.icon.url, 360), 360
            )

    img.paste(user_icon, (180, 200), user_icon)
    if guild_icon:
        img.paste(guild_icon, (560, 600), guild_icon)

    draw.text((800, 80), user.display_name, font=font_big, fill=(0, 0, 0))
    draw.text((3320, 280), f"{level:02}", font=font_big, fill=(30, 233, 182))

    draw.text((1120, 920), f"#{server_rank}", font=font_mid, fill=(30, 233, 182))
    draw.text((1840, 920), f"#{weekly_rank}", font=font_mid, fill=(30, 233, 182))
    draw.text((2640, 920), f"{weekly_exp}", font=font_mid, fill=(30, 233, 182))

    next_exp = total_exp_for_level(level + 1)
    ratio = min(exp / next_exp, 1) if next_exp else 0

    bar_x, bar_y = 80, 1400
    bar_w, bar_h = 3840, 96

    draw.rectangle((bar_x, bar_y, bar_x + bar_w, bar_y + bar_h), fill=(200, 200, 200))
    draw.rectangle(
        (bar_x, bar_y, bar_x + int(bar_w * ratio), bar_y + bar_h),
        fill=(30, 233, 182)
    )

    draw.text((80, 1040), f"EXP : {exp}/{next_exp}", font=font_small, fill=(0, 0, 0))

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

    @rank.command(name="show", description="ランクを表示")
    async def rank_show(
        self,
        interaction: discord.Interaction,
        user: discord.Member | None = None
    ):
        await interaction.response.defer()
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

        card = await generate_rank_card(
            interaction, user, level, exp, server_rank, weekly_rank, weekly_exp
        )

        await interaction.response.send_message(file=discord.File(card))

# =====================
# SETUP
# =====================
async def setup(bot: commands.Bot):
    await bot.add_cog(Rank(bot))
