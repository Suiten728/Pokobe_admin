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
RANK_NOTIFICATION_CHANNEL_ID = int(os.getenv("RANK_NOTIFICATION_CHANNEL_ID"))

DB_PATH = "data/rank/rank.db"
RANK_BG_PATH = "assets/rankbg/rank_bg.png"
# rank_bg.png - 2000 × 752 px 
FONT_BOLD = "assets/font/NotoSansJP-Bold.ttf"
FONT_MED  = "assets/font/NotoSansJP-Medium.ttf"
FONT_REG  = "assets/font/NotoSansJP-Regular.ttf"

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
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
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
        con.commit()

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
    return img.resize((size, size), Image.Resampling.LANCZOS)

def circle_crop(img: Image.Image, size: int, border: int = 0, border_color=(30, 233, 182, 255)) -> Image.Image:
    # 画像を丸く切り抜く
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
    out = Image.new("RGBA", (size, size))
    out.paste(img, (0, 0), mask)

    if border <= 0:
        return out

    # 枠付きの新しいキャンバスを作成（枠の分だけ大きくする）
    total = size + border * 2
    framed = Image.new("RGBA", (total, total), (0, 0, 0, 0))
    
    # 枠（塗りつぶし円）を描画
    ImageDraw.Draw(framed).ellipse((0, 0, total, total), fill=border_color)
    
    # 中央に元の丸アイコンを貼り付け
    framed.paste(out, (border, border), out)
    return framed

# =====================
# IMAGE GENERATION (2000px版)
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
    
    font_big = ImageFont.truetype(FONT_BOLD, 115)
    font_mid = ImageFont.truetype(FONT_MED, 75)
    font_small = ImageFont.truetype(FONT_REG, 60)

    async with aiohttp.ClientSession() as session:
        user_icon = circle_crop(
            await load_icon(session, user.display_avatar.url, 400), 400
        )

        guild_icon = None
        if interaction.guild.icon:
            guild_icon = circle_crop(
                await load_icon(session, interaction.guild.icon.url, 220), 220,
                border=3,                        # 枠の太さ（px）
                border_color=(30, 233, 182, 255) # 枠の色（テーマカラーに合わせてある)
        )
        

    # 座標
    img.paste(user_icon, (18, 30), user_icon)
    # ペースト座標を枠の分だけずらす（border=3なら -3）
    if guild_icon:
            img.paste(guild_icon, (255 - 3, 305 - 3), guild_icon)

    draw.text((480, 120), user.display_name, font=font_big, fill=(0, 0, 0), anchor="lm")
    draw.text((1780, 250), f"{level}", font=font_big, fill=(30, 233, 182), anchor="mm")

    draw.text((670, 520), f"#{server_rank}", font=font_mid, fill=(30, 233, 182), anchor="mm")
    draw.text((1040, 520), f"#{weekly_rank}", font=font_mid, fill=(30, 233, 182), anchor="mm")
    draw.text((1400, 520), f"{weekly_exp}", font=font_mid, fill=(30, 233, 182), anchor="mm")

    next_exp = total_exp_for_level(level + 1)
    ratio = min(exp / next_exp, 1) if next_exp else 0

    # バーの座標とサイズ
    bar_x, bar_y = 40, 680
    bar_w, bar_h = 1920, 54

    draw.rectangle((bar_x, bar_y, bar_x + bar_w, bar_y + bar_h), fill=(200, 200, 200))
    draw.rectangle(
        (bar_x, bar_y, bar_x + int(bar_w * ratio), bar_y + bar_h),
        fill=(30, 233, 182)
    )

    draw.text((40, 580), f"EXP : {exp}/{next_exp}", font=font_small, fill=(0, 0, 0))

    os.makedirs("/tmp", exist_ok=True)
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

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """メッセージ送信時に経験値を付与"""
        if message.author.bot or not message.guild:
            return
            
        import random
        gained_exp = 4

        with sqlite3.connect(DB_PATH) as con:
            cur = con.cursor()
            
            # 現在の経験値とレベルを取得
            cur.execute("SELECT exp FROM users WHERE user_id=?", (message.author.id,))
            row = cur.fetchone()
            old_exp = row[0] if row else 0
            old_level = calc_level(old_exp)

            # 経験値を追加
            cur.execute("""
                INSERT INTO users (user_id, exp, level) 
                VALUES (?, ?, ?) 
                ON CONFLICT(user_id) DO UPDATE SET exp = exp + ?
            """, (message.author.id, gained_exp, old_level, gained_exp))

            # 週間経験値も追加
            cur.execute("""
                INSERT INTO weekly_exp (user_id, exp) 
                VALUES (?, ?) 
                ON CONFLICT(user_id) DO UPDATE SET exp = exp + ?
            """, (message.author.id, gained_exp, gained_exp))

            con.commit()

            # 新しいレベルを計算
            new_exp = old_exp + gained_exp
            new_level = calc_level(new_exp)

            notify_ch = guild.get_channel(RANK_NOTIFICATION_CHANNEL_ID)

            if notify_ch is None:
                print(f"エラー: チャンネルID {RANK_NOTIFICATION_CHANNEL_ID} が見つかりません")
                return

            # レベルアップした場合
            if new_level > old_level:
                # レベルを更新
                cur.execute("UPDATE users SET level=? WHERE user_id=?", (new_level, message.author.id))
                con.commit()

                # メンション設定を確認
                cur.execute("SELECT mention FROM users WHERE user_id=?", (message.author.id,))
                mention_row = cur.fetchone()
                mention_enabled = mention_row[0] if mention_row else 1

                if mention_enabled:
                    try:
                        await notify_ch.send(
                            f"🎉 {message.author.mention} がレベルアップしました！ **Lv.{old_level}** → **Lv.{new_level}**"
                        )
                        print(f"レベルアップ通知送信成功: {message.author.name} Lv.{new_level}")
                    except discord.Forbidden:
                        print(f"エラー: チャンネル {notify_ch.name} への送信権限がありません")
                    except discord.HTTPException as e:
                        print(f"HTTPエラー: {e}")
                    except Exception as e:
                        print(f"レベルアップ通知エラー: {type(e).__name__}: {e}")

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

        # 修正: interaction.response.defer()の後はfollowupを使う
        await interaction.followup.send(file=discord.File(card))

    @rank.command(name="leaderboard", description="ランキングを表示")
    async def rank_leaderboard(
        self,
        interaction: discord.Interaction,
        type: str = "total"
    ):
        await interaction.response.defer()

        with sqlite3.connect(DB_PATH) as con:
            cur = con.cursor()
            
            if type == "weekly":
                cur.execute("""
                    SELECT user_id, exp FROM weekly_exp 
                    WHERE exp > 0 
                    ORDER BY exp DESC 
                    LIMIT 10
                """)
                title = "📊 週間ランキング"
            else:
                cur.execute("""
                    SELECT user_id, exp FROM users 
                    WHERE exp > 0 
                    ORDER BY exp DESC 
                    LIMIT 10
                """)
                title = "🏆 総合ランキング"
            
            rows = cur.fetchall()

        if not rows:
            await interaction.followup.send("ランキングデータがありません。")
            return

        embed = discord.Embed(title=title, color=discord.Color.green())
        
        for idx, (user_id, exp) in enumerate(rows, 1):
            user = interaction.guild.get_member(user_id)
            if user:
                level = calc_level(exp) if type != "weekly" else ""
                level_text = f"Lv.{level} | " if level else ""
                embed.add_field(
                    name=f"{idx}. {user.display_name}",
                    value=f"{level_text}EXP: {exp}",
                    inline=False
                )

        await interaction.followup.send(embed=embed)

    @rank.command(name="mention", description="レベルアップ時のメンション設定")
    async def rank_mention(
        self,
        interaction: discord.Interaction,
        enabled: bool
    ):
        with sqlite3.connect(DB_PATH) as con:
            cur = con.cursor()
            cur.execute("""
                INSERT INTO users (user_id, mention) 
                VALUES (?, ?) 
                ON CONFLICT(user_id) DO UPDATE SET mention=?
            """, (interaction.user.id, int(enabled), int(enabled)))
            con.commit()

        status = "有効" if enabled else "無効"
        await interaction.response.send_message(
            f"レベルアップ時のメンションを{status}にしました。",
            ephemeral=True
        )


# =====================
# SETUP
# =====================
async def setup(bot: commands.Bot):
    await bot.add_cog(Rank(bot))
