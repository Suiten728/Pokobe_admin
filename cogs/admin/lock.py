import discord
from discord.ext import commands
import sqlite3
import asyncio

DB_PATH = "data/pin.db"

class LockMessage(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._init_db()
        self.last_sent_message_id = {}  # チャンネルごとの最後に送信したメッセージIDを記録

    def _init_db(self):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS locked_messages (
            guild_id INTEGER,
            channel_id INTEGER,
            message_id INTEGER,
            PRIMARY KEY (guild_id, channel_id, message_id)
        )""")
        conn.commit()
        conn.close()

    @commands.command(name="lock")
    @commands.has_permissions(administrator=True)
    async def lock(self, ctx, message_id: int):
        """指定したメッセージを「最下部固定」対象にする"""
        try:
            target_msg = await ctx.channel.fetch_message(message_id)
        except discord.NotFound:
            await ctx.send("❌ メッセージが見つかりません。", ephemeral=True)
            return

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO locked_messages (guild_id, channel_id, message_id) VALUES (?, ?, ?)",
                  (ctx.guild.id, ctx.channel.id, target_msg.id))
        conn.commit()
        conn.close()

        await ctx.send(f"✅ メッセージ `{message_id}` を {ctx.channel.mention} で固定対象にしました。", ephemeral=True)

    @commands.command(name="unlock")
    @commands.has_permissions(administrator=True)
    async def unlock(self, ctx, message_id: int):
        """固定対象から解除"""
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("DELETE FROM locked_messages WHERE guild_id = ? AND channel_id = ? AND message_id = ?",
                  (ctx.guild.id, ctx.channel.id, message_id))
        conn.commit()
        conn.close()

        await ctx.send(f"✅ メッセージ `{message_id}` の固定を解除しました。", ephemeral=True)

    @commands.command(name="listlocks")
    async def listlocks(self, ctx):
        """現在の固定対象を表示"""
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT message_id FROM locked_messages WHERE guild_id = ? AND channel_id = ?",
                  (ctx.guild.id, ctx.channel.id))
        rows = c.fetchall()
        conn.close()

        if not rows:
            await ctx.send("📌 このチャンネルには固定対象はありません。", ephemeral=True)
            return

        ids = [str(r[0]) for r in rows]
        await ctx.send("📌 現在の固定対象メッセージID:\n" + "\n".join(ids), ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # DMは無視
        if not message.guild:
            return

        channel_key = (message.guild.id, message.channel.id)

        # Botが送信した場合は2秒待つ
        if message.author.bot:
            await asyncio.sleep(2)
            # 待機後、このメッセージが自分が送信した固定メッセージかチェック
            if channel_key in self.last_sent_message_id:
                if message.id == self.last_sent_message_id[channel_key]:
                    # 自分が送信した固定メッセージなので何もしない
                    return

        # このギルド・チャンネルで固定対象があるかを取得
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            "SELECT message_id FROM locked_messages WHERE guild_id = ? AND channel_id = ?",
            (message.guild.id, message.channel.id),
        )
        rows = c.fetchall()
        conn.close()

        if not rows:
            return

        for (msg_id,) in rows:
            try:
                # 直前の「固定コピー」を取得
                old_msg = await message.channel.fetch_message(msg_id)

                # ---- ここがポイント：常に"埋め込みとして"再送する ----
                # 元が埋め込みなら1つ目をそのまま使う／なければ本文をdescriptionへ
                if old_msg.embeds:
                    embed = old_msg.embeds[0]
                else:
                    embed = discord.Embed(
                        description=old_msg.content or "\u200b",  # 空を避ける
                        color=discord.Color.blue()
                    )

                # 新しい埋め込みメッセージを最下部に送信（content/添付は送らない）
                new_msg = await message.channel.send(embed=embed)

                # このメッセージIDを記録（次回のチェック用）
                self.last_sent_message_id[channel_key] = new_msg.id

                # 送信直後に即座にDBを更新
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute(
                    "UPDATE locked_messages SET message_id = ? WHERE guild_id = ? AND channel_id = ? AND message_id = ?",
                    (new_msg.id, message.guild.id, message.channel.id, msg_id),
                )
                conn.commit()
                conn.close()

                # 直前の固定コピーだけ削除（他の通常メッセージは削除しない）
                try:
                    await old_msg.delete()
                except discord.HTTPException:
                    pass

            except discord.NotFound:
                # 直前の固定コピーが見つからない場合はDBから掃除
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute(
                    "DELETE FROM locked_messages WHERE guild_id = ? AND channel_id = ? AND message_id = ?",
                    (message.guild.id, message.channel.id, msg_id),
                )
                conn.commit()
                conn.close()


async def setup(bot):
    await bot.add_cog(LockMessage(bot))