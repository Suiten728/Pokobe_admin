import discord
from discord.ext import commands
import json
import os
from datetime import datetime
import aiohttp
from dotenv import load_dotenv
import random

load_dotenv("ci/.env")

TOKUMEI_WEBHOOK1_URL = os.getenv("TOKUMEI_WEBHOOK1_URL")
TOKUMEI_WEBHOOK2_URL = os.getenv("TOKUMEI_WEBHOOK2_URL")

DATA_FILE = "data/anonymous_users.json"
PANEL_MESSAGE_FILE = "data/anonymous_panel_message.json"

# Discord初期アバター色
DISCORD_COLORS = [
    "6D28D9",  # 紫
    "3B82F6",  # 青
    "EF4444",  # 赤
    "F59E0B",  # オレンジ
    "10B981",  # 緑
]


# ===== JSON管理 =====
def load_data():
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f, ensure_ascii=False, indent=4)
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def load_panel_info():
    os.makedirs(os.path.dirname(PANEL_MESSAGE_FILE), exist_ok=True)
    if not os.path.exists(PANEL_MESSAGE_FILE):
        return {}
    with open(PANEL_MESSAGE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_panel_info(channel_id: int, message_id: int):
    with open(PANEL_MESSAGE_FILE, "w", encoding="utf-8") as f:
        json.dump({"channel_id": channel_id, "message_id": message_id}, f)


# ===== Button (永続化対応) =====
class AnonymousButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="匿名で送信",
        style=discord.ButtonStyle.green,
        custom_id="anonymous_send_button_persistent"
    )
    async def send(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AnonymousModal())


# ===== Modal =====
class AnonymousModal(discord.ui.Modal, title="匿名メッセージ送信"):
    message = discord.ui.TextInput(
        label="内容",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=2000,
        placeholder="ここに意見を入力してください..."
    )

    def __init__(self):
        super().__init__()

    async def on_submit(self, interaction: discord.Interaction):
        # Cogのインスタンスを取得
        cog = interaction.client.get_cog("AnonymousBox")
        if not cog:
            await interaction.response.send_message(
                "エラー: システムが利用できません。",
                ephemeral=True
            )
            return

        num = await cog.send_anonymous_message(
            interaction.user,
            self.message.value
        )

        # パネルを最新位置に再送信
        await cog.refresh_panel()

        await interaction.response.send_message(
            f"匿名{num} として送信しました。",
            ephemeral=True
        )


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

    # パネル再送信（常に最新位置に）
    async def refresh_panel(self):
        panel_info = load_panel_info()
        if not panel_info:
            return

        channel = self.bot.get_channel(panel_info.get("channel_id"))
        if not channel:
            return

        # 古いメッセージを削除
        try:
            old_message = await channel.fetch_message(panel_info["message_id"])
            await old_message.delete()
        except:
            pass

        # 新しいメッセージを送信
        embed = discord.Embed(
            title="匿名ご意見箱",
            description="ボタンから匿名で送信できます。",
            color=0x2ECC71
        )
        
        new_message = await channel.send(embed=embed, view=AnonymousButton())
        save_panel_info(channel.id, new_message.id)

    # パネル設置
    @commands.command(name="set_anonymous_panel")
    @commands.has_permissions(administrator=True)
    async def set_panel(self, ctx):
        # コマンドメッセージを削除
        try:
            await ctx.message.delete()
        except:
            pass

        embed = discord.Embed(
            title="匿名ご意見箱",
            description="ボタンから匿名で送信できます。",
            color=0x2ECC71
        )
        
        # パネルを送信
        message = await ctx.send(embed=embed, view=AnonymousButton())
        
        # メッセージIDを保存
        save_panel_info(ctx.channel.id, message.id)

    # Webhook② 匿名送信
    async def send_anonymous_message(self, user: discord.User, text: str):
        number = self.get_anonymous_number(user.id)
        
        # ランダムな初期アバター
        avatar_url = f"https://cdn.discordapp.com/embed/avatars/{random.randint(0, 5)}.png"

        async with aiohttp.ClientSession() as session:
            webhook = discord.Webhook.from_url(
                self.webhook_send_url,
                session=session
            )
            await webhook.send(
                content=text,
                username=f"匿名{number}",
                avatar_url=avatar_url
            )

        return number


# ===== setup =====
async def setup(bot):
    cog = AnonymousBox(bot)
    await bot.add_cog(cog)
    
    # Bot起動時にViewを永続化登録
    bot.add_view(AnonymousButton())