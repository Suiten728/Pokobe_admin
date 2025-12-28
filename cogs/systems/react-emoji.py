import discord
from discord.ext import commands
import json
import os
import asyncio

DATA_PATH = "data/emoji_react.json"
REACTION_DELAY = 0.7  # レート制限対策


class Emoji(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data = self.load_data()

    # ===== JSON =====
    def load_data(self):
        if not os.path.exists(DATA_PATH):
            return {}
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_data(self):
        with open(DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    # ===== Events =====
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        cid = str(message.channel.id)
        config = self.data.get(cid)

        if not config or not config.get("enabled"):
            return

        for emoji in config.get("emojis", []):
            try:
                await message.add_reaction(emoji)
                await asyncio.sleep(REACTION_DELAY)
            except discord.HTTPException as e:
                print(f"❌ reaction error [{emoji}]:", e)

    # ===== Commands =====
    @commands.command(name="react_on")
    @commands.has_permissions(manage_channels=True)
    async def react_on(self, ctx):
        cid = str(ctx.channel.id)
        self.data.setdefault(cid, {"enabled": True, "emojis": []})
        self.data[cid]["enabled"] = True
        self.save_data()
        await ctx.send("✅ このチャンネルで自動リアクションを有効にしたよ！")

    @commands.command(name="react_off")
    @commands.has_permissions(manage_channels=True)
    async def react_off(self, ctx):
        cid = str(ctx.channel.id)
        if cid in self.data:
            self.data[cid]["enabled"] = False
            self.save_data()
        await ctx.send("⛔ このチャンネルの自動リアクションを無効にしたよ")

    @commands.command(name="react_add")
    @commands.has_permissions(manage_channels=True)
    async def react_add(self, ctx, emoji: str):
        cid = str(ctx.channel.id)
        self.data.setdefault(cid, {"enabled": True, "emojis": []})

        if emoji in self.data[cid]["emojis"]:
            await ctx.send("⚠️ その絵文字はすでに登録されてるよ")
            return

        self.data[cid]["emojis"].append(emoji)
        self.save_data()
        await ctx.send(f"➕ リアクションに {emoji} を追加したよ！")

    @commands.command(name="react_remove")
    @commands.has_permissions(manage_channels=True)
    async def react_remove(self, ctx, emoji: str):
        cid = str(ctx.channel.id)
        if cid not in self.data or emoji not in self.data[cid]["emojis"]:
            await ctx.send("❌ その絵文字は登録されてないよ")
            return

        self.data[cid]["emojis"].remove(emoji)
        self.save_data()
        await ctx.send(f"➖ リアクション {emoji} を削除したよ")

    @commands.command(name="react_list")
    async def react_list(self, ctx):
        cid = str(ctx.channel.id)
        config = self.data.get(cid)

        if not config or not config.get("emojis"):
            await ctx.send("📭 このチャンネルにはリアクションが設定されていません。")
            return

        emojis = " ".join(config["emojis"])
        status = "ON" if config.get("enabled") else "OFF"
        await ctx.send(f"📌 状態: {status}\n🎭 絵文字: {emojis}")

    @commands.command(name="react_apply")
    @commands.has_permissions(manage_messages=True)
    async def react_apply(self, ctx, message_id: int):
        cid = str(ctx.channel.id)
        config = self.data.get(cid)

        if not config or not config.get("emojis"):
            await ctx.reply("このチャンネルにはリアクションが設定されていません。")
            return

        try:
            message = await ctx.channel.fetch_message(message_id)
        except discord.NotFound:
            await ctx.reply("そのメッセージは見つからりませんでした。")
            return
        except discord.Forbidden:
            await ctx.reply("そのメッセージにアクセスできません。")
            return

        added = 0

        for emoji in config["emojis"]:
            already = False
            for reaction in message.reactions:
                if str(reaction.emoji) == emoji:
                    async for user in reaction.users():
                        if user.id == self.bot.user.id:
                            already = True
                            break

            if already:
                continue

            try:
                await message.add_reaction(emoji)
                added += 1
                await asyncio.sleep(REACTION_DELAY)
            except discord.HTTPException:
                pass

        await ctx.reply(f"指定メッセージに {added} 個のリアクションを追加しました。")



async def setup(bot):
    await bot.add_cog(Emoji(bot))
