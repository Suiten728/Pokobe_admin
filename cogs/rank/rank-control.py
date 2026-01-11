# =====================================
# rank-control.py
# Rank Control Panel
# =====================================

import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput
import sqlite3

DB = "data/rank/rank.db"

# =====================
# DB INIT
# =====================
def init_settings():
    with sqlite3.connect(DB) as con:
        cur = con.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value INTEGER
        )
        """)
        defaults = {
            "text_exp": 5,
            "vc_exp_per_min": 5,
            "cooldown_sec": 60,
            "weekly_enabled": 1
        }
        for k, v in defaults.items():
            cur.execute("INSERT OR IGNORE INTO settings VALUES (?,?)", (k, v))

# =====================
# MODAL
# =====================
class SettingModal(Modal):
    def __init__(self, key: str, title: str):
        super().__init__(title=title)
        self.key = key
        self.value = TextInput(label="数値を入力", required=True)
        self.add_item(self.value)

    async def on_submit(self, interaction: discord.Interaction):
        with sqlite3.connect(DB) as con:
            con.execute("UPDATE settings SET value=? WHERE key=?", (int(self.value.value), self.key))
        await interaction.response.send_message("✅ 更新しました", ephemeral=True)

# =====================
# VIEW
# =====================
class RankControlView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📩 メッセージEXP", style=discord.ButtonStyle.primary)
    async def text_exp(self, interaction: discord.Interaction, _):
        await interaction.response.send_modal(SettingModal("text_exp", "メッセージEXP設定"))

    @discord.ui.button(label="🎙 VC EXP", style=discord.ButtonStyle.primary)
    async def vc_exp(self, interaction: discord.Interaction, _):
        await interaction.response.send_modal(SettingModal("vc_exp_per_min", "VC EXP/分設定"))

    @discord.ui.button(label="⏱ クールダウン", style=discord.ButtonStyle.secondary)
    async def cooldown(self, interaction: discord.Interaction, _):
        await interaction.response.send_modal(SettingModal("cooldown_sec", "クールダウン秒数"))

    @discord.ui.button(label="📊 Weekly ON/OFF", style=discord.ButtonStyle.success)
    async def weekly(self, interaction: discord.Interaction, _):
        with sqlite3.connect(DB) as con:
            cur = con.cursor()
            cur.execute("SELECT value FROM settings WHERE key='weekly_enabled'")
            val = cur.fetchone()[0]
            new = 0 if val else 1
            cur.execute("UPDATE settings SET value=?", (new,))
        await interaction.response.send_message(f"Weekly: {'ON' if new else 'OFF'}", ephemeral=True)

# =====================
# COG
# =====================
class RankControl(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        init_settings()

    @commands.command(name="rank-ctrl")
    @commands.has_permissions(administrator=True)
    async def rank_ctrl(self, ctx):
        await ctx.send("🛠 Rank Control Panel", view=RankControlView())

async def setup(bot):
    await bot.add_cog(RankControl(bot))
