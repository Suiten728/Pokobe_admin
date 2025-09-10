import discord
from discord.ext import commands
from discord import app_commands
from PIL import Image, ImageDraw, ImageFont
import os
import sqlite3
import io

DB_PATH = "data/userdata.db"

# SQLite 初期化
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    messages INTEGER DEFAULT 0
                )""")
    conn.commit()
    conn.close()

def add_message(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, messages) VALUES (?, 0)", (user_id,))
    c.execute("UPDATE users SET messages = messages + 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def get_user(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT messages FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0

# ランク判定
def get_rank(messages: int):
    if messages < 10:
        return "見習い", 10
    elif messages < 50:
        return "一人前", 50
    elif messages < 200:
        return "熟練者", 200
    else:
        return "達人", None  # 上限なし

# 画像生成
def generate_rank_card(user: discord.User, messages: int):
    rank, next_goal = get_rank(messages)

    # ベース画像
    img = Image.new("RGB", (600, 200), (30, 30, 30))
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype("arial.ttf", 24)

    # ユーザー名 & ランク
    draw.text((150, 40), f"{user.display_name}", font=font, fill=(255, 255, 255))
    draw.text((150, 80), f"ランク: {rank}", font=font, fill=(200, 200, 200))

    # 発言数と進捗バー
    if next_goal:
        progress = messages / next_goal
        bar_length = int(400 * progress)
        draw.rectangle([150, 130, 150+bar_length, 150], fill=(0, 200, 0))
        draw.rectangle([150, 130, 550, 150], outline=(255, 255, 255))
        draw.text((150, 160), f"{messages}/{next_goal}", font=font, fill=(180, 180, 180))
    else:
        draw.text((150, 130), f"{messages} (MAX!)", font=font, fill=(255, 215, 0))

    # アイコン描画
    pfp = Image.open(io.BytesIO(user.display_avatar.read())).resize((100, 100))
    img.paste(pfp, (30, 50))

    # 画像をDiscord送信用に変換
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer

class RankCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        init_db()

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        add_message(message.author.id)

    @commands.hybrid_command(name="rank", description="自分のランクを表示する")
    async def rank(self, ctx: commands.Context):
        messages = get_user(ctx.author.id)
        buffer = generate_rank_card(ctx.author, messages)
        file = discord.File(buffer, filename="rank.png")
        await ctx.reply(file=file)

async def setup(bot):
    await bot.add_cog(RankCog(bot))