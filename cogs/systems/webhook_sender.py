import discord
from discord.ext import commands
import aiohttp
import asyncio
import os
from dotenv import load_dotenv

# .envファイルを読み込む
load_dotenv()
SENDER_WEBHOOK_URL = os.getenv("SENDER_WEBHOOK_URL")
CM_ROLE_ID = os.getenv("CM_ROLE_ID")

# ユーザーごとのセッション管理
user_sessions = {}

class WebhookSendView(discord.ui.View):
    """送信確認用のView"""
    def __init__(self, user_id: int, message_id: int, channel_id: int, avatar_url: str, webhook_url: str, confirm_message, preview_content: str):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.message_id = message_id
        self.channel_id = channel_id
        self.avatar_url = avatar_url
        self.webhook_url = webhook_url
        self.confirm_message = confirm_message
        self.preview_content = preview_content
        self.logs = []
        self.reply_enabled = False
        self.reply_message_id = None
        self.value = None
    
    def add_log(self, log_message: str):
        """ログを追加"""
        self.logs.append(log_message)
    
    async def update_message(self):
        """確認メッセージを更新"""
        try:
            # ログを結合
            log_text = "\n".join(self.logs) if self.logs else "待機中..."
            
            # チャンネルメンション
            channel_mention = f"<#{self.channel_id}>"
            
            # アバター表示
            avatar_display = self.avatar_url if self.avatar_url else "デフォルト"
            
            # リプライ状態
            reply_status = f"🔗 返信先: `{self.reply_message_id}`" if self.reply_enabled else "返信なし"
            
            updated_message = (
                f"<@{self.user_id}>\n"
                f"**以下の内容で送信します。送信しますか？**\n\n"
                f"📢 **送信先チャンネル:** {channel_mention}\n"
                f"🖼️ **アバター:** {avatar_display}\n"
                f"💬 **返信:** {reply_status}\n\n"
                f"**送信されるメッセージ:**\n"
                f"{self.preview_content}\n\n"
                f"```\n{log_text}\n```"
            )
            
            await self.confirm_message.edit(content=updated_message, view=self)
        except Exception as e:
            print(f"メッセージ更新エラー: {e}")
    
    @discord.ui.button(label="返信機能を有効にする", style=discord.ButtonStyle.gray, row=0)
    async def toggle_reply_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("このボタンはあなたが使用できません。", ephemeral=True)
            return
        
        if self.reply_enabled:
            # 返信機能を無効化
            self.reply_enabled = False
            self.reply_message_id = None
            button.label = "返信機能を有効にする"
            button.style = discord.ButtonStyle.gray
            await interaction.response.defer()
            await self.update_message()
        else:
            # 返信先メッセージIDの入力を要求
            await interaction.response.send_message(
                f"{interaction.user.mention} 返信先のメッセージIDを送信してください。",
                ephemeral=True
            )
            
            # セッションに返信待機状態を保存
            if self.user_id in user_sessions:
                user_sessions[self.user_id]["waiting_reply"] = True
                user_sessions[self.user_id]["view_instance"] = self

    @discord.ui.button(label="はい", style=discord.ButtonStyle.green, row=1)
    async def yes_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("このボタンはあなたが使用できません。", ephemeral=True)
            return

        await interaction.response.defer()
        
        # ボタンを無効化
        for item in self.children:
            item.disabled = True
        await self.confirm_message.edit(view=self)
        
        # メッセージを取得して送信
        try:
            # ログ: 検索開始
            self.add_log(f"[DEBUG] メッセージID {self.message_id} を検索中...")
            await self.update_message()
            
            message = None
            searched_channels = 0
            searched_threads = 0
            
            # 通常のチャンネルとスレッドを検索
            for guild in interaction.client.guilds:
                # TextChannel
                for channel in guild.text_channels:
                    searched_channels += 1
                    try:
                        message = await channel.fetch_message(self.message_id)
                        self.add_log(f"[DEBUG] メッセージを発見: チャンネル {channel.name} (ID: {channel.id})")
                        await self.update_message()
                        break
                    except:
                        continue
                
                if message:
                    break
                
                # Thread
                for thread in guild.threads:
                    searched_threads += 1
                    try:
                        message = await thread.fetch_message(self.message_id)
                        self.add_log(f"[DEBUG] メッセージを発見: スレッド {thread.name} (ID: {thread.id})")
                        await self.update_message()
                        break
                    except:
                        continue
                
                if message:
                    break
                
                # Forum
                for channel in guild.forums:
                    try:
                        for thread in channel.threads:
                            searched_threads += 1
                            try:
                                message = await thread.fetch_message(self.message_id)
                                self.add_log(f"[DEBUG] メッセージを発見: フォーラムスレッド {thread.name} (ID: {thread.id})")
                                await self.update_message()
                                break
                            except:
                                continue
                    except:
                        continue
                    
                    if message:
                        break
                
                if message:
                    break
            
            # ログ: 検索結果
            self.add_log(f"[DEBUG] {searched_channels} 個のチャンネル、{searched_threads} 個のスレッドを検索しました")
            await self.update_message()
            
            if not message:
                self.add_log(f"[ERROR] メッセージID {self.message_id} が見つかりませんでした")
                await self.update_message()
                self.stop()
                return
            
            # リプライ機能が有効な場合、返信先メッセージを取得
            reply_message = None
            if self.reply_enabled and self.reply_message_id:
                self.add_log(f"[DEBUG] 返信先メッセージID {self.reply_message_id} を検索中...")
                await self.update_message()
                
                for guild in interaction.client.guilds:
                    # TextChannel
                    for channel in guild.text_channels:
                        try:
                            reply_message = await channel.fetch_message(self.reply_message_id)
                            self.add_log(f"[DEBUG] 返信先メッセージを発見")
                            await self.update_message()
                            break
                        except:
                            continue
                    
                    if reply_message:
                        break
                    
                    # Thread
                    for thread in guild.threads:
                        try:
                            reply_message = await thread.fetch_message(self.reply_message_id)
                            self.add_log(f"[DEBUG] 返信先メッセージを発見")
                            await self.update_message()
                            break
                        except:
                            continue
                    
                    if reply_message:
                        break
                    
                    # Forum
                    for channel in guild.forums:
                        try:
                            for thread in channel.threads:
                                try:
                                    reply_message = await thread.fetch_message(self.reply_message_id)
                                    self.add_log(f"[DEBUG] 返信先メッセージを発見")
                                    await self.update_message()
                                    break
                                except:
                                    continue
                        except:
                            continue
                        
                        if reply_message:
                            break
                    
                    if reply_message:
                        break
                
                if not reply_message:
                    self.add_log(f"[WARN] 返信先メッセージが見つかりませんでした。返信なしで送信します")
                    await self.update_message()
            
            # Web Hookで送信
            self.add_log("[DEBUG] Web Hookで送信中...")
            await self.update_message()
            
            async with aiohttp.ClientSession() as session:
                # Web Hookを取得
                webhook = discord.Webhook.from_url(self.webhook_url, session=session)
                
                # 送信先チャンネルを変更
                try:
                    webhook_id = self.webhook_url.split('/')[-2]
                    webhook_token = self.webhook_url.split('/')[-1]
                    
                    async with session.patch(
                        f"https://discord.com/api/v10/webhooks/{webhook_id}/{webhook_token}",
                        json={"channel_id": str(self.channel_id)}
                    ) as resp:
                        if resp.status == 200:
                            self.add_log(f"[DEBUG] 送信先チャンネルを変更しました")
                            await self.update_message()
                        else:
                            self.add_log(f"[WARN] チャンネル変更に失敗しました (status: {resp.status})")
                            await self.update_message()
                except Exception as e:
                    self.add_log(f"[WARN] チャンネル変更エラー: {str(e)}")
                    await self.update_message()
                
                # 送信用の引数を準備
                send_kwargs = {}
                
                # アバターURLを設定
                if self.avatar_url:
                    send_kwargs["avatar_url"] = self.avatar_url
                
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
                
                # メッセージ送信
                await webhook.send(**send_kwargs, wait=False)
            
            # ログ: 送信完了
            self.add_log("[DEBUG] 送信が完了しました！")
            await self.update_message()
            
        except Exception as e:
            self.add_log(f"[ERROR] エラーが発生しました: {str(e)}")
            await self.update_message()
        
        # セッションをクリア
        if self.user_id in user_sessions:
            del user_sessions[self.user_id]
        
        self.stop()

    @discord.ui.button(label="いいえ", style=discord.ButtonStyle.red, row=1)
    async def no_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("このボタンはあなたが使用できません。", ephemeral=True)
            return

        await interaction.response.defer()
        
        # ボタンを無効化
        for item in self.children:
            item.disabled = True
        
        # ログ: キャンセル
        self.add_log("[INFO] 送信がキャンセルされました")
        await self.update_message()
        
        # セッションをクリア
        if self.user_id in user_sessions:
            del user_sessions[self.user_id]
        
        self.stop()


class WebhookSenderCog(commands.Cog):
    """Web Hook送信機能のCog"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.webhook_url = SENDER_WEBHOOK_URL
        self.cm_role_id = int(CM_ROLE_ID) if CM_ROLE_ID and CM_ROLE_ID.isdigit() else None
        
        if not self.webhook_url:
            print("⚠️ 警告: SENDER_WEBHOOK_URLが.envファイルに設定されていません。")
        
        if not self.cm_role_id:
            print("⚠️ 警告: CM_ROLE_IDが.envファイルに設定されていません。権限チェックは無効です。")

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
            # 権限チェック
            if self.cm_role_id:
                if not any(role.id == self.cm_role_id for role in message.author.roles):
                    try:
                        await message.delete()
                    except:
                        pass
                    return
            
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
            user_sessions[user_id]["bot_message"] = bot_msg
            return
        
        # セッションが存在しない場合は処理しない
        if user_id not in user_sessions:
            return
        
        session = user_sessions[user_id]
        
        # 返信先メッセージID待機中
        if session.get("waiting_reply"):
            # IDの検証
            if not message.content.isdigit():
                try:
                    await message.delete()
                except:
                    pass
                return
            
            # ユーザーのメッセージを削除
            try:
                await message.delete()
            except:
                pass
            
            reply_message_id = int(message.content)
            
            # Viewインスタンスを取得して更新
            view_instance = session.get("view_instance")
            if view_instance:
                view_instance.reply_enabled = True
                view_instance.reply_message_id = reply_message_id
                
                # ボタンのラベルを更新
                for item in view_instance.children:
                    if isinstance(item, discord.ui.Button) and "返信機能" in item.label:
                        item.label = "返信機能を無効にする"
                        item.style = discord.ButtonStyle.green
                
                await view_instance.update_message()
            
            # 返信待機状態を解除
            session["waiting_reply"] = False
            return
        
        # メッセージID待機中
        if session["step"] == "waiting_message_id":
            # IDの検証
            if not message.content.isdigit():
                try:
                    await message.delete()
                except:
                    pass
                
                if "bot_message" in session:
                    try:
                        await session["bot_message"].delete()
                    except:
                        pass
                
                error_msg = await message.channel.send("❌ 無効なメッセージIDです。数字のみで構成されたIDを送信してください。")
                session["bot_message"] = error_msg
                return
            
            try:
                await message.delete()
            except:
                pass
            
            if "bot_message" in session:
                try:
                    await session["bot_message"].delete()
                except:
                    pass
            
            message_id = int(message.content)
            session["message_id"] = message_id
            session["step"] = "waiting_channel_id"
            
            bot_msg = await message.channel.send(f"{message.author.mention} 送信先のチャンネルIDを送信してください。")
            session["bot_message"] = bot_msg
            return
        
        # チャンネルID待機中
        if session["step"] == "waiting_channel_id":
            # IDの検証
            if not message.content.isdigit():
                try:
                    await message.delete()
                except:
                    pass
                
                if "bot_message" in session:
                    try:
                        await session["bot_message"].delete()
                    except:
                        pass
                
                error_msg = await message.channel.send("❌ 無効なチャンネルIDです。数字のみで構成されたIDを送信してください。")
                session["bot_message"] = error_msg
                return
            
            try:
                await message.delete()
            except:
                pass
            
            if "bot_message" in session:
                try:
                    await session["bot_message"].delete()
                except:
                    pass
            
            channel_id = int(message.content)
            session["channel_id"] = channel_id
            session["step"] = "waiting_avatar_url"
            
            bot_msg = await message.channel.send(
                f"{message.author.mention} アバター画像を添付するか、URLを送信してください。\n"
                f"（デフォルトアバターを使用する場合は「スキップ」と送信）"
            )
            session["bot_message"] = bot_msg
            return
        
        # アバターURL待機中
        if session["step"] == "waiting_avatar_url":
            try:
                await message.delete()
            except:
                pass
            
            if "bot_message" in session:
                try:
                    await session["bot_message"].delete()
                except:
                    pass
            
            avatar_url = None
            
            # 添付ファイルがある場合（画像添付）
            if message.attachments:
                # 最初の添付ファイルを使用
                attachment = message.attachments[0]
                # 画像ファイルかチェック
                if attachment.content_type and attachment.content_type.startswith('image/'):
                    avatar_url = attachment.url
                else:
                    error_msg = await message.channel.send("❌ 画像ファイルを添付してください。")
                    session["bot_message"] = error_msg
                    return
            elif message.content.lower() != "スキップ":
                # URLの簡易検証
                if message.content.startswith("http://") or message.content.startswith("https://"):
                    avatar_url = message.content
                else:
                    error_msg = await message.channel.send("❌ 無効なURLです。http:// または https:// で始まるURLを送信するか、画像を添付してください。")
                    session["bot_message"] = error_msg
                    return
            
            session["avatar_url"] = avatar_url
            session["step"] = "confirming"
            
            # 処理中メッセージを送信
            processing_msg = await message.channel.send("処理中...")
            
            try:
                # メッセージのプレビューを取得
                preview_message = await self.fetch_message_by_id(session["message_id"])
                
                # プレビューテキストを作成
                if preview_message:
                    preview_content = await self.create_preview_text(preview_message)
                else:
                    preview_content = "> (プレビュー取得失敗)"
                
                # 処理完了メッセージを表示（0.5秒）
                await processing_msg.edit(content="✅処理完了！")
                await asyncio.sleep(0.5)
                
                # sessionからchannel_idとavatar_urlを取得
                channel_id = session["channel_id"]
                avatar_url = session["avatar_url"]
                
                # チャンネルメンション
                channel_mention = f"<#{channel_id}>"
                
                # アバター表示
                avatar_display = avatar_url if avatar_url else "デフォルト"
                
                # 確認メッセージ
                confirm_message_text = (
                    f"{message.author.mention}\n"
                    f"**以下の内容で送信します。送信しますか？**\n\n"
                    f"📢 **送信先チャンネル:** {channel_mention}\n"
                    f"🖼️ **アバター:** {avatar_display}\n"
                    f"💬 **返信:** 返信なし\n\n"
                    f"**送信されるメッセージ:**\n"
                    f"{preview_content}\n\n"
                    f"```\n待機中...\n```"
                )
                
                # 処理中メッセージを確認画面に変更
                await processing_msg.edit(content=confirm_message_text)
                
                view = WebhookSendView(
                    user_id=user_id,
                    message_id=session["message_id"],
                    channel_id=channel_id,
                    avatar_url=avatar_url,
                    webhook_url=self.webhook_url,
                    confirm_message=processing_msg,
                    preview_content=preview_content
                )
                
                # Viewを確認メッセージに追加
                await processing_msg.edit(view=view)
                
            except Exception as e:
                await processing_msg.edit(content=f"❌ エラーが発生しました: {str(e)}")
                print(f"確認メッセージ送信エラー: {e}")
                if user_id in user_sessions:
                    del user_sessions[user_id]
                return
    
    async def fetch_message_by_id(self, message_id: int):
        """メッセージIDからメッセージを取得"""
        for guild in self.bot.guilds:
            # TextChannel
            for channel in guild.text_channels:
                try:
                    return await channel.fetch_message(message_id)
                except:
                    continue
            
            # Thread
            for thread in guild.threads:
                try:
                    return await thread.fetch_message(message_id)
                except:
                    continue
            
            # Forum
            for channel in guild.forums:
                try:
                    for thread in channel.threads:
                        try:
                            return await thread.fetch_message(message_id)
                        except:
                            continue
                except:
                    continue
        
        return None
    
    async def create_preview_text(self, message):
        """メッセージのプレビューテキストを作成"""
        if not message:
            return "> (プレビュー取得失敗)"
        
        preview_parts = []
        
        # メッセージ本文
        if message.content:
            content = message.content
            if len(content) > 500:
                content = content[:500] + "..."
            preview_parts.append(f"> {content.replace(chr(10), chr(10) + '> ')}")
        
        # Embedの詳細情報
        if message.embeds:
            for i, embed in enumerate(message.embeds, 1):
                embed_info = [f"\n📋 **Embed {i}:**"]
                
                if embed.title:
                    embed_info.append(f"  title = {embed.title}")
                
                if embed.description:
                    desc = embed.description
                    if len(desc) > 200:
                        desc = desc[:200] + "..."
                    embed_info.append(f"  description = {desc}")
                
                if embed.color:
                    embed_info.append(f"  color = #{embed.color.value:06x}")
                
                if embed.footer:
                    embed_info.append(f"  footer = {embed.footer.text}")
                
                if embed.image:
                    embed_info.append(f"  image = {embed.image.url}")
                
                if embed.thumbnail:
                    embed_info.append(f"  thumbnail = {embed.thumbnail.url}")
                
                if embed.fields:
                    embed_info.append(f"  fields = {len(embed.fields)}個")
                
                preview_parts.append("\n".join(embed_info))
        
        # 添付ファイル
        if message.attachments:
            preview_parts.append(f"\n📎 添付ファイル: {len(message.attachments)}個")
        
        # コンテンツがない場合
        if not preview_parts:
            preview_parts.append("> (コンテンツなし)")
        
        return "\n".join(preview_parts)


async def setup(bot: commands.Bot):
    """Cogのセットアップ"""
    await bot.add_cog(WebhookSenderCog(bot))