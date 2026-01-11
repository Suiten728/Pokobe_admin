# ========================================
# rank.py - Rank System Core
# Version: 1.14.0
# ========================================

import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
import json
import math
from datetime import datetime
from dotenv import load_dotenv

load_dotenv("ci/.env")

LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID"))
OWNER_ID = int(os.getenv("OWNER_ID"))
RANK_NOTIFICATION_CHANNEL_ID = int(os.getenv("RANK_NOTIFICATION_CHANNEL_ID"))

DATA_PATH = "data/rank_data.json"
BG_IMAGE_PATH = "assets/rank_bg.png"

# ========================================
# Rank Definitions
# ========================================

RANK_ROLES = {
    1: "🔰｜見習い訓練兵",
    5: "🌸｜慣れてきた隊士",
    10: "🌱｜馴染んできた隊士",
    20: "🛡｜一人前の隊士",
    30: "⚔｜リラックスした隊士",
    40: "🏅｜すべてを熟知している隊士",
    50: "👑｜凄腕のベテラン隊士",
    75: "🌟｜戦場を生き抜いた隊士",
    100: "👑｜熟練した隊長"
}

LOG_TRIGGER_LEVELS = RANK_ROLES.keys()

# ========================================
# Utility Functions
# ========================================

def exp_for_level(level: int) -> int:
    return 40 * level

def total_exp_for_level(level: int) -> int:
    return 20 * level * (level + 1)

def calc_level(total_exp: int) -> int:
    return int((math.sqrt(1 + total_exp / 10) - 1) / 2)

def load_data():
    if not os.path.exists(DATA_PATH):
        return {}
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# ========================================
# Rank Cog
# ========================================

class Rank(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.data = load_data()

    # ========================================
    # EXP Add
    # ========================================

    async def add_exp(self, member: discord.Member, amount: int):
        uid = str(member.id)
        before_exp = self.data.get(uid, {}).get("exp", 0)
        before_level = calc_level(before_exp)

        self.data.setdefault(uid, {"exp": 0, "mention": True})
        self.data[uid]["exp"] += amount

        after_exp = self.data[uid]["exp"]
        after_level = calc_level(after_exp)

        save_data(self.data)

        if after_level > before_level:
            await self.handle_level_up(member, before_level, after_level)

    # ========================================
    # Level Up Handling
    # ========================================

    async def handle_level_up(self, member, before_lv, after_lv):
        guild = member.guild
        notify_ch = guild.get_channel(RANK_NOTIFICATION_CHANNEL_ID)

        for lv in LOG_TRIGGER_LEVELS:
            if before_lv < lv <= after_lv:
                await self.assign_rank_role(member, lv)

                if notify_ch:
                    mention = member.mention if self.data[str(member.id)].get("mention", True) else member.display_name
                    await notify_ch.send(
                        f"{mention} さんが **Lv.{lv}** に到達しました！🎉"
                    )

                await self.log_rank_change(member, lv)

    # ========================================
    # Role Assignment
    # ========================================

    async def assign_rank_role(self, member: discord.Member, level: int):
        guild = member.guild
        role_name = RANK_ROLES[level]

        role = discord.utils.get(guild.roles, name=role_name)
        if role is None:
            role = await guild.create_role(
                name=role_name,
                colour=discord.Colour.light_grey()
            )

        try:
            await member.add_roles(role, reason="Rank Up")
        except discord.Forbidden:
            await self.notify_permission_error(guild)

    # ========================================
    # Logging
    # ========================================

    async def log_rank_change(self, member, level):
        log_ch = member.guild.get_channel(LOG_CHANNEL_ID)
        if not log_ch:
            return

        embed = discord.Embed(
            title="ランクロール変更ログ",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="ユーザー", value=member.mention)
        embed.add_field(name="到達レベル", value=f"Lv.{level}")
        embed.add_field(name="付与ロール", value=RANK_ROLES[level])
        embed.add_field(name="理由", value="ランク到達による自動付与", inline=False)

        await log_ch.send(embed=embed)

    # ========================================
    # Permission Error
    # ========================================

    async def notify_permission_error(self, guild):
        ch = guild.get_channel(LOG_CHANNEL_ID)
        owner = guild.get_member(OWNER_ID)
        if ch:
            embed = discord.Embed(
                title="⚠ 権限不足エラー",
                description="ランクロール操作に必要な権限が不足しています。",
                color=discord.Color.red()
            )
            if owner:
                embed.add_field(name="通知先", value=owner.mention)
            await ch.send(embed=embed)

    # ========================================
    # /rank Commands
    # ========================================

    @app_commands.command(name="rank", description="自分または指定ユーザーのランクを表示")
    async def rank(self, interaction: discord.Interaction, user: discord.Member = None):
        user = user or interaction.user
        uid = str(user.id)
        exp = self.data.get(uid, {}).get("exp", 0)
        level = calc_level(exp)

        embed = discord.Embed(
            title=f"{user.display_name} のランク",
            color=discord.Color.green()
        )
        embed.add_field(name="レベル", value=f"Lv.{level}")
        embed.add_field(name="総EXP", value=exp)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="rank_leaderboard", description="ランク上位表示")
    @app_commands.choices(type=[
        app_commands.Choice(name="normal", value="normal"),
        app_commands.Choice(name="weekly", value="weekly")
    ])
    async def leaderboard(self, interaction: discord.Interaction, type: str):
        sorted_users = sorted(
            self.data.items(),
            key=lambda x: x[1]["exp"],
            reverse=True
        )

        embed = discord.Embed(
            title="🏆 ランキング TOP10",
            color=discord.Color.gold()
        )

        rank = 1
        for uid, info in sorted_users:
            if info["exp"] <= 0:
                continue
            member = interaction.guild.get_member(int(uid))
            if member:
                embed.add_field(
                    name=f"{rank}位",
                    value=f"{member.display_name} - {info['exp']} EXP",
                    inline=False
                )
                rank += 1
            if rank > 10:
                break

        await interaction.response.send_message(embed=embed)

# ========================================
# Setup
# ========================================

async def setup(bot):
    await bot.add_cog(Rank(bot))
