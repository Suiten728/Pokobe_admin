import discord
from discord.ext import commands
import sqlite3
import os
import matplotlib.pyplot as plt
from matplotlib import font_manager, rcParams

# =====================
# パス設定
# =====================
DB_PATH = "data/omikuji/omikuji_stats.db"
IMG_PATH = "data/omikuji/images/omikuji_stats.png"

# =====================
# 日本語フォント（存在チェック付き）
# =====================
FONT_CANDIDATES = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/ipafont-gothic/ipag.ttf",
]

for path in FONT_CANDIDATES:
    if os.path.exists(path):
        font_prop = font_manager.FontProperties(fname=path)
        rcParams["font.family"] = font_prop.get_name()
        break

rcParams["axes.unicode_minus"] = False

# =====================
# 結果一覧
# =====================
RESULTS = ["ござ吉", "大吉", "中吉", "小吉", "吉", "末吉", "凶", "大凶", "大厄日"]

# =====================
# DB初期化
# =====================
def init_db():
    os.makedirs("data/omikuji/images", exist_ok=True)

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            result TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)

# =====================
# データ取得
# =====================
def fetch_stats():
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("""
        SELECT result, COUNT(*) 
        FROM stats 
        GROUP BY result
        """)
        return cur.fetchall()

# =====================
# グラフ生成
# =====================
def generate_graph():
    rows = fetch_stats()

    # 全結果を0で初期化
    counts = {r: 0 for r in RESULTS}

    # DBの値を反映
    for result, count in rows:
        if result in counts:
            counts[result] = count

    labels = list(counts.keys())
    values = list(counts.values())

    plt.figure(figsize=(10, 5))
    plt.bar(labels, values)
    plt.title("おみくじ結果 統計")
    plt.xlabel("結果")
    plt.ylabel("回数")

    max_count = max(values) if values else 0
    plt.yticks(range(0, max_count + 1, 1))

    plt.tight_layout()
    plt.savefig(IMG_PATH)
    plt.close()

# =====================
# Cog
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
        rows = fetch_stats()

        if not rows:
            return await ctx.reply("📊 まだ統計データがありません。")

        generate_graph()

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