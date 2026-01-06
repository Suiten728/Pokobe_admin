import discord
from discord.ext import commands
import json
import os

CONTROL_FILE = "data/omikuji_control.json"

RESULTS = ["ござ吉", "大吉", "中吉", "小吉", "吉", "末吉", "凶", "大凶"]


# -------------------
# JSON操作
# -------------------
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


# -------------------
# 表示用計算
# -------------------
def format_probability(weights):
    total = sum(weights.values())
    lines = []

    for k in RESULTS:
        v = weights.get(k, 1)
        percent = (v / total) * 100 if total else 0
        inv = round(total / v, 2) if v else "∞"

        lines.append(
            f"**{k}** ： {percent:.2f}%（1 / {inv}）"
        )

    return "\n".join(lines)


# ===================
# プルダウン
# ===================
class ProbabilitySelect(discord.ui.Select):
    def __init__(self):
        super().__init__(
            placeholder="おみくじ確率モードを選択",
            options=[
                discord.SelectOption(label="通常", description="全て同じ確率", value="normal"),
                discord.SelectOption(label="カスタム", description="確率を自由に設定", value="custom")
            ],
            custom_id="omikuji:prob_mode"
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != interaction.client.owner_id:
            return await interaction.response.send_message("オーナーのみ使用できます。", ephemeral=True)

        control = load_control()
        control["probability"]["mode"] = self.values[0]
        save_control(control)

        await interaction.response.send_message(
            f"確率モードを **{self.values[0]}** に設定しました。",
            ephemeral=True
        )


# ===================
# 管理View
# ===================
class OmikujiControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ProbabilitySelect())

    @discord.ui.button(label="カスタム確率を設定", style=discord.ButtonStyle.blurple)
    async def set_prob(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != interaction.client.owner_id:
            return await interaction.response.send_message("オーナーのみ使用できます。", ephemeral=True)

        await interaction.response.send_message(
            "以下の形式で送ってください（数字は重み）\n\n"
            "大吉 5\n中吉 4\n小吉 3\n吉 3\n末吉 2\n凶 1\n大凶 1",
            ephemeral=True
        )

        def check(m):
            return m.author == interaction.user and m.channel == interaction.channel

        msg = await interaction.client.wait_for("message", check=check)

        weights = {}
        for line in msg.content.splitlines():
            try:
                k, v = line.split()
                if k in RESULTS:
                    weights[k] = int(v)
            except:
                pass

        control = load_control()
        control["probability"]["weights"] = weights
        control["probability"]["mode"] = "custom"
        save_control(control)

        await interaction.followup.send("✅ カスタム確率を保存しました。", ephemeral=True)

    @discord.ui.button(label="確率を確認", style=discord.ButtonStyle.green)
    async def check_prob(self, interaction: discord.Interaction, button: discord.ui.Button):
        control = load_control()
        prob = control["probability"]

        if prob["mode"] == "normal":
            desc = "現在は **全て均等確率** です。"
        else:
            desc = format_probability(prob["weights"])

        embed = discord.Embed(
            title="🎯 おみくじ確率一覧",
            description=desc,
            color=discord.Color.green()
        )
        embed.set_footer(text=f"モード：{prob['mode']}")

        await interaction.response.send_message(embed=embed, ephemeral=True)


# ===================
# Cog
# ===================
class OmikujiControlCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="omikuji_ctrl")
    @commands.is_owner()
    async def ctrl(self, ctx):
        embed = discord.Embed(
            title="🍃 おみくじ管理パネル",
            description="確率設定・確認ができます。",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed, view=OmikujiControlView())


async def setup(bot):
    bot.add_view(OmikujiControlView())
    await bot.add_cog(OmikujiControlCog(bot))
