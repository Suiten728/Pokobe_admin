# anonymous_box.py
import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from datetime import datetime

# ===== JSON管理部分 =====
DATA_FILE = "data/anonymous_users.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f, ensure_ascii=False, indent=4)

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


# ===== Cog本体 =====
class AnonymousBox(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # WebhookのURL（あなたの環境に合わせて書き換えてください）
        self.webhook_main_url = "https://discord.com/api/webhooks/1444214615109140501/v4M5x-lA4UPs8JaOx_7kGuhqyn40-nCenl6enWjlmCMxDnjPAkHHX0M44fHKcNSexNAn"  # 常在メッセージ（匿名掲示板）
        self.webhook_send_url = "https://discord.com/api/webhooks/1444664381794422816/usj6YjSvyNOEvpXrd-UWa8dN2fB0AZvMjil8vjJQS1I4oXWpPogIKhjesoHOF-2csmzZ"  # 匿名番号付き投稿

        # 常在メッセージを管理（再送・削除のため）
        self.panel_message = None

    # =====================================================
    # 匿名番号の取得
    # =====================================================
    def get_anonymous_number(self, user_id: int):
        data = load_data()

        date_key = datetime.now().strftime("%Y-%m-%d")

        if date_key not in data:
            data[date_key] = {}

        # すでに番号がある → そのまま返す
        if str(user_id) in data[date_key]:
            return data[date_key][str(user_id)]

        # 新しい番号を採番
        new_number = len(data[date_key]) + 1
        data[date_key][str(user_id)] = new_number
        save_data(data)
        return new_number

    # =====================================================
    # パネルを設置するコマンド（管理者のみ）
    # =====================================================
    @commands.command(name="set_anonymous_panel")
    @commands.has_permissions(administrator=True)
    async def set_panel(self, ctx):
        embed = discord.Embed(
            title="匿名ご意見箱",
            description="下のボタンから匿名メッセージを送信できます。\n送信すると匿名番号が付与されます。",
            color=0x2ECC71,
        )
        view = AnonymousButton(self)

        msg = await ctx.send(embed=embed, view=view)
        self.panel_message = msg

    # =====================================================
    # 常在メッセージ（WebHook①）の更新
    # =====================================================
    async def update_main_webhook_message(self, channel, content: str):
        """Webhook①を常に最新に保つ"""

        # 既存メッセージ削除
        async for msg in channel.history(limit=20):
            if msg.author.bot:
                await msg.delete()

        webhook = discord.SyncWebhook.from_url(self.webhook_main_url)
        webhook.send(content)

    # =====================================================
    # 匿名投稿の送信処理
    # =====================================================
    async def send_anonymous_message(self, user: discord.User, text: str):
        number = self.get_anonymous_number(user.id)
        name = f"匿名{number}"

        webhook = discord.SyncWebhook.from_url(self.webhook_send_url)
        webhook.send(
            text,
            username=name,
            avatar_url=user.avatar.url if user.avatar else None
        )

        return number


# =====================================================
# ButtonのUI部分
# =====================================================
class AnonymousModal(discord.ui.Modal, title="匿名メッセージ送信"):
    message = discord.ui.TextInput(
        label="メッセージ内容",
        style=discord.TextStyle.paragraph,
        placeholder="ここに内容を書いてください",
        required=True,
        max_length=2000
    )

    def __init__(self, cog: AnonymousBox):
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction):
        user = interaction.user
        text = self.message.value

        num = await self.cog.send_anonymous_message(user, text)

        # Webhook①を更新（掲示板）
        await self.cog.update_main_webhook_message(interaction.channel, f"新しい匿名投稿があります！")

        await interaction.response.send_message(
            f"匿名{num} として送信しました！", ephemeral=True
        )


class AnonymousButton(discord.ui.View):
    def __init__(self, cog: AnonymousBox):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(label="匿名で送信", style=discord.ButtonStyle.green)
    async def send_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AnonymousModal(self.cog))


# ===== セットアップ =====
async def setup(bot):
    await bot.add_cog(AnonymousBox(bot))
