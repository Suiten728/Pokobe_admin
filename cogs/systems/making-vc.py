import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import json
import os

DATA_FILE = "data/voice_rooms.json"
MAKING_VC_CHANNEl = [1444245711905620100] # 個室作成VCのチャンネルIDリスト


class VoiceRoomManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # 永続化データ読み込み
        if not os.path.exists(DATA_FILE):
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                f.write("{}")

        with open(DATA_FILE, "r", encoding="utf-8") as f:
            self.rooms = json.load(f)

    def save(self):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(self.rooms, f, indent=4, ensure_ascii=False)

    # -----------------------------
    #   個室作成VCに入室したら作成
    # -----------------------------
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):

        # 個室作成VCに入った
        if after.channel and after.channel.id in MAKING_VC_CHANNEl:
            await self.create_private_room(member, after.channel)

        # どこも関係ない場合は終了
        if not before.channel:
            return

        # 退出した部屋が登録された個室
        for owner_id, data in list(self.rooms.get("active", {}).items()):
            if before.channel.id == data["voice_id"]:
                channel = before.channel

                # VCが空になったら削除
                if len(channel.members) == 0:
                    text = member.guild.get_channel(data["text_id"])
                    await channel.delete()
                    if text:
                        await text.delete()

                    del self.rooms["active"][owner_id]
                    self.save()

    # -----------------------------
    #   個室作成処理
    # -----------------------------
    async def create_private_room(self, member, create_channel):
        guild = member.guild
        category = create_channel.category

        # VC作成
        voice = await guild.create_voice_channel(
            name=f"{member.name} の部屋",
            category=category
        )

        # 設定パネル用テキストチャンネル作成
        text = await guild.create_text_channel(
            name=f"{member.name}の部屋",
            category=category
        )

        # データ保存
        if "active" not in self.rooms:
            self.rooms["active"] = {}

        self.rooms["active"][str(member.id)] = {
            "voice_id": voice.id,
            "text_id": text.id
        }
        self.save()

        # パネル送信
        await text.send(
            content=f"{member.mention} さんの個室が作成されました！",
            embed=self.panel_embed(member, voice),
            view=self.PanelButtons(self, member.id))

        # メンバーを移動
        await member.move_to(voice)

    # -----------------------------
    #   パネルEmbed
    # -----------------------------
    def panel_embed(self, member, voice):
        emb = discord.Embed(
            title="個室コントロールパネル",
            description=f"部屋: **{voice.name}**",
            color=0x00AAFF
        )
        emb.add_field(name="名前変更", value="VCの名前を変更できます！", inline=False)
        emb.add_field(name="人数制限", value="最大人数を設定できます！0にすると制限なしになります。", inline=False)
        emb.add_field(name="公開/非公開", value="他のユーザーから見えるかを変更できます！", inline=False)
        return emb

    # -----------------------------
    # ボタン類
    # -----------------------------
    class PanelButtons(discord.ui.View):
        def __init__(self, cog, owner_id):
            super().__init__(timeout=None)
            self.cog = cog
            self.owner_id = owner_id

        # 名前変更
        @discord.ui.button(label="🖊 名前変更", style=discord.ButtonStyle.blurple, custom_id="rename_room")
        async def rename_room(self, interaction: discord.Interaction, button: discord.ui.Button):
            room = self.cog.rooms["active"].get(str(self.owner_id))
            if not room:
                return await interaction.response.send_message("部屋が見つかりません。", ephemeral=True)

            await interaction.response.send_modal(
                VoiceRoomManager.RenameModal(self.cog, room["voice_id"])
            )

        # 人数制限
        @discord.ui.button(label="👤 人数制限", style=discord.ButtonStyle.green, custom_id="limit_room")
        async def limit_room(self, interaction: discord.Interaction, button: discord.ui.Button):
            room = self.cog.rooms["active"].get(str(self.owner_id))
            if not room:
                return await interaction.response.send_message("部屋が見つかりません。", ephemeral=True)

            await interaction.response.send_modal(
                VoiceRoomManager.LimitModal(self.cog, room["voice_id"])
            )

        # 公開/非公開
        @discord.ui.button(label="🔐 公開/非公開", style=discord.ButtonStyle.red, custom_id="toggle_private")
        async def toggle_private(self, interaction: discord.Interaction, button: discord.ui.Button):
            room = self.cog.rooms["active"].get(str(self.owner_id))
            if not room:
                return await interaction.response.send_message("部屋が見つかりません。", ephemeral=True)

            voice = interaction.guild.get_channel(room["voice_id"])
            overwrites = voice.overwrites

            everyone = interaction.guild.default_role

            if overwrites.get(everyone) and overwrites[everyone].view_channel is False:
                # 非公開 → 公開
                overwrites[everyone] = discord.PermissionOverwrite(view_channel=True)
                msg = "公開に変更しました！"
            else:
                # 公開 → 非公開
                overwrites[everyone] = discord.PermissionOverwrite(view_channel=False)
                msg = "非公開に変更しました！"

            await voice.edit(overwrites=overwrites)
            await interaction.response.send_message(msg, ephemeral=True)

    # -----------------------------
    # Modal: 名前変更
    # -----------------------------
    class RenameModal(discord.ui.Modal, title="名前変更"):
        def __init__(self, cog, voice_id):
            super().__init__()
            self.cog = cog
            self.voice_id = voice_id

            self.new_name = discord.ui.TextInput(label="新しい部屋の名前", max_length=32)
            self.add_item(self.new_name)

        async def on_submit(self, interaction: discord.Interaction):
            voice = interaction.guild.get_channel(self.voice_id)
            await voice.edit(name=self.new_name.value)
            await interaction.response.send_message("名前を変更しました！", ephemeral=True)

    # -----------------------------
    # Modal: 人数制限
    # -----------------------------
    class LimitModal(discord.ui.Modal, title="人数制限変更"):
        def __init__(self, cog, voice_id):
            super().__init__()
            self.cog = cog
            self.voice_id = voice_id

            self.limit = discord.ui.TextInput(label="人数（数字）", max_length=2)
            self.add_item(self.limit)

        async def on_submit(self, interaction: discord.Interaction):
            voice = interaction.guild.get_channel(self.voice_id)
            try:
                limit = int(self.limit.value)
                await voice.edit(user_limit=limit)
                await interaction.response.send_message("人数制限を変更しました！", ephemeral=True)
            except:
                await interaction.response.send_message("数字を入力してください。", ephemeral=True)


async def setup(bot):
    await bot.add_cog(VoiceRoomManager(bot))