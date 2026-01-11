# ============================================
# rank.py
# Rank System Core
# Spec v1.14.0 FULL COMPLIANCE
# ============================================

import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import os
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
FONT_BOLD = "assets/font/NotoSansJP-Bold.otf"
FONT_MED = "assets/font/NotoSansJP-Medium.otf"
FONT_REG = "assets/font/NotoSansJP-Regular.otf"

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
# LEVEL FORMULA
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

    font_big = ImageFont.truetype(FONT_BOLD, 48)
    font_mid = ImageFont.truetype(FONT_MED, 30)
    font_small = ImageFont.truetype(FONT_REG, 24)

    # USERNAME
    draw.text((180, 35), username, font=font_big, fill=(0, 0, 0))

    # LEVEL
    draw.text((930, 35), f"{level:02}", font=font_big, fill=(30, 233, 182))

    # SERVER RANK
    draw.text((180, 120), f"#{server_rank}", font=font_mid, fill=(30, 233, 182))

    # WEEKLY RANK
    draw.text((360, 120), f"#{weekly_rank}", font=font_mid, fill=(30, 233, 182))

    # WEEKLY EXP
    draw.text((560, 120), f"{weekly_exp}", font=font_mid, fill=(30, 233, 182))

    # EXP TEXT
    draw.text(
        (180, 190),
        f"EXP : {exp}/{next_exp}",
        font=font_small,
        fill=(0, 0, 0)
    )

    # PROGRESS BAR
    bar_x, bar_y = 180, 225
    bar_w, bar_h = 720, 18
    ratio = min(exp / next_exp, 1) if next_exp > 0 else 0
    fill_w = int(bar_w * ratio)

    draw.rectangle(
        (bar_x, bar_y, bar_x + bar_w, bar_y + bar_h),
        fill=(200, 200, 200)
    )
    draw.rectangle(
        (bar_x, bar_y, bar_x + fill_w, bar_y + bar_h),
        fill=(30, 233, 182)
    )

    out = f"/tmp/rank_{username}.png"
    img.save(out)
    return out

# =====================
# COG
# =====================
class Rank(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        init_db()
        self.bot.tree.add_command(self.rank_group)

    # =====================
    # /rank GROUP
    # =====================
    rank_group = app_commands.Group(
        name="rank",
        description="ランク関連コマンド"
    )

    # =====================
    # 共通処理
    # =====================
    async def _send_rank(
        self,
        interaction: discord.Interaction,
        user: discord.Member
    ):
        guild_members = [
            m for m in interaction.guild.members
            if not m.bot
        ]
        total_members = len(guild_members)

        with sqlite3.connect(DB_PATH) as con:
            cur = con.cursor()

            cur.execute(
                "SELECT exp, level FROM users WHERE user_id=?",
                (user.id,)
            )
            row = cur.fetchone()
            exp, level = row if row else (0, 0)

            # SERVER RANK
            cur.execute(
                "SELECT user_id FROM users WHERE exp>0 ORDER BY exp DESC"
            )
            ranked = [r[0] for r in cur.fetchall()]

            server_rank = (
                ranked.index(user.id) + 1
                if exp > 0 and user.id in ranked
                else total_members
            )

            # WEEKLY
            cur.execute(
                "SELECT user_id FROM weekly_exp WHERE exp>0 ORDER BY exp DESC"
            )
            wranked = [r[0] for r in cur.fetchall()]

            weekly_rank = (
                wranked.index(user.id) + 1
                if user.id in wranked
                else total_members
            )

            cur.execute(
                "SELECT exp FROM weekly_exp WHERE user_id=?",
                (user.id,)
            )
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

        await interaction.response.send_message(
            file=discord.File(card)
        )

    # =====================
    # /rank show
    # =====================
    @rank_group.command(
        name="show",
        description="自分または指定ユーザーのランクを表示"
    )
    async def rank_show(
        self,
        interaction: discord.Interaction,
        user: discord.Member | None = None
    ):
        await self._send_rank(
            interaction,
            user or interaction.user
        )

    # =====================
    # /rank leaderboard
    # =====================
    @rank_group.command(
        name="leaderboard",
        description="ランキングを表示"
    )
    @app_commands.choices(
        type=[
            app_commands.Choice(name="Normal", value="normal"),
            app_commands.Choice(name="Weekly", value="weekly"),
        ]
    )
    async def rank_leaderboard(
        self,
        interaction: discord.Interaction,
        type: app_commands.Choice[str]
    ):
        with sqlite3.connect(DB_PATH) as con:
            cur = con.cursor()
            if type.value == "weekly":
                cur.execute(
                    "SELECT user_id, exp FROM weekly_exp WHERE exp>0 ORDER BY exp DESC LIMIT 10"
                )
            else:
                cur.execute(
                    "SELECT user_id, exp FROM users WHERE exp>0 ORDER BY exp DESC LIMIT 10"
                )
            rows = cur.fetchall()

        embed = discord.Embed(
            title="🏆 ランキング",
            colour=discord.Colour.gold()
        )

        if not rows:
            embed.description = "誰もEXPを所持していません"
            await interaction.response.send_message(embed=embed)
            return

        for i, (uid, exp) in enumerate(rows, start=1):
            member = interaction.guild.get_member(uid)
            if member:
                embed.add_field(
                    name=f"{i}位",
                    value=f"{member.display_name} - {exp} EXP",
                    inline=False
                )

        await interaction.response.send_message(embed=embed)

    # =====================
    # /rank notify
    # =====================
    @rank_group.command(
        name="notify",
        description="ランクアップ通知のメンション切替"
    )
    @app_commands.choices(
        mode=[
            app_commands.Choice(name="ON", value="on"),
            app_commands.Choice(name="OFF", value="off"),
        ]
    )
    async def rank_notify(
        self,
        interaction: discord.Interaction,
        mode: app_commands.Choice[str]
    ):
        val = 1 if mode.value == "on" else 0
        with sqlite3.connect(DB_PATH) as con:
            con.execute(
                "INSERT INTO users(user_id, mention) VALUES(?,?) "
                "ON CONFLICT(user_id) DO UPDATE SET mention=?",
                (interaction.user.id, val, val)
            )
        await interaction.response.send_message(
            "✅ 設定を更新しました",
            ephemeral=True
        )

# =====================
# SETUP
# =====================
async def setup(bot: commands.Bot):
    await bot.add_cog(Rank(bot))

