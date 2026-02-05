import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import json
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path="ci/.env")
channel_id_env = os.getenv("MAKING_VC_CHANNEL_ID")
if channel_id_env is None:
    raise ValueError("⚠ MAKING_VC_CHANNEL_ID が .env に設定されていません")

MAKING_VC_CHANNEL_ID = int(channel_id_env)
DATA_FILE = "data/voice_rooms.json"


class VoiceRoomManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        if not os.path.exists(DATA_FILE):
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                f.write("{}")

        with open(DATA_FILE, "r", encoding="utf-8") as f:
            self.rooms = json.load(f)

    def save(self):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(self.rooms, f, indent=4, ensure_ascii=False)

    # -----------------------------
    #   VC入退室監視
    # -----------------------------
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):

        if after.channel and after.channel.id == MAKING_VC_CHANNEL_ID:
            await self.create_private_room(member, after.channel)

        if not before.channel:
            return

        for owner_id, data in list(self.rooms.get("active", {}).items()):
            if before.channel.id == data["voice_id"]:
                if len(before.channel.members) == 0:
                    text = member.guild.get_channel(data["text_id"])
                    await before.channel.delete()
                    if text:
                        await text.delete()

                    del self.rooms["active"][owner_id]
                    self.save()

    # -----------------------------
    #   個室作成
    # -----------------------------
    async def create_private_room(self, member, create_channel):
        guild = member.guild
        category = create_channel.category

        voice = await guild.create_voice_channel(
            name=f"{member.name} の部屋",
            category=category
        )

        text = await guild.create_text_channel(
            name=f"{member.name}の部屋",
            category=category
        )

        if "active" not in self.rooms:
            self.rooms["active"] = {}

        self.rooms["active"][str(member.id)] = {
            "voice_id": voice.id,
            "text_id": text.id
        }
        self.save()

        await text.send(
            content=f"{member.mention} さんの個室が作成されました！",
            embed=self.panel_embed(member, voice),
            view=self.PanelButtons(self)
        )

        await member.move_to(voice)

    # -----------------------------
    #   Embed
    # -----------------------------
    def panel_embed(self, member, voice):
        emb = discord.Embed(
            title="個室コントロールパネル",
            description=f"部屋: **{voice.name}**",
            color=0x00AAFF
        )
        emb.add_field(name="🖊 名前変更", value="VCの名前を変更できます！", inline=False)
        emb.add_field(name="👤 人数制限", value="最大人数を設定できます！0に設定すると無制限になります。", inline=False)
        emb.add_field(name="🔐 公開/非公開", value="他のユーザーからVCが見えるかを変更できます！", inline=False)
        return emb

    # -----------------------------
    #   永続 View
    # -----------------------------
    class PanelButtons(discord.ui.View):
        def __init__(self, cog):
            super().__init__(timeout=None)
            self.cog = cog

        def get_room(self, interaction):
            if not interaction.message.mentions:
                return None
            owner_id = interaction.message.mentions[0].id
            return owner_id, self.cog.rooms.get("active", {}).get(str(owner_id))

        @discord.ui.button(
            label="🖊 名前変更",
            style=discord.ButtonStyle.blurple,
            custom_id="vc:rename"
        )
        async def rename_room(self, interaction: discord.Interaction, button: discord.ui.Button):
            data = self.get_room(interaction)
            if not data or not data[1]:
                return await interaction.response.send_message("部屋が見つかりません", ephemeral=True)

            owner_id, room = data
            await interaction.response.send_modal(
                VoiceRoomManager.RenameModal(
                    self.cog,
                    room["voice_id"],
                    room["text_id"]
                )
            )

        @discord.ui.button(
            label="👤 人数制限",
            style=discord.ButtonStyle.green,
            custom_id="vc:limit"
        )
        async def limit_room(self, interaction: discord.Interaction, button: discord.ui.Button):
            data = self.get_room(interaction)
            if not data or not data[1]:
                return await interaction.response.send_message("部屋が見つかりません", ephemeral=True)

            owner_id, room = data
            await interaction.response.send_modal(
                VoiceRoomManager.LimitModal(self.cog, room["voice_id"])
            )

        @discord.ui.button(
            label="🔐 公開/非公開",
            style=discord.ButtonStyle.red,
            custom_id="vc:toggle"
        )
        async def toggle_private(self, interaction: discord.Interaction, button: discord.ui.Button):
            data = self.get_room(interaction)
            if not data or not data[1]:
                return await interaction.response.send_message("部屋が見つかりません", ephemeral=True)

            owner_id, room = data
            voice = interaction.guild.get_channel(room["voice_id"])
            overwrites = voice.overwrites
            everyone = interaction.guild.default_role

            if overwrites.get(everyone) and overwrites[everyone].view_channel is False:
                overwrites[everyone] = discord.PermissionOverwrite(view_channel=True)
                msg = "公開にしました"
            else:
                overwrites[everyone] = discord.PermissionOverwrite(view_channel=False)
                msg = "非公開にしました"

            await voice.edit(overwrites=overwrites)
            await interaction.response.send_message(msg, ephemeral=True)

    # -----------------------------
    #   Modal
    # -----------------------------
    class RenameModal(discord.ui.Modal, title="名前変更"):
        def __init__(self, cog, voice_id, text_id):
            super().__init__()
            self.voice_id = voice_id
            self.text_id = text_id
            self.new_name = discord.ui.TextInput(label="新しい名前", max_length=32)
            self.add_item(self.new_name)

        async def on_submit(self, interaction: discord.Interaction):
            voice = interaction.guild.get_channel(self.voice_id)
            text = interaction.guild.get_channel(self.text_id)

            if not voice:
                return await interaction.response.send_message("VCがありません", ephemeral=True)

            await voice.edit(name=self.new_name.value)
            if text:
                await text.edit(name=self.new_name.value)

            await interaction.response.send_message("変更しました", ephemeral=True)

    class LimitModal(discord.ui.Modal, title="人数制限"):
        def __init__(self, cog, voice_id):
            super().__init__()
            self.voice_id = voice_id
            self.limit = discord.ui.TextInput(label="人数", max_length=2)
            self.add_item(self.limit)

        async def on_submit(self, interaction: discord.Interaction):
            try:
                limit = int(self.limit.value)
                voice = interaction.guild.get_channel(self.voice_id)
                await voice.edit(user_limit=limit)
                await interaction.response.send_message("変更しました", ephemeral=True)
            except:
                await interaction.response.send_message("数字を入力してください", ephemeral=True)


async def setup(bot):
    cog = VoiceRoomManager(bot)
    await bot.add_cog(cog)
    bot.add_view(VoiceRoomManager.PanelButtons(cog))