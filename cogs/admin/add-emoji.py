# cogs/admin/add_emoji.py

import discord
from discord.ext import commands

class AddEmoji(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="addemoji")
    @commands.has_permissions(manage_emojis=True)
    async def add_emoji(self, ctx, emoji_name: str):
        # 添付ファイル確認
        if not ctx.message.attachments:
            await ctx.send("❌ 画像を添付してください。")
            return

        attachment = ctx.message.attachments[0]

        # 画像形式チェック（ゆるめ）
        if not attachment.filename.lower().endswith((".png", ".jpg", ".jpeg", ".gif")):
            await ctx.send("❌ PNG / JPG / GIF のみ対応しています。")
            return

        try:
            # 画像データ取得
            image_bytes = await attachment.read()

            # 絵文字作成
            emoji = await ctx.guild.create_custom_emoji(
                name=emoji_name,
                image=image_bytes,
                reason=f"Added by {ctx.author}"
            )

            await ctx.send(f"✅ 絵文字を追加しました！ {emoji}")

        except discord.Forbidden:
            await ctx.send("❌ Botに絵文字管理権限がありません。")

        except discord.HTTPException as e:
            await ctx.send("❌ 絵文字の追加に失敗しました。（サイズ超過の可能性あり）")

    @add_emoji.error
    async def add_emoji_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ このコマンドを使う権限がありません。")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("❌ 絵文字名を指定してください。\n例: `P!addemoji test_emoji`")

async def setup(bot):
    await bot.add_cog(AddEmoji(bot))
