import discord
from discord.ext import commands
import aiohttp
import os
from dotenv import load_dotenv

# .envファイルを読み込む
load_dotenv()
SENDER_WEBHOOK_URL = os.getenv("SENDER_WEBHOOK_URL")

# ユーザーごとのセッション管理
user_sessions = {}

class WebhookSendView(discord.ui.View):
    """送信確認用のView"""
    def __init__(self, user_id: int, message_id: int, channel_id: int, webhook_url: str, webhook_info: dict, messages_to_delete: list):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.message_id = message_id
        self.channel_id = channel_id
        self.webhook_url = webhook_url
        self.webhook_info = webhook_info
        self.messages_to_delete = messages_to_delete
        self.value = None

    @discord.ui.button(label="はい", style=discord.ButtonStyle.green)
    async def yes_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("このボタンはあなたが使用できません。", ephemeral=True)
            return

        await interaction.response.defer()
        
        # 確認メッセージも削除リストに追加
        self.messages_to_delete.append(interaction.message)
        
        # メッセージを取得
        try:
            # メッセージIDからメッセージを取得
            message = None
            for channel in interaction.client.get_all_channels():
                if isinstance(channel, discord.TextChannel):
                    try:
                        message = await channel.fetch_message(self.message_id)
                        break
                    except (discord.NotFound, discord.Forbidden):
                        continue
            
            if not message:
                await interaction.followup.send("❌ 指定されたメッセージが見つかりませんでした。", ephemeral=True)
                # メッセージを削除
                await self.delete_messages()
                self.stop()
                return
            
            # Web Hookのチャンネルを変更してから送信
            async with aiohttp.ClientSession() as session:
                # Web Hookのチャンネルを変更
                webhook_id = self.webhook_url.split('/')[-2]
                webhook_token = self.webhook_url.split('/')[-1]
                
                # Web Hookの情報を更新（チャンネルを変更）
                async with session.patch(
                    f"https://discord.com/api/v10/webhooks/{webhook_id}",
                    json={"channel_id": str(self.channel_id)},
                    headers={"Authorization": f"Bot {interaction.client.http.token}"}
                ) as resp:
                    if resp.status != 200:
                        await interaction.followup.send("❌ Web Hookのチャンネル変更に失敗しました。", ephemeral=True)
                        # メッセージを削除
                        await self.delete_messages()
                        self.stop()
                        return
                
                # Web Hookで送信
                webhook = discord.Webhook.from_url(self.webhook_url, session=session)
                
                # 添付ファイルの処理
                files = []
                if message.attachments:
                    for attachment in message.attachments:
                        file_data = await attachment.read()
                        files.append(discord.File(fp=discord.utils.BytesIO(file_data), filename=attachment.filename))
                
                # Embedの処理
                embeds = message.embeds if message.embeds else None
                
                # メッセージ送信（usernameとavatar_urlは指定しない）
                await webhook.send(
                    content=message.content if message.content else None,
                    embeds=embeds,
                    files=files if files else None,
                )
            
            await interaction.followup.send("✅ メッセージを送信しました!", ephemeral=True)
            
            # メッセージを削除
            await self.delete_messages()
            
        except discord.NotFound:
            await interaction.followup.send("❌ 指定されたメッセージが見つかりませんでした。", ephemeral=True)
            await self.delete_messages()
        except discord.Forbidden:
            await interaction.followup.send("❌ メッセージの取得またはWeb Hookの送信に失敗しました。権限を確認してください。", ephemeral=True)
            await self.delete_messages()
        except Exception as e:
            await interaction.followup.send(f"❌ エラーが発生しました: {str(e)}", ephemeral=True)
            await self.delete_messages()
        
        # セッションをクリア
        if self.user_id in user_sessions:
            del user_sessions[self.user_id]
        
        self.stop()
    
    async def delete_messages(self):
        """メッセージを削除"""
        for msg in self.messages_to_delete:
            try:
                await msg.delete()
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                # メッセージが既に削除されている、または権限がない場合は無視
                pass

    @discord.ui.button(label="いいえ", style=discord.ButtonStyle.red)
    async def no_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("このボタンはあなたが使用できません。", ephemeral=True)
            return

        await interaction.response.send_message("❌ 送信をキャンセルしました。", ephemeral=True)
        
        # 確認メッセージも削除リストに追加
        self.messages_to_delete.append(interaction.message)
        
        # メッセージを削除
        await self.delete_messages()
        
        # セッションをクリア
        if self.user_id in user_sessions:
            del user_sessions[self.user_id]
        
        self.stop()


class WebhookSenderCog(commands.Cog):
    """Web Hook送信機能のCog"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.webhook_url = SENDER_WEBHOOK_URL
        
        if not self.webhook_url:
            print("⚠️ 警告: SENDER_WEBHOOK_URLが.envファイルに設定されていません。")

    async def get_webhook_info(self) -> dict:
        """Web Hookの情報を取得"""
        try:
            webhook_id = self.webhook_url.split('/')[-2]
            async with aiohttp.ClientSession() as session:
                webhook = discord.Webhook.from_url(self.webhook_url, session=session)
                # Web Hook情報を取得
                async with session.get(f"https://discord.com/api/v10/webhooks/{webhook_id}") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return {
                            "name": data.get("name", "Unknown"),
                            "avatar": data.get("avatar"),
                            "channel_id": data.get("channel_id")
                        }
        except Exception as e:
            print(f"Web Hook情報の取得に失敗: {e}")
        
        return {"name": "Unknown", "avatar": None, "channel_id": None}

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """メッセージイベントのリスナー"""
        
        # Botのメッセージは無視
        if message.author.bot:
            return
        
        # DMは無視
        if not message.guild:
            return
        
        # メッセージの内容がNoneの場合は無視
        if message.content is None:
            return
        
        # Web Hook URLが設定されていない場合
        if not self.webhook_url:
            return
        
        user_id = message.author.id
        
        # 新しいセッション開始
        if message.content == "WH送信":
            # 既存のセッションがある場合はクリア
            if user_id in user_sessions:
                del user_sessions[user_id]
            
            user_sessions[user_id] = {
                "step": "waiting_message_id",
                "channel_id": message.channel.id,
                "messages_to_delete": [message]  # ユーザーのメッセージも追加
            }
            
            bot_msg = await message.channel.send(f"{message.author.mention} 送信するメッセージIDを送信してください。")
            user_sessions[user_id]["messages_to_delete"].append(bot_msg)
            return
        
        # セッションが存在しない場合は処理しない
        if user_id not in user_sessions:
            return
        
        session = user_sessions[user_id]
        
        # ユーザーのメッセージを削除リストに追加
        session["messages_to_delete"].append(message)
        
        # メッセージID待機中
        if session["step"] == "waiting_message_id":
            # IDの検証
            if not message.content.isdigit():
                error_msg = await message.channel.send("❌ 無効なメッセージIDです。数字のみで構成されたIDを送信してください。")
                session["messages_to_delete"].append(error_msg)
                return
            
            message_id = int(message.content)
            session["message_id"] = message_id
            session["step"] = "waiting_channel_id"
            
            bot_msg = await message.channel.send(f"{message.author.mention} 送信するチャンネルIDを送信してください。")
            session["messages_to_delete"].append(bot_msg)
            return
        
        # チャンネルID待機中
        if session["step"] == "waiting_channel_id":
            # IDの検証
            if not message.content.isdigit():
                error_msg = await message.channel.send("❌ 無効なチャンネルIDです。数字のみで構成されたIDを送信してください。")
                session["messages_to_delete"].append(error_msg)
                return
            
            channel_id = int(message.content)
            
            # チャンネルの存在確認
            target_channel = self.bot.get_channel(channel_id)
            if not target_channel:
                error_msg = await message.channel.send("❌ 指定されたチャンネルが見つかりません。チャンネルIDを確認してください。")
                session["messages_to_delete"].append(error_msg)
                return
            
            # セッションの状態を更新して、これ以上メッセージを処理しないようにする
            session["step"] = "confirming"
            
            # Web Hookの情報を取得
            webhook_info = await self.get_webhook_info()
            webhook_name = webhook_info["name"]
            
            # アバターURLの構築
            if webhook_info["avatar"]:
                webhook_id = self.webhook_url.split('/')[-2]
                webhook_avatar_url = f"https://cdn.discordapp.com/avatars/{webhook_id}/{webhook_info['avatar']}.png"
            else:
                webhook_avatar_url = "なし"
            
            # 確認メッセージ
            confirm_message = (
                f"{message.author.mention}\n"
                f"**以下の内容で送信します。送信しますか？**\n\n"
                f"📝 **名前:** `{webhook_name}`\n"
                f"🖼️ **アバター:** {webhook_avatar_url}\n"
                f"📢 **送信先チャンネル:** {target_channel.mention}\n"
            )
            
            view = WebhookSendView(
                user_id=user_id,
                message_id=session["message_id"],
                channel_id=channel_id,
                webhook_url=self.webhook_url,
                webhook_info=webhook_info,
                messages_to_delete=session["messages_to_delete"]
            )
            
            await message.channel.send(confirm_message, view=view)


async def setup(bot: commands.Bot):
    """Cogのセットアップ"""
    await bot.add_cog(WebhookSenderCog(bot))