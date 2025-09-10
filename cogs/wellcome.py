import discord
from discord.ext import commands

# ウェルカムメッセージを送るチャンネルID
WELCOME_CHANNEL_ID = 1363499582578757752  

class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """メンバー参加時に呼ばれる"""
        channel = self.bot.get_channel(WELCOME_CHANNEL_ID)
        if channel is None:
            print("❌ ウェルカムチャンネルが見つかりません")
            return

        # 埋め込みメッセージ
        embed = discord.Embed(
            title="🎉 サーバーへようこそ！",
            description=f"{member.mention} さん、こんにちは！"
                        f"かざま隊の集いの場へようこそ！ここではかざま隊と話せる場所を"
                        f"⚠セキュリティ上、このサーバーに入ってから10分しなければメッセージは送信できません。お待ち下さい。cd d\\",
            color=discord.Color.green()
        )
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        embed.set_footer(text=f"現在のメンバー数: {member.guild.member_count}")

        # 画像を埋め込みに追加（任意のURL）
        embed.set_image(url="https://images.frwi.net/data/images/a7c85085-12ca-46e6-8683-10cbefa0470c.png")

        await channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Welcome(bot))
