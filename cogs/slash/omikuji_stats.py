import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import os
import matplotlib.pyplot as plt
from matplotlib import font_manager, rcParams

DB_PATH = "data/omikuji/omikuji_stats.db"
IMG_PATH = "data/omikuji/images/omikuji_stats.png"

# ============
# 日本語フォント設定
# ============
font_path = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
font_prop = font_manager.FontProperties(fname=font_path)

rcParams["font.family"] = font_prop.get_name()
rcParams["axes.unicode_minus"] = False

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

# ---RESULTS---
RISULTS = ["ござ吉", "大吉", "中吉", "小吉", "吉", "末吉", "凶", "大凶", "大厄日"]
# ---結果を0で初期化---
counts = {r: 0 for r in RISULTS}
# ---実際のデータを反映---
for result, count in fetch_stats():
    if result in counts:
        counts[result] = count

# ============
# グラフ生成
# ============
def generate_graph(data):
    labels = list(counts.keys())
    counts = list(counts.values())

    plt.figure(figsize=(10, 5))
    plt.bar(labels, counts)
    plt.title("おみくじ結果 統計")
    plt.xlabel("結果")
    plt.ylabel("回数")

    # Y軸を1刻みに設定
    max_count = max(counts)
    plt.yticks(range(0, max_count + 1, 1))

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
        name="おみくじ統計",
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
