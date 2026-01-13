import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

# .envファイルを読み込む
load_dotenv('ci/')

class RealtimeRedirect(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # .envから設定を読み込む
        self.staff_role_id = int(os.getenv('STAFF_ROLE_ID'))
        self.realtime_channel_id = int(os.getenv('REALTIME_CHANNEL_ID'))
    
    @commands.Cog.listener()
    async def on_message(self, message):
        # Botのメッセージは無視
        if message.author.bot:
            return
        
        # メッセージが「同接誘導」のみかチェック
        if message.content == '同接誘導':
            # スタッフロールを持っているかチェック
            staff_role = discord.utils.get(message.guild.roles, id=self.staff_role_id)
            
            if staff_role in message.author.roles:
                # メッセージを削除
                try:
                    await message.delete()
                except discord.Forbidden:
                    print("メッセージを削除する権限がありません")
                    return
                except discord.NotFound:
                    print("メッセージが見つかりません")
                    return
                
                # Embedを作成
                embed = discord.Embed(
                    description=f"リアルタイムの配信に関する話題は <#{self.realtime_channel_id}> にてお願いします",
                    color=discord.Color.blue()
                )
                
                # Embedを送信
                await message.channel.send(embed=embed)
            # スタッフでない場合は無反応(何もしない)

async def setup(bot):
    await bot.add_cog(RealtimeRedirect(bot))