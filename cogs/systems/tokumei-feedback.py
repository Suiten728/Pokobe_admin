import discord
from discord.ext import commands
import json
import os
from datetime import datetime
import aiohttp
from dotenv import load_dotenv

load_dotenv("ci/.env")

TOKUMEI_WEBHOOK1_URL = os.getenv("TOKUMEI_WEBHOOK1_URL")
TOKUMEI_WEBHOOK2_URL = os.getenv("TOKUMEI_WEBHOOK2_URL")

DATA_FILE = "data/anonymous_users.json"


# ===== JSON管理 =====
def load_data():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f, ensure_ascii=False, indent=4)
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


# ===== Cog =====
class AnonymousBox(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.webhook_main_url = TOKUMEI_WEBHOOK1_URL
        self.webhook_send_url = TOKUMEI_WEBHOOK2_URL

    # 匿名番号
    def get_anonymous_number(self, user_id: int):
        data = load_data()
        date_key = datetime.now().strftime("%Y-%m-%d")

        if date_key not in data:
            data[date_key] = {}

        if str(user_id) in data[date_key]:
            return data[date_key][str(user_id)]

        num = len(data[date_key]) + 1
        data[date_key][str(user_id)] = num
        save_data(data)
        return num

    # パネル設置
    @commands.command(name="set_anonymous_panel")
    @commands.has_permissions(administrator=True)
    async def set_panel(self, ctx):
        embed = discord.Embed(
            title="匿名ご意見箱",
            description="ボタンから匿名で送信できます。",
            color=0x2ECC71
        )
        await ctx.send(embed=embed, view=AnonymousButton(self))

    # Webhook① 更新
    async def update_main_webhook_message(self, text: str):
        async with aiohttp.ClientSession() as session:
            webhook = discord.Webhook.from_url(
                self.webhook_main_url,
                session=session
            )
            await webhook.send(text)

    # Webhook② 匿名送信（ここが最重要）
    async def send_anonymous_message(self, user: discord.User, text: str):
        number = self.get_anonymous_number(user.id)

        async with aiohttp.ClientSession() as session:
            webhook = discord.Webhook.from_url(
                self.webhook_send_url,
                session=session
            )
            await webhook.send(
                content=text,
                username=f"匿名{number}",
                avatar_url=user.display_avatar.url
            )

        return number


# ===== Modal =====
class AnonymousModal(discord.ui.Modal, title="匿名メッセージ送信"):
    message = discord.ui.TextInput(
        label="内容",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=2000
    )

    def __init__(self, cog: AnonymousBox):
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction):
        num = await self.cog.send_anonymous_message(
            interaction.user,
            self.message.value
        )

        await self.cog.update_main_webhook_message("📮 新しい匿名投稿があります")

        await interaction.response.send_message(
            f"匿名{num} として送信しました。",
            ephemeral=True
        )


# ===== Button =====
class AnonymousButton(discord.ui.View):
    def __init__(self, cog: AnonymousBox):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(label="匿名で送信", style=discord.ButtonStyle.green)
    async def send(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(
            AnonymousModal(self.cog)
        )


# ===== setup =====
async def setup(bot):
    await bot.add_cog(AnonymousBox(bot))
