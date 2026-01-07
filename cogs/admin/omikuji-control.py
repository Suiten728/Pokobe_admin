import discord
from discord.ext import commands
import json
import os
from datetime import datetime

DATA_FILE = "data/omikuji/omikuji.json"
CONTROL_FILE = "data/omikuji/omikuji_control.json"

RESULTS = ["ござ吉", "大吉", "中吉", "小吉", "吉", "末吉", "凶", "大凶", "大厄日"]
MAX_PRESETS = 5

# =====================
# JSON
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
                "presets": {},
                "active_preset": None
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
            msg = "❌ テスターモードを解除しました。"
        else:
            control["tester"].append(uid)
            msg = "✅ テスターモードに設定しました。"

        save_control(control)
        await interaction.response.send_message(msg, ephemeral=True)

class StreakModal(discord.ui.Modal, title="連続日数変更"):
    user_id = discord.ui.TextInput(label="ユーザーID")
    days = discord.ui.TextInput(label="連続日数", placeholder="数字")

    async def on_submit(self, interaction: discord.Interaction):
        data = load_data()
        uid = self.user_id.value.strip()
        count = int(self.days.value)

        if uid not in data:
            data[uid] = {"last_date": datetime.now().strftime("%Y-%m-%d"), "count": 0}

        data[uid]["count"] = count
        save_data(data)

        await interaction.response.send_message("✅ 連続日数を変更しました。", ephemeral=True)

class UserInfoModal(discord.ui.Modal, title="ユーザー情報検索"):
    user_id = discord.ui.TextInput(label="ユーザーID")

    async def on_submit(self, interaction: discord.Interaction):
        data = load_data()
        uid = self.user_id.value.strip()

        if uid not in data:
            return await interaction.response.send_message("記録がありません。", ephemeral=True)

        info = data[uid]
        today = datetime.now().strftime("%Y-%m-%d")

        embed = discord.Embed(title="👤 ユーザー情報", color=discord.Color.green())
        embed.add_field(name="最終日", value=info["last_date"], inline=False)
        embed.add_field(name="連続日数", value=f'{info["count"]}日', inline=False)
        embed.add_field(name="今日引いたか", value="はい" if info["last_date"] == today else "いいえ")

        await interaction.response.send_message(embed=embed, ephemeral=True)

class ProbabilityModal(discord.ui.Modal, title="確率変更"):
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
        control["probability"]["weights"] = weights
        control["probability"]["mode"] = "custom"
        control["probability"]["active_preset"] = None
        save_control(control)

        view = SavePresetView()
        await interaction.response.send_message(
            "✅ 確率を変更しました！\nこの確率をプリセットに登録しますか？",
            view=view,
            ephemeral=True
        )

class PresetNameModal(discord.ui.Modal, title="プリセット名変更"):
    name = discord.ui.TextInput(label="プリセット名")

    async def on_submit(self, interaction: discord.Interaction):
        control = load_control()
        presets = control["probability"]["presets"]

        if len(presets) >= MAX_PRESETS:
            return await interaction.response.send_message("❌ プリセットは最大5個までです。", ephemeral=True)

        presets[self.name.value] = control["probability"]["weights"]
        control["probability"]["mode"] = "preset"
        control["probability"]["active_preset"] = self.name.value

        save_control(control)
        await interaction.response.send_message("✅ プリセットを保存しました。", ephemeral=True)

# =====================
# Views
# =====================
class SavePresetView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="登録する", style=discord.ButtonStyle.green, custom_id="omikuji:save_yes")
    async def yes(self, interaction: discord.Interaction, _):
        await interaction.response.send_modal(PresetNameModal())

    @discord.ui.button(label="登録しない", style=discord.ButtonStyle.gray, custom_id="omikuji:save_no")
    async def no(self, interaction: discord.Interaction, _):
        await interaction.response.send_message("❌ 登録しませんでした。", ephemeral=True)

class PresetSelect(discord.ui.Select):
    def __init__(self):
        control = load_control()
        options = [discord.SelectOption(label="通常", value="normal")]

        for name in control["probability"]["presets"]:
            options.append(discord.SelectOption(label=name, value=name))

        super().__init__(
            placeholder="確率プリセット選択",
            options=options,
            custom_id="omikuji:preset_select"
        )

    async def callback(self, interaction: discord.Interaction):
        control = load_control()
        val = self.values[0]

        if val == "normal":
            control["probability"]["mode"] = "normal"
        else:
            control["probability"]["mode"] = "preset"
            control["probability"]["weights"] = control["probability"]["presets"][val]
            control["probability"]["active_preset"] = val

        save_control(control)
        await interaction.response.send_message("✅ プリセットを適用しました。", ephemeral=True)

class OmikujiControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(PresetSelect())

    @discord.ui.button(label="テスターモード切替", style=discord.ButtonStyle.green, custom_id="omikuji:tester")
    async def tester(self, i, _): await i.response.send_modal(TesterModal())

    @discord.ui.button(label="連続日数変更", style=discord.ButtonStyle.blurple, custom_id="omikuji:streak")
    async def streak(self, i, _): await i.response.send_modal(StreakModal())

    @discord.ui.button(label="記録リセット", style=discord.ButtonStyle.red, custom_id="omikuji:reset")
    async def reset(self, interaction: discord.Interaction, _):
        await interaction.response.send_message("UserIDを送信してください。", ephemeral=True)

    @discord.ui.button(label="ユーザー情報検索", style=discord.ButtonStyle.gray, custom_id="omikuji:info")
    async def info(self, i, _): await i.response.send_modal(UserInfoModal())

    @discord.ui.button(label="今日引いた人数", style=discord.ButtonStyle.secondary, custom_id="omikuji:today")
    async def today(self, interaction: discord.Interaction, _):
        data = load_data()
        today = datetime.now().strftime("%Y-%m-%d")
        users = [f"<@{u}>" for u, v in data.items() if v["last_date"] == today]
        await interaction.response.send_message(
            "\n".join(users) if users else "誰も引いていません。",
            ephemeral=True
        )

    @discord.ui.button(label="確率確認", style=discord.ButtonStyle.secondary, custom_id="omikuji:check")
    async def check(self, interaction: discord.Interaction, _):
        control = load_control()
        await interaction.response.send_message(
            format_probability(control["probability"]["weights"]),
            ephemeral=True
        )

    @discord.ui.button(label="確率変更", style=discord.ButtonStyle.blurple, custom_id="omikuji:change")
    async def change(self, i, _): await i.response.send_modal(ProbabilityModal())

# =====================
# Cog
# =====================
class OmikujiControlCog(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @commands.command(name="omikuji_ctrl")
    @commands.is_owner()
    async def ctrl(self, ctx):
        embed = discord.Embed(
            title="🍃 おみくじ管理パネル",
            description="おみくじの管理パネル",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed, view=OmikujiControlView())

async def setup(bot):
    bot.add_view(OmikujiControlView())
    await bot.add_cog(OmikujiControlCog(bot))
