import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import os
import matplotlib.pyplot as plt

DB_PATH = "data/omikuji/omikuji_stats.db"
IMG_PATH = "data/omikuji/images/omikuji_stats.png"

# ============
# DB初期化
# ============
def init_db():
    os.makedirs("data", exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            result TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)

# ============
# データ取得
# ============
def fetch_stats():
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("""
        SELECT result, COUNT(*) 
        FROM stats 
        GROUP BY result
        ORDER BY COUNT(*) DESC
        """)
        return cur.fetchall()

# ============
# グラフ生成
# ============
def generate_graph(data):
    labels = [row[0] for row in data]
    counts = [row[1] for row in data]

    plt.figure(figsize=(8, 5))
    plt.bar(labels, counts)
    plt.title("おみくじ結果 統計")
    plt.xlabel("結果")
    plt.ylabel("回数")
    plt.tight_layout()

    plt.savefig(IMG_PATH)
    plt.close()

# =====================
# Cog 本体
# =====================
class OmikujiStatsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        init_db()

    @commands.hybrid_command(
        name="omikuji_stats",
        description="おみくじの統計をグラフで表示します"
    )
    async def omikuji_stats(self, ctx: commands.Context):
        data = fetch_stats()

        if not data:
            return await ctx.reply("📊 まだ統計データがありません。")

        generate_graph(data)

        file = discord.File(IMG_PATH, filename="omikuji_stats.png")
        embed = discord.Embed(
            title="📊 おみくじ統計",
            description="これまでに引かれた結果の回数です。",
            color=discord.Color.green()
        )
        embed.set_image(url="attachment://omikuji_stats.png")

        await ctx.reply(embed=embed, file=file)

# =====================
# setup
# =====================
async def setup(bot):
    await bot.add_cog(OmikujiStatsCog(bot))
