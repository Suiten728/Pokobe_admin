import discord
from discord.ext import commands
import json
import os
from datetime import datetime

DATA_FILE = "ci/data/omikuji.json"
CONTROL_FILE = "ci/data/omikuji_control.json"


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
        return {"tester": []}
    with open(CONTROL_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_control(data):
    with open(CONTROL_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


# ==================
#   永続ボタン
# ==================
class OmikujiControlView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    # ① テスターモード設定
    @discord.ui.button(label="テスターモード設定", style=discord.ButtonStyle.green, custom_id="omikuji:set_tester")
    async def set_tester(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != interaction.client.owner_id:
            return await interaction.response.send_message("オーナーのみ使用できます。", ephemeral=True)

        await interaction.response.send_message("テスターモードにしたい人をメンション or ID で送ってください。", ephemeral=True)

        def check(msg):
            return msg.author.id == interaction.user.id and msg.channel == interaction.channel

        msg = await interaction.client.wait_for("message", check=check)
        user = None

        if msg.mentions:
            user = msg.mentions[0]
        else:
            try:
                user = await interaction.guild.fetch_member(int(msg.content))
            except:
                return await interaction.followup.send("ユーザーが見つかりません。", ephemeral=True)

        control = load_control()
        if str(user.id) not in control["tester"]:
            control["tester"].append(str(user.id))
            save_control(control)

        await interaction.followup.send(f"{user.mention} をテスターモードに設定しました！", ephemeral=True)

    # ② 連続参拝日数の変更
    @discord.ui.button(label="連続日数を変更", style=discord.ButtonStyle.blurple, custom_id="omikuji:edit_streak")
    async def edit_streak(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != interaction.client.owner_id:
            return await interaction.response.send_message("オーナーのみ使用できます。", ephemeral=True)

        await interaction.response.send_message("対象ユーザーをメンション or ID で送信してください。", ephemeral=True)

        def check(msg):
            return msg.author.id == interaction.user.id and msg.channel == interaction.channel
        msg = await interaction.client.wait_for("message", check=check)

        if msg.mentions:
            user = msg.mentions[0]
        else:
            try:
                user = await interaction.guild.fetch_member(int(msg.content))
            except:
                return await interaction.followup.send("ユーザーが見つかりません。", ephemeral=True)

        await interaction.followup.send("新しい連続参拝日数を送ってください。", ephemeral=True)
        msg2 = await interaction.client.wait_for("message", check=check)

        try:
            new_count = int(msg2.content)
        except:
            return await interaction.followup.send("数字で入力してください。", ephemeral=True)

        data = load_data()
        user_id = str(user.id)

        if user_id not in data:
            data[user_id] = {"last_date": datetime.now().strftime("%Y-%m-%d"), "count": 0}

        data[user_id]["count"] = new_count
        save_data(data)

        await interaction.followup.send(f"{user.mention} の連続参拝日数を **{new_count}日** に変更しました！", ephemeral=True)

    # ③ 記録リセット
    @discord.ui.button(label="記録リセット", style=discord.ButtonStyle.red, custom_id="omikuji:reset_user")
    async def reset_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != interaction.client.owner_id:
            return await interaction.response.send_message("オーナーのみ使用できます。", ephemeral=True)

        await interaction.response.send_message("リセットしたいユーザーをメンション or ID で送信してください。", ephemeral=True)

        def check(msg):
            return msg.author.id == interaction.user.id and msg.channel == interaction.channel
        msg = await interaction.client.wait_for("message", check=check)

        if msg.mentions:
            user = msg.mentions[0]
        else:
            try:
                user = await interaction.guild.fetch_member(int(msg.content))
            except:
                return await interaction.followup.send("ユーザーが見つかりません。", ephemeral=True)

        data = load_data()
        user_id = str(user.id)

        if user_id in data:
            del data[user_id]
            save_data(data)
            await interaction.followup.send(f"{user.mention} の記録をリセットしました！", ephemeral=True)
        else:
            await interaction.followup.send("記録がありません。", ephemeral=True)

    # ④ 今日引いた人一覧
    @discord.ui.button(label="今日引いた人一覧", style=discord.ButtonStyle.gray, custom_id="omikuji:today_list")
    async def today_list(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != interaction.client.owner_id:
            return await interaction.response.send_message("オーナーのみ使用できます。", ephemeral=True)

        data = load_data()
        today = datetime.now().strftime("%Y-%m-%d")

        users = [f"<@{uid}>" for uid, info in data.items() if info["last_date"] == today]

        embed = discord.Embed(
            title="📅 今日おみくじを引いた人一覧",
            description="\n".join(users) if users else "誰も引いていません。",
            color=discord.Color.green()
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)


# ===========================
#   コグ本体（prefix）
# ===========================
class OmikujiControlCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="omikuji_ctrl")
    @commands.is_owner()
    async def omikuji_control(self, ctx):
        embed = discord.Embed(
            title="🍃 おみくじ管理パネル 🍃",
            description="おみくじの設定を管理できます。",
            color=discord.Color.green()
        )

        view = OmikujiControlView(self.bot)
        await ctx.send(embed=embed, view=view)


async def setup(bot):
    # 永続化ボタンの登録
    bot.add_view(OmikujiControlView(bot))

    await bot.add_cog(OmikujiControlCog(bot))

