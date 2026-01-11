# ============================================
# rank-control.py
# EXP Control & Award Logic
# ============================================

import discord
from discord.ext import commands, tasks
import sqlite3
import time
from dotenv import load_dotenv

load_dotenv("ci/.env")

DB_PATH = "data/rank/rank.db"

# =====================
# DB INIT
# =====================
def init_db():
    with sqlite3.connect(DB_PATH) as con:
        cur = con.cursor()

        # 設定
        cur.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value INTEGER
        )
        """)

        # users拡張
        cur.execute("""
        ALTER TABLE users ADD COLUMN last_message_exp INTEGER DEFAULT 0
        """)
        cur.execute("""
        ALTER TABLE users ADD COLUMN last_vc_exp INTEGER DEFAULT 0
        """)

        # 初期設定
        defaults = {
            "msg_exp": 5,
            "msg_cd": 60,
            "vc_exp": 10,
            "vc_interval": 300,
            "weekly_enabled": 1,
        }

        for k, v in defaults.items():
            cur.execute(
                "INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)",
                (k, v)
            )

# =====================
# UTIL
# =====================
def get_setting(key: str) -> int:
    with sqlite3.connect(DB_PATH) as con:
        cur = con.cursor()
        cur.execute("SELECT value FROM settings WHERE key=?", (key,))
        row = cur.fetchone()
        return row[0] if row else 0

def add_exp(user_id: int, amount: int, weekly: bool):
    now = int(time.time())
    with sqlite3.connect(DB_PATH) as con:
        cur = con.cursor()

        cur.execute(
            "INSERT OR IGNORE INTO users(user_id) VALUES(?)",
            (user_id,)
        )
        cur.execute(
            "UPDATE users SET exp = exp + ? WHERE user_id=?",
            (amount, user_id)
        )

        if weekly:
            cur.execute(
                "INSERT OR IGNORE INTO weekly_exp(user_id) VALUES(?)",
                (user_id,)
            )
            cur.execute(
                "UPDATE weekly_exp SET exp = exp + ? WHERE user_id=?",
                (amount, user_id)
            )

# =====================
# COG
# =====================
class RankControl(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        init_db()
        self.vc_loop.start()

    # =====================
    # MESSAGE EXP
    # =====================
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        now = int(time.time())
        msg_exp = get_setting("msg_exp")
        cooldown = get_setting("msg_cd")
        weekly = bool(get_setting("weekly_enabled"))

        with sqlite3.connect(DB_PATH) as con:
            cur = con.cursor()
            cur.execute(
                "SELECT last_message_exp FROM users WHERE user_id=?",
                (message.author.id,)
            )
            row = cur.fetchone()
            last = row[0] if row else 0

            if now - last < cooldown:
                return

            cur.execute(
                "INSERT OR IGNORE INTO users(user_id,last_message_exp) VALUES(?,?)",
                (message.author.id, now)
            )
            cur.execute(
                "UPDATE users SET last_message_exp=? WHERE user_id=?",
                (now, message.author.id)
            )

        add_exp(message.author.id, msg_exp, weekly)

    # =====================
    # VC EXP LOOP
    # =====================
    @tasks.loop(seconds=30)
    async def vc_loop(self):
        vc_exp = get_setting("vc_exp")
        interval = get_setting("vc_interval")
        weekly = bool(get_setting("weekly_enabled"))
        now = int(time.time())

        for guild in self.bot.guilds:
            for vc in guild.voice_channels:
                for member in vc.members:
                    if member.bot:
                        continue

                    with sqlite3.connect(DB_PATH) as con:
                        cur = con.cursor()
                        cur.execute(
                            "SELECT last_vc_exp FROM users WHERE user_id=?",
                            (member.id,)
                        )
                        row = cur.fetchone()
                        last = row[0] if row else 0

                        if now - last < interval:
                            continue

                        cur.execute(
                            "INSERT OR IGNORE INTO users(user_id,last_vc_exp) VALUES(?,?)",
                            (member.id, now)
                        )
                        cur.execute(
                            "UPDATE users SET last_vc_exp=? WHERE user_id=?",
                            (now, member.id)
                        )

                    add_exp(member.id, vc_exp, weekly)

    @vc_loop.before_loop
    async def before_vc(self):
        await self.bot.wait_until_ready()

async def setup(bot: commands.Bot):
    await bot.add_cog(RankControl(bot))
