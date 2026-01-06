import discord
from discord.ext import commands
import json
import os
from datetime import datetime

DATA_FILE = "data/omikuji.json"
CONTROL_FILE = "data/omikuji_control.json"

RESULTS = ["ござ吉", "大吉", "中吉", "小吉", "吉", "末吉", "凶", "大凶"]

# =====================
# JSON操作
# =====================
def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_control():
    if not os.path.exists(CONTROL_FILE):
        return {
            "tester": [],
            "probability": {
                "mode": "normal",
                "weights": {r: 1 for r in RESULTS}
            }
        }
    with open(CONTROL_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_control(data):
    with open(CONTROL_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# =====================
# 表示用
# =====================
def format_probability(weights):
    total = sum(weights.values())
    lines = []

    for r in RESULTS:
        v = weights.get(r, 1)
        percent = (v / total) * 100 if total else 0
        inv = round(total / v, 2) if v else "∞"
        lines.append(f"**{r}** ： {percent:.2f}%（1 / {inv}）")

    return "\n".join(lines)

# =====================
# Modals
# =====================
class TesterModal(discord.ui.Modal, title="テスターモード設定"):
    user_id = discord.ui.TextInput(label="ユーザーID")

    async def on_submit(self, interaction: discord.Interaction):
        control = load_control()
        uid = self.user_id.value.strip()

        if uid not in control["tester"]:
            control["tester"].append(uid)
            save_control(control)

        await interaction.response.send_message("✅ テスターモードに設定しました。", ephemeral=True)

class EditStreakModal(discord.ui.Modal, title="連続参拝日数変更"):
    user_id = discord.ui.TextInput(label="ユーザーID")
    days = discord.ui.TextInput(label="新しい連続日数", placeholder="数字")

    async def on_submit(self, interaction: discord.Interaction):
        try:
            days = int(self.days.value)
        except:
            return await interaction.response.send_message("❌ 日数は数字で入力してください。", ephemeral=True)

        data = load_data()
        uid = self.user_id.value.strip()

        if uid not in data:
            data[uid] = {
                "last_date": datetime.now().strftime("%Y-%m-%d"),
                "count": days
            }
        else:
            data[uid]["count"] = days

        save_data(data)
        await interaction.response.send_message("✅ 連続日数を変更しました。", ephemeral=True)

class ResetUserModal(discord.ui.Modal, title="記録リセット"):
    user_id = discord.ui.TextInput(label="ユーザーID")

    async def on_submit(self, interaction: discord.Interaction):
        data = load_data()
        uid = self.user_id.value.strip()

        if uid in data:
            del data[uid]
            save_data(data)
            await interaction.response.send_message("✅ 記録をリセットしました。", ephemeral=True)
        else:
            await interaction.response.send_message("記録が存在しません。", ephemeral=True)

class ProbabilityModal(discord.ui.Modal, title="カスタム確率設定"):
    weights = discord.ui.TextInput(
        label="確率（重み）",
        style=discord.TextStyle.paragraph,
        placeholder="ござ吉 1\n大吉 10\n中吉 10\n小吉 10\n吉 10\n末吉 10\n凶 10\n大凶 10"
    )

    async def on_submit(self, interaction: discord.Interaction):
        weights = {}
        for line in self.weights.value.splitlines():
            try:
                k, v = line.split()
                if k in RESULTS:
                    weights[k] = int(v)
            except:
                pass

        control = load_control()
        control["probability"]["mode"] = "custom"
        control["probability"]["weights"] = weights
        save_control(control)

        await interaction.response.send_message("✅ カスタム確率を保存しました。", ephemeral=True)

# =====================
# View
# =====================
class OmikujiControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="テスターモード設定", style=discord.ButtonStyle.green, custom_id="omikuji:tester")
    async def tester(self, interaction: discord.Interaction, _):
        await interaction.response.send_modal(TesterModal())

    @discord.ui.button(label="連続日数変更", style=discord.ButtonStyle.blurple, custom_id="omikuji:streak")
    async def streak(self, interaction: discord.Interaction, _):
        await interaction.response.send_modal(EditStreakModal())

    @discord.ui.button(label="記録リセット", style=discord.ButtonStyle.red, custom_id="omikuji:reset")
    async def reset(self, interaction: discord.Interaction, _):
        await interaction.response.send_modal(ResetUserModal())

    @discord.ui.button(label="今日引いた人数", style=discord.ButtonStyle.gray, custom_id="omikuji:today")
    async def today(self, interaction: discord.Interaction, _):
        data = load_data()
        today = datetime.now().strftime("%Y-%m-%d")
        users = [f"<@{uid}>" for uid, v in data.items() if v["last_date"] == today]

        embed = discord.Embed(
            title="📅 今日おみくじを引いた人",
            description="\n".join(users) if users else "誰も引いていません。",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="確率変更", style=discord.ButtonStyle.blurple, custom_id="omikuji:prob")
    async def prob(self, interaction: discord.Interaction, _):
        await interaction.response.send_modal(ProbabilityModal())

    @discord.ui.button(label="確率確認", style=discord.ButtonStyle.green, custom_id="omikuji:check")
    async def check(self, interaction: discord.Interaction, _):
        control = load_control()
        prob = control["probability"]

        desc = (
            "現在は **均等確率** です。"
            if prob["mode"] == "normal"
            else format_probability(prob["weights"])
        )

        embed = discord.Embed(
            title="🎯 おみくじ確率",
            description=desc,
            color=discord.Color.green()
        )
        embed.set_footer(text=f"モード：{prob['mode']}")
        await interaction.response.send_message(embed=embed, ephemeral=True)

# =====================
# Cog
# =====================
class OmikujiControlCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="omikuji_ctrl")
    @commands.is_owner()
    async def ctrl(self, ctx):
        embed = discord.Embed(
            title="🍃 おみくじ管理パネル",
            description="モーダル対応 管理UI",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed, view=OmikujiControlView())

async def setup(bot):
    bot.add_view(OmikujiControlView())
    await bot.add_cog(OmikujiControlCog(bot))