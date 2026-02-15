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
    def __init__(self, user_id: int, message_id: int, webhook_url: str, webhook_info: dict, confirm_message):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.message_id = message_id
        self.webhook_url = webhook_url
        self.webhook_info = webhook_info
        self.confirm_message = confirm_message
        self.value = None

    @discord.ui.button(label="はい", style=discord.ButtonStyle.green)
    async def yes_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("このボタンはあなたが使用できません。", ephemeral=True)
            return

        await interaction.response.defer()
        
        # メッセージを取得
        try:
            # メッセージIDからメッセージを取得
            print(f"[DEBUG] メッセージID {self.message_id} を検索中...")
            message = None
            searched_channels = 0
            
            for channel in interaction.client.get_all_channels():
                if isinstance(channel, discord.TextChannel):
                    searched_channels += 1
                    try:
                        message = await channel.fetch_message(self.message_id)
                        print(f"[DEBUG] メッセージを発見: チャンネル {channel.name} (ID: {channel.id})")
                        break
                    except discord.NotFound:
                        continue
                    except discord.Forbidden:
                        print(f"[DEBUG] アクセス拒否: チャンネル {channel.name} (ID: {channel.id})")
                        continue
            
            print(f"[DEBUG] {searched_channels} 個のチャンネルを検索しました")
            
            if not message:
                print(f"[DEBUG] メッセージID {self.message_id} が見つかりませんでした")
                await interaction.followup.send(
                    "❌ 指定されたメッセージが見つかりませんでした。\n\n"
                    "**確認事項:**\n"
                    "• メッセージIDが正しいか確認してください\n"
                    "• Botがそのチャンネルにアクセスできるか確認してください\n"
                    "• メッセージが削除されていないか確認してください",
                    ephemeral=True
                )
                # 確認メッセージを削除
                try:
                    await self.confirm_message.delete()
                except:
                    pass
                self.stop()
                return
            
            # Web Hookで送信（チャンネル変更なし）
            async with aiohttp.ClientSession() as session:
                webhook = discord.Webhook.from_url(self.webhook_url, session=session)
                
                # 送信用の引数を準備
                send_kwargs = {}
                
                # コンテンツの処理
                if message.content:
                    send_kwargs["content"] = message.content
                
                # 添付ファイルの処理
                if message.attachments:
                    files = []
                    for attachment in message.attachments:
                        file_data = await attachment.read()
                        files.append(discord.File(fp=discord.utils.BytesIO(file_data), filename=attachment.filename))
                    send_kwargs["files"] = files
                
                # Embedの処理
                if message.embeds:
                    send_kwargs["embeds"] = message.embeds
                
                # メッセージ送信（usernameとavatar_urlは指定しない）
                await webhook.send(**send_kwargs)
            
            await interaction.followup.send("✅ メッセージを送信しました!", ephemeral=True)
            
            # 確認メッセージを削除
            try:
                await self.confirm_message.delete()
            except:
                pass
            
        except discord.NotFound:
            await interaction.followup.send("❌ 指定されたメッセージが見つかりませんでした。", ephemeral=True)
            try:
                await self.confirm_message.delete()
            except:
                pass
        except discord.Forbidden:
            await interaction.followup.send("❌ メッセージの取得またはWeb Hookの送信に失敗しました。権限を確認してください。", ephemeral=True)
            try:
                await self.confirm_message.delete()
            except:
                pass
        except Exception as e:
            await interaction.followup.send(f"❌ エラーが発生しました: {str(e)}", ephemeral=True)
            try:
                await self.confirm_message.delete()
            except:
                pass
        
        # セッションをクリア
        if self.user_id in user_sessions:
            del user_sessions[self.user_id]
        
        self.stop()

    @discord.ui.button(label="いいえ", style=discord.ButtonStyle.red)
    async def no_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("このボタンはあなたが使用できません。", ephemeral=True)
            return

        await interaction.response.send_message("❌ 送信をキャンセルしました。", ephemeral=True)
        
        # 確認メッセージを削除
        try:
            await self.confirm_message.delete()
        except:
            pass
        
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
            async with aiohttp.ClientSession() as session:
                webhook = discord.Webhook.from_url(self.webhook_url, session=session)
                webhook_data = await webhook.fetch()
                
                return {
                    "name": webhook_data.name or "Unknown",
                    "avatar_url": webhook_data.display_avatar.url if webhook_data.avatar else None,
                    "channel_id": webhook_data.channel_id
                }
        except Exception as e:
            print(f"Web Hook情報の取得に失敗: {e}")
        
        return {"name": "Unknown", "avatar_url": None, "channel_id": None}

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
            
            # ユーザーのメッセージをすぐに削除
            try:
                await message.delete()
            except:
                pass
            
            user_sessions[user_id] = {
                "step": "waiting_message_id",
                "channel_id": message.channel.id
            }
            
            bot_msg = await message.channel.send(f"{message.author.mention} 送信するメッセージIDを送信してください。")
            # Botメッセージの参照を保存
            user_sessions[user_id]["bot_message"] = bot_msg
            return
        
        # セッションが存在しない場合は処理しない
        if user_id not in user_sessions:
            return
        
        session = user_sessions[user_id]
        
        # メッセージID待機中
        if session["step"] == "waiting_message_id":
            # IDの検証
            if not message.content.isdigit():
                # ユーザーのメッセージを削除
                try:
                    await message.delete()
                except:
                    pass
                
                # 前のBotメッセージも削除
                if "bot_message" in session:
                    try:
                        await session["bot_message"].delete()
                    except:
                        pass
                
                # エラーメッセージを送信
                error_msg = await message.channel.send("❌ 無効なメッセージIDです。数字のみで構成されたIDを送信してください。")
                
                # 新しいBotメッセージを保存
                session["bot_message"] = error_msg
                return
            
            # ユーザーのメッセージを削除
            try:
                await message.delete()
            except:
                pass
            
            # 前のBotメッセージも削除
            if "bot_message" in session:
                try:
                    await session["bot_message"].delete()
                except:
                    pass
            
            message_id = int(message.content)
            session["message_id"] = message_id
            session["step"] = "confirming"
            
            try:
                # Web Hookの情報を取得
                webhook_info = await self.get_webhook_info()
                webhook_name = webhook_info["name"]
                webhook_avatar_url = webhook_info["avatar_url"] or "なし"
                
                # Web Hookの送信先チャンネルを取得
                webhook_channel_id = webhook_info.get("channel_id")
                if webhook_channel_id:
                    webhook_channel = self.bot.get_channel(webhook_channel_id)
                    webhook_channel_mention = webhook_channel.mention if webhook_channel else f"<#{webhook_channel_id}>"
                else:
                    webhook_channel_mention = "不明"
                
                # 確認メッセージ
                confirm_message_text = (
                    f"{message.author.mention}\n"
                    f"**以下の内容で送信します。送信しますか？**\n\n"
                    f"📝 **名前:** `{webhook_name}`\n"
                    f"🖼️ **アバター:** {webhook_avatar_url}\n"
                    f"📢 **送信先チャンネル:** {webhook_channel_mention}\n"
                )
                
                confirm_msg = await message.channel.send(confirm_message_text)
                
                view = WebhookSendView(
                    user_id=user_id,
                    message_id=session["message_id"],
                    webhook_url=self.webhook_url,
                    webhook_info=webhook_info,
                    confirm_message=confirm_msg
                )
                
                # Viewを確認メッセージに追加
                await confirm_msg.edit(view=view)
                
            except Exception as e:
                # エラーが発生した場合
                error_msg = await message.channel.send(f"❌ エラーが発生しました: {str(e)}\n\nWeb Hook URLが正しく設定されているか確認してください。")
                print(f"確認メッセージ送信エラー: {e}")
                # セッションをクリア
                if user_id in user_sessions:
                    del user_sessions[user_id]
                return


async def setup(bot: commands.Bot):
    """Cogのセットアップ"""
    await bot.add_cog(WebhookSenderCog(bot))
