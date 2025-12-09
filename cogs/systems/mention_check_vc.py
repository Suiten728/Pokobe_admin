# === role_mention_vc_check.py ===
import discord
from discord.ext import commands

class RoleMentionVCCheck(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # ▼書き換えてね
        self.target_channel_id = 1444550578326732901  # 反応するテキストチャンネルID
        self.target_role_id = 1444491233312509962    # メンションされたら反応するロールID

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Bot自身やDMは無視
        if message.author.bot or message.guild is None:
            return
        
        # 指定チャンネルのみ
        if message.channel.id != self.target_channel_id:
            return
        
        # 指定ロールがメンションされていない場合スルー
        role_ids = [role.id for role in message.role_mentions]
        if self.target_role_id not in role_ids:
            return
        
        # VCに接続しているか確認
        voice_state = message.author.voice
        if voice_state is None or voice_state.channel is None:
            return
        
        vc = voice_state.channel
        vc_id_str = f"<#{vc.id}>"
        await message.reply(f"現在 **{message.author.display_name}** さんは VC： **{vc_id_str}** に接続しています！")

        
async def setup(bot):
    await bot.add_cog(RoleMentionVCCheck(bot))
