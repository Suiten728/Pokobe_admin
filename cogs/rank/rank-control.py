# ========================================
# rank-control.py - Rank Admin Control
# ========================================

import discord
from discord.ext import commands
from discord import app_commands
import json
import os

DATA_PATH = "data/rank_data.json"

def load_data():
    if not os.path.exists(DATA_PATH):
        return {}
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

class RankControl(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ========================================
    # Mention Toggle
    # ========================================

    @app_commands.command(name="rank_mention", description="ランクアップ通知のメンションON/OFF")
    async def rank_mention(self, interaction: discord.Interaction, enable: bool):
        data = load_data()
        uid = str(interaction.user.id)
        data.setdefault(uid, {"exp": 0})
        data[uid]["mention"] = enable
        save_data(data)

        await interaction.response.send_message(
            f"ランクアップ通知メンションを **{'ON' if enable else 'OFF'}** にしました"
        )

    # ========================================
    # EXP Control
    # ========================================

    @app_commands.command(name="rank_add_exp", description="指定ユーザーにEXPを付与")
    @app_commands.checks.has_permissions(administrator=True)
    async def add_exp(self, interaction: discord.Interaction, user: discord.Member, amount: int):
        data = load_data()
        uid = str(user.id)
        data.setdefault(uid, {"exp": 0})
        data[uid]["exp"] += amount
        save_data(data)

        await interaction.response.send_message(
            f"{user.mention} に **{amount} EXP** を付与しました"
        )

# ========================================
# Setup
# ========================================

async def setup(bot):
    await bot.add_cog(RankControl(bot))
