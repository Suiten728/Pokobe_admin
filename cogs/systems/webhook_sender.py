import discord
from discord.ext import commands
import aiohttp
import asyncio
import os
from dotenv import load_dotenv

# .envファイルを読み込む
load_dotenv(dotenv_path="ci/.env")
SENDER_WEBHOOK_URL = os.getenv("SENDER_WEBHOOK_URL")
CM_ROLE_ID = os.getenv("CM_ROLE_ID")

# ユーザーごとのセッション管理
user_sessions = {}

class WebhookSendView(discord.ui.View):
    """送信確認用のView"""
    def __init__(self, user_id: int, message_id: int, webhook_url: str, webhook_info: dict, confirm_message, preview_content: str):
        super().__init__(timeout=300)  # 5分
        self.user_id = user_id
        self.message_id = message_id
        self.webhook_url = webhook_url
        self.webhook_info = webhook_info
        self.confirm_message = confirm_message
        self.preview_content = preview_content
        self.logs = []
        self.value = None
    
    def add_log(self, log_message: str):
        """ログを追加"""
        self.logs.append(log_message)
    
    async def update_message(self):
        """確認メッセージを更新"""
        try:
            webhook_name = self.webhook_info["name"]
            webhook_avatar_url = self.webhook_info["avatar_url"] or "なし"
            webhook_channel_id = self.webhook_info.get("channel_id")
            
            if webhook_channel_id:
                webhook_channel_mention = f"<#{webhook_channel_id}>"
            else:
                webhook_channel_mention = "不明"
            
            # ログを結合
            log_text = "\n".join(self.logs) if self.logs else "待機中..."
            
            updated_message = (
                f"<@{self.user_id}>\n"
                f"**以下の内容で送信します。送信しますか？**\n\n"
                f"📝 **名前:** `{webhook_name}`\n"
                f"🖼️ **アバター:** {webhook_avatar_url}\n"
                f"📢 **送信先チャンネル:** {webhook_channel_mention}\n\n"
                f"**送信されるメッセージ:**\n"
                f"{self.preview_content}\n\n"
                f"```\n{log_text}\n```"
            )
            
            await self.confirm_message.edit(content=updated_message, view=self)
        except Exception as e:
            print(f"メッセージ更新エラー: {e}")

    @discord.ui.button(label="はい", style=discord.ButtonStyle.green)
    async def yes_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("このボタンはあなたが使用できません。", ephemeral=True)
            return

        await interaction.response.defer()
        
        # ボタンを無効化
        for item in self.children:
            item.disabled = True
        await self.confirm_message.edit(view=self)
        
        # メッセージを取得
        try:
            # ログ: 検索開始
            self.add_log(f"[DEBUG] メッセージID {self.message_id} を検索中...")
            await self.update_message()
            
            message = None
            searched_channels = 0
            searched_threads = 0
            
            # 通常のチャンネルとスレッドを検索
            for guild in interaction.client.guilds:
                # TextChannel（通常のテキストチャンネル）
                for channel in guild.text_channels:
                    searched_channels += 1
                    try:
                        message = await channel.fetch_message(self.message_id)
                        self.add_log(f"[DEBUG] メッセージを発見: チャンネル {channel.name} (ID: {channel.id})")
                        await self.update_message()
                        break
                    except discord.NotFound:
                        continue
                    except discord.Forbidden:
                        continue
                
                if message:
                    break
                
                # Thread（アクティブなスレッド）
                for thread in guild.threads:
                    searched_threads += 1
                    try:
                        message = await thread.fetch_message(self.message_id)
                        self.add_log(f"[DEBUG] メッセージを発見: スレッド {thread.name} (ID: {thread.id})")
                        await self.update_message()
                        break
                    except discord.NotFound:
                        continue
                    except discord.Forbidden:
                        continue
                
                if message:
                    break
                
                # ForumChannel（フォーラムチャンネル内のスレッド）
                for channel in guild.forums:
                    try:
                        active_threads = channel.threads
                        for thread in active_threads:
                            searched_threads += 1
                            try:
                                message = await thread.fetch_message(self.message_id)
                                self.add_log(f"[DEBUG] メッセージを発見: フォーラムスレッド {thread.name} (ID: {thread.id})")
                                await self.update_message()
                                break
                            except discord.NotFound:
                                continue
                            except discord.Forbidden:
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
            
            # Web Hookで送信
            self.add_log("[DEBUG] Web Hookで送信中...")
            await self.update_message()
            
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
                
                # メッセージ送信
                await webhook.send(**send_kwargs)
            
            # ログ: 送信完了
            self.add_log("[DEBUG] 送信が完了しました！")
            await self.update_message()
            
        except discord.NotFound:
            self.add_log("[ERROR] 指定されたメッセージが見つかりませんでした")
            await self.update_message()
        except discord.Forbidden:
            self.add_log("[ERROR] メッセージの取得またはWeb Hookの送信に失敗しました")
            await self.update_message()
        except Exception as e:
            self.add_log(f"[ERROR] エラーが発生しました: {str(e)}")
            await self.update_message()
        
        # セッションをクリア
        if self.user_id in user_sessions:
            del user_sessions[self.user_id]
        
        self.stop()

    @discord.ui.button(label="いいえ", style=discord.ButtonStyle.red)
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
            # 権限チェック
            if self.cm_role_id:
                # CM_ROLE_IDが設定されている場合のみチェック
                if not any(role.id == self.cm_role_id for role in message.author.roles):
                    # 権限がない場合
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
            
            # 処理中メッセージを送信
            processing_msg = await message.channel.send("処理中...")
            
            try:
                # メッセージのプレビューを取得
                preview_message = None
                for guild in self.bot.guilds:
                    # TextChannel
                    for channel in guild.text_channels:
                        try:
                            preview_message = await channel.fetch_message(message_id)
                            break
                        except:
                            continue
                    
                    if preview_message:
                        break
                    
                    # Thread
                    for thread in guild.threads:
                        try:
                            preview_message = await thread.fetch_message(message_id)
                            break
                        except:
                            continue
                    
                    if preview_message:
                        break
                    
                    # Forum
                    for channel in guild.forums:
                        try:
                            for thread in channel.threads:
                                try:
                                    preview_message = await thread.fetch_message(message_id)
                                    break
                                except:
                                    continue
                        except:
                            continue
                        
                        if preview_message:
                            break
                    
                    if preview_message:
                        break
                
                # プレビューテキストを作成
                if preview_message:
                    preview_content = preview_message.content if preview_message.content else "(コンテンツなし)"
                    if len(preview_content) > 500:
                        preview_content = preview_content[:500] + "..."
                    
                    # 添付ファイルがある場合
                    if preview_message.attachments:
                        preview_content += f"\n📎 添付ファイル: {len(preview_message.attachments)}個"
                    
                    # Embedがある場合
                    if preview_message.embeds:
                        preview_content += f"\n📋 Embed: {len(preview_message.embeds)}個"
                    
                    preview_content = f"> {preview_content.replace(chr(10), chr(10) + '> ')}"
                else:
                    preview_content = "> (プレビュー取得失敗)"
                
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
                
                # 処理完了メッセージを表示（0.5秒）
                await processing_msg.edit(content="✅処理完了！")
                await asyncio.sleep(0.5)
                
                # 確認メッセージ
                confirm_message_text = (
                    f"{message.author.mention}\n"
                    f"**以下の内容で送信します。送信しますか？**\n\n"
                    f"📝 **名前:** `{webhook_name}`\n"
                    f"🖼️ **アバター:** {webhook_avatar_url}\n"
                    f"📢 **送信先チャンネル:** {webhook_channel_mention}\n\n"
                    f"**送信されるメッセージ:**\n"
                    f"{preview_content}\n\n"
                    f"```\n待機中...\n```"
                )
                
                # 処理中メッセージを確認画面に変更
                await processing_msg.edit(content=confirm_message_text)
                
                view = WebhookSendView(
                    user_id=user_id,
                    message_id=session["message_id"],
                    webhook_url=self.webhook_url,
                    webhook_info=webhook_info,
                    confirm_message=processing_msg,
                    preview_content=preview_content
                )
                
                # Viewを確認メッセージに追加
                await processing_msg.edit(view=view)
                
            except Exception as e:
                # エラーが発生した場合
                await processing_msg.edit(content=f"❌ エラーが発生しました: {str(e)}\n\nWeb Hook URLが正しく設定されているか確認してください。")
                print(f"確認メッセージ送信エラー: {e}")
                # セッションをクリア
                if user_id in user_sessions:
                    del user_sessions[user_id]
                return


async def setup(bot: commands.Bot):
    """Cogのセットアップ"""
    await bot.add_cog(WebhookSenderCog(bot))