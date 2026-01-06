import discord
from discord.ext import commands
import json
import os
from datetime import datetime

DATA_FILE = "data/omikuji.json"
CONTROL_FILE = "data/omikuji_control.json"

RESULTS = ["ござ吉", "大吉", "中吉", "小吉", "吉", "末吉", "凶", "大凶"]
MAX_PRESETS = 5

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
                "mode": "normal",   # normal / custom / preset
                "weights": {r: 1 for r in RESULTS},
                "active_preset": None,
                "presets": {}
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
class TesterModal(discord.ui.Modal, title="テスターモード切替"):
    user_id = discord.ui.TextInput(label="ユーザーID")

    async def on_submit(self, interaction: discord.Interaction):
        control = load_control()
        uid = self.user_id.value.strip()

        if uid in control["tester"]:
            control["tester"].remove(uid)
            msg = "❌ テスターモードから解除しました。"
        else:
            control["tester"].append(uid)
            msg = "✅ テスターモードに設定しました。"

        save_control(control)
        await interaction.response.send_message(msg, ephemeral=True)

class UserStatusModal(discord.ui.Modal, title="ユーザー状態確認"):
    user_id = discord.ui.TextInput(label="ユーザーID")

    async def on_submit(self, interaction: discord.Interaction):
        data = load_data()
        uid = self.user_id.value.strip()

        if uid not in data:
            return await interaction.response.send_message(
                "このユーザーはまだおみくじを引いていません。",
                ephemeral=True
            )

        info = data[uid]
        today = datetime.now().strftime("%Y-%m-%d")

        embed = discord.Embed(
            title="👤 ユーザーおみくじ状態",
            color=discord.Color.green()
        )
        embed.add_field(name="最後に引いた日", value=info["last_date"], inline=False)
        embed.add_field(name="連続参拝日数", value=f'{info["count"]}日', inline=False)
        embed.add_field(
            name="今日引いたか",
            value="はい" if info["last_date"] == today else "いいえ",
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

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
        control["probability"]["active_preset"] = None
        save_control(control)

        await interaction.response.send_message(
            "✅ カスタム確率を設定しました。\nプリセットとして保存することもできます。",
            ephemeral=True
        )

class PresetNameModal(discord.ui.Modal, title="プリセット名を入力"):
    name = discord.ui.TextInput(label="プリセット名")

    async def on_submit(self, interaction: discord.Interaction):
        control = load_control()
        presets = control["probability"]["presets"]

        if len(presets) >= MAX_PRESETS:
            return await interaction.response.send_message(
                "❌ プリセットは最大5個までです。",
                ephemeral=True
            )

        presets[self.name.value] = control["probability"]["weights"]
        control["probability"]["mode"] = "preset"
        control["probability"]["active_preset"] = self.name.value

        save_control(control)
        await interaction.response.send_message(
            f"✅ プリセット **{self.name.value}** を保存しました。",
            ephemeral=True
        )

# =====================
# View
# =====================
class OmikujiControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="テスターモード切替", style=discord.ButtonStyle.green, custom_id="omikuji:tester")
    async def tester(self, interaction: discord.Interaction, _):
        await interaction.response.send_modal(TesterModal())

    @discord.ui.button(label="ユーザー状態確認", style=discord.ButtonStyle.gray, custom_id="omikuji:status")
    async def status(self, interaction: discord.Interaction, _):
        await interaction.response.send_modal(UserStatusModal())

    @discord.ui.button(label="確率変更（カスタム）", style=discord.ButtonStyle.blurple, custom_id="omikuji:prob")
    async def prob(self, interaction: discord.Interaction, _):
        await interaction.response.send_modal(ProbabilityModal())

    @discord.ui.button(label="プリセットとして保存", style=discord.ButtonStyle.green, custom_id="omikuji:save_preset")
    async def save_preset(self, interaction: discord.Interaction, _):
        await interaction.response.send_modal(PresetNameModal())

    @discord.ui.button(label="確率確認", style=discord.ButtonStyle.secondary, custom_id="omikuji:check")
    async def check(self, interaction: discord.Interaction, _):
        control = load_control()
        prob = control["probability"]

        desc = (
            "現在は **均等確率**"
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
            description="モーダル対応 管理UI（プリセット対応）",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed, view=OmikujiControlView())

async def setup(bot):
    bot.add_view(OmikujiControlView())
    await bot.add_cog(OmikujiControlCog(bot))