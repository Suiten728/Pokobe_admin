import discord
from discord.ext import commands
import json
import os
import asyncio
from dotenv import load_dotenv

load_dotenv()

DATA_PATH = "data/emoji_react.json"
REACTION_DELAY = 0.7

try:
    STAFF_ROLE_ID = int(os.getenv("STAFF_ROLE_ID", "0"))
except (ValueError, TypeError):
    STAFF_ROLE_ID = 0


# ───────────────────────────────────────────────
#  ユーティリティ
# ───────────────────────────────────────────────

def is_staff(ctx) -> bool:
    return any(r.id == STAFF_ROLE_ID for r in ctx.author.roles)


def build_summary(data: dict, channel_id: str) -> str:
    config = data.get(channel_id, {})
    status = "🟢 ON" if config.get("enabled") else "🔴 OFF"
    emojis = " ".join(config.get("emojis", [])) or "（なし）"
    detached_count = len(config.get("detached", []))
    return (
        f"## ⚙️ リアクション管理\n"
        f"**状態:** {status}\n"
        f"**絵文字:** {emojis}\n"
        f"**排除メッセージ数:** {detached_count} 件"
    )


async def bot_already_reacted(message: discord.Message, emoji: str, bot_id: int) -> bool:
    """Botが既にその絵文字でリアクション済みかどうかを確認する"""
    for reaction in message.reactions:
        if str(reaction.emoji) == emoji:
            async for user in reaction.users():
                if user.id == bot_id:
                    return True
    return False


# ───────────────────────────────────────────────
#  NoCopy ミックスイン
#  LayoutView は __init__ 時にクラス変数の items を deepcopy するが、
#  cog（bot を含む）は asyncio.Future を持つためコピー不可。
#  __deepcopy__ で自分自身を返すことで deepcopy をスキップする。
# ───────────────────────────────────────────────

class NoCopy:
    def __deepcopy__(self, memo):
        return self


# ───────────────────────────────────────────────
#  共通ボタン
# ───────────────────────────────────────────────

class BackButton(NoCopy, discord.ui.Button):
    def __init__(self, cog, channel_id: str):
        super().__init__(label="戻る", style=discord.ButtonStyle.secondary)
        self._cog = cog
        self._channel_id = channel_id

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(
            view=make_main_view(self._cog, self._channel_id)
        )


# ───────────────────────────────────────────────
#  メインビュー
# ───────────────────────────────────────────────

class OperationSelect(NoCopy, discord.ui.Select):
    def __init__(self, cog, channel_id: str):
        self._cog = cog
        self._channel_id = channel_id
        options = [
            discord.SelectOption(label="ON",               value="on",     emoji="🟢", description="自動リアクションを有効化"),
            discord.SelectOption(label="OFF",              value="off",    emoji="🔴", description="自動リアクションを無効化"),
            discord.SelectOption(label="絵文字を追加",     value="add",    emoji="➕"),
            discord.SelectOption(label="絵文字を削除",     value="remove", emoji="➖"),
            discord.SelectOption(label="一覧を確認",       value="list",   emoji="📋"),
            discord.SelectOption(label="メッセージに適用", value="apply",  emoji="✅"),
            discord.SelectOption(label="メッセージを排除", value="detach", emoji="🚫"),
        ]
        super().__init__(placeholder="操作を選択してください", options=options)

    async def callback(self, interaction: discord.Interaction):
        val = self.values[0]
        cid = self._channel_id

        if val in ("on", "off"):
            self._cog.data.setdefault(cid, {"enabled": False, "emojis": [], "detached": []})
            self._cog.data[cid]["enabled"] = (val == "on")
            self._cog.save_data()
            label = "✅ 有効にしました！" if val == "on" else "⛔ 無効にしました"
            await interaction.response.edit_message(view=make_main_view(self._cog, cid))
            await interaction.followup.send(label, ephemeral=True)

        elif val == "add":
            await interaction.response.edit_message(view=make_add_view(self._cog, cid))

        elif val == "remove":
            emojis = self._cog.data.get(cid, {}).get("emojis", [])
            if not emojis:
                await interaction.response.send_message("❌ 削除できる絵文字がありません", ephemeral=True)
            else:
                await interaction.response.edit_message(view=make_remove_view(self._cog, cid))

        elif val == "list":
            config = self._cog.data.get(cid, {})
            emojis = " ".join(config.get("emojis", [])) or "（なし）"
            status = "ON" if config.get("enabled") else "OFF"
            detached = config.get("detached", [])
            det_text = "\n".join(f"• `{d}`" for d in detached) if detached else "（なし）"
            await interaction.response.send_message(
                f"📌 状態: **{status}**\n🎭 絵文字: {emojis}\n🚫 排除リスト:\n{det_text}",
                ephemeral=True,
            )

        elif val == "apply":
            await interaction.response.edit_message(view=make_apply_view(self._cog, cid))

        elif val == "detach":
            await interaction.response.edit_message(view=make_detach_view(self._cog, cid))


def make_main_view(cog, channel_id: str):
    class MainControlView(discord.ui.LayoutView):
        container = discord.ui.Container(
            discord.ui.TextDisplay(build_summary(cog.data, channel_id)),
            discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
            discord.ui.ActionRow(OperationSelect(cog, channel_id)),
            accent_colour=discord.Colour.blurple(),
        )
    return MainControlView(timeout=300)


# ───────────────────────────────────────────────
#  追加フロー
# ───────────────────────────────────────────────

class AddButton(NoCopy, discord.ui.Button):
    def __init__(self, cog, channel_id: str):
        super().__init__(label="追加する", style=discord.ButtonStyle.primary)
        self._cog = cog
        self._channel_id = channel_id

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "絵文字をこのチャンネルに **1つだけ** 送信してください（30秒以内）",
            ephemeral=True,
        )

        def check(m: discord.Message):
            return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id

        try:
            msg = await interaction.client.wait_for("message", check=check, timeout=30.0)
        except asyncio.TimeoutError:
            await interaction.followup.send("⏱️ タイムアウトしました", ephemeral=True)
            return

        emoji = msg.content.strip()
        try:
            await msg.delete()
        except discord.HTTPException:
            pass

        config = self._cog.data.setdefault(
            self._channel_id, {"enabled": False, "emojis": [], "detached": []}
        )
        config.setdefault("emojis", [])

        if emoji in config["emojis"]:
            await interaction.followup.send("⚠️ その絵文字はすでに登録されています", ephemeral=True)
            return

        config["emojis"].append(emoji)
        self._cog.save_data()

        await interaction.message.edit(view=make_add_confirm_view(self._cog, self._channel_id, emoji))
        await interaction.followup.send(
            f"✅ **{emoji}** を追加しました！\n"
            "過去のメッセージにも適用しますか？（パネルのボタンから選択）",
            ephemeral=True,
        )


def make_add_view(cog, channel_id: str):
    class AddView(discord.ui.LayoutView):
        container = discord.ui.Container(
            discord.ui.TextDisplay(
                "## ➕ 絵文字を追加\n"
                "「追加する」を押すと、このチャンネルに絵文字を送信するよう指示が届きます。"
            ),
            discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
            discord.ui.ActionRow(
                AddButton(cog, channel_id),
                BackButton(cog, channel_id),
            ),
            accent_colour=discord.Colour.green(),
        )
    return AddView(timeout=300)


class ApplyToPastButton(NoCopy, discord.ui.Button):
    def __init__(self, cog, channel_id: str, emoji: str):
        super().__init__(label="適用する", style=discord.ButtonStyle.success)
        self._cog = cog
        self._channel_id = channel_id
        self._emoji = emoji

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(view=make_main_view(self._cog, self._channel_id))
        await interaction.followup.send("🔄 過去のメッセージに適用中...", ephemeral=True)

        bot_id = interaction.client.user.id
        added = 0
        detached = self._cog.data.get(self._channel_id, {}).get("detached", [])

        async for message in interaction.channel.history(limit=100):
            if message.author.bot:
                continue
            if str(message.id) in detached:
                continue
            # Botが既にリアクション済みかどうかを確認
            already = await bot_already_reacted(message, self._emoji, bot_id)
            if already:
                continue
            try:
                await message.add_reaction(self._emoji)
                added += 1
                await asyncio.sleep(REACTION_DELAY)
            except discord.HTTPException:
                pass

        await interaction.followup.send(
            f"✅ {added} 件のメッセージに {self._emoji} を適用しました", ephemeral=True
        )


class SkipApplyButton(NoCopy, discord.ui.Button):
    def __init__(self, cog, channel_id: str):
        super().__init__(label="適用しない", style=discord.ButtonStyle.secondary)
        self._cog = cog
        self._channel_id = channel_id

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(view=make_main_view(self._cog, self._channel_id))


def make_add_confirm_view(cog, channel_id: str, emoji: str):
    class AddApplyConfirmView(discord.ui.LayoutView):
        container = discord.ui.Container(
            discord.ui.TextDisplay(
                f"## ✅ {emoji} を追加しました！\n"
                f"過去のメッセージ（最新 100 件）にも {emoji} を追加しますか？"
            ),
            discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
            discord.ui.ActionRow(
                ApplyToPastButton(cog, channel_id, emoji),
                SkipApplyButton(cog, channel_id),
            ),
            accent_colour=discord.Colour.green(),
        )
    return AddApplyConfirmView(timeout=300)


# ───────────────────────────────────────────────
#  削除フロー
# ───────────────────────────────────────────────

class EmojiRemoveSelect(NoCopy, discord.ui.Select):
    def __init__(self, cog, channel_id: str):
        self._cog = cog
        self._channel_id = channel_id
        emojis = cog.data.get(channel_id, {}).get("emojis", [])
        options = [discord.SelectOption(label=e, value=e) for e in emojis]
        super().__init__(placeholder="削除する絵文字を選択", options=options)

    async def callback(self, interaction: discord.Interaction):
        emoji = self.values[0]
        config = self._cog.data.get(self._channel_id, {})
        if emoji in config.get("emojis", []):
            config["emojis"].remove(emoji)
            self._cog.save_data()
        await interaction.response.edit_message(view=make_main_view(self._cog, self._channel_id))
        await interaction.followup.send(f"➖ {emoji} を削除しました", ephemeral=True)


def make_remove_view(cog, channel_id: str):
    class RemoveView(discord.ui.LayoutView):
        container = discord.ui.Container(
            discord.ui.TextDisplay("## ➖ 絵文字を削除\n削除する絵文字を選択してください。"),
            discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
            discord.ui.ActionRow(EmojiRemoveSelect(cog, channel_id)),
            discord.ui.ActionRow(BackButton(cog, channel_id)),
            accent_colour=discord.Colour.red(),
        )
    return RemoveView(timeout=300)


# ───────────────────────────────────────────────
#  Apply フロー
# ───────────────────────────────────────────────

class ApplyInputButton(NoCopy, discord.ui.Button):
    def __init__(self, cog, channel_id: str):
        super().__init__(label="メッセージIDを入力", style=discord.ButtonStyle.primary)
        self._cog = cog
        self._channel_id = channel_id

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "適用するメッセージの **ID** をこのチャンネルに送信してください（30秒以内）",
            ephemeral=True,
        )

        def check(m: discord.Message):
            return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id

        try:
            msg = await interaction.client.wait_for("message", check=check, timeout=30.0)
        except asyncio.TimeoutError:
            await interaction.followup.send("⏱️ タイムアウトしました", ephemeral=True)
            return

        raw = msg.content.strip()
        try:
            await msg.delete()
        except discord.HTTPException:
            pass

        if not raw.isdigit():
            await interaction.followup.send("❌ 無効なメッセージIDです", ephemeral=True)
            return
        message_id = int(raw)

        config = self._cog.data.get(self._channel_id, {})
        emojis = config.get("emojis", [])
        if not emojis:
            await interaction.followup.send("❌ 絵文字が設定されていません", ephemeral=True)
            return

        if str(message_id) in config.get("detached", []):
            await interaction.followup.send("🚫 そのメッセージは排除リストに含まれています", ephemeral=True)
            return

        try:
            target = await interaction.channel.fetch_message(message_id)
        except discord.NotFound:
            await interaction.followup.send("❌ メッセージが見つかりませんでした", ephemeral=True)
            return
        except discord.Forbidden:
            await interaction.followup.send("❌ そのメッセージにアクセスできません", ephemeral=True)
            return

        bot_id = interaction.client.user.id
        added = 0
        for emoji in emojis:
            # Botが既にリアクション済みかどうかを確認
            already = await bot_already_reacted(target, emoji, bot_id)
            if already:
                continue
            try:
                await target.add_reaction(emoji)
                added += 1
                await asyncio.sleep(REACTION_DELAY)
            except discord.HTTPException:
                pass

        await interaction.message.edit(view=make_main_view(self._cog, self._channel_id))
        await interaction.followup.send(
            f"✅ {added} 個のリアクションをメッセージ `{message_id}` に追加しました", ephemeral=True
        )


def make_apply_view(cog, channel_id: str):
    class ApplyInputView(discord.ui.LayoutView):
        container = discord.ui.Container(
            discord.ui.TextDisplay(
                "## ✅ メッセージに適用\n"
                "リアクションを追加したいメッセージのIDを入力します。\n"
                "排除リストに含まれるメッセージには適用されません。"
            ),
            discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
            discord.ui.ActionRow(
                ApplyInputButton(cog, channel_id),
                BackButton(cog, channel_id),
            ),
            accent_colour=discord.Colour.green(),
        )
    return ApplyInputView(timeout=300)


# ───────────────────────────────────────────────
#  Detach フロー
# ───────────────────────────────────────────────

class DetachInputButton(NoCopy, discord.ui.Button):
    def __init__(self, cog, channel_id: str):
        super().__init__(label="メッセージIDを入力", style=discord.ButtonStyle.danger)
        self._cog = cog
        self._channel_id = channel_id

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "排除するメッセージの **ID** をこのチャンネルに送信してください（30秒以内）\n"
            "※ そのメッセージのBotリアクションを削除し、今後 apply されなくなります",
            ephemeral=True,
        )

        def check(m: discord.Message):
            return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id

        try:
            msg = await interaction.client.wait_for("message", check=check, timeout=30.0)
        except asyncio.TimeoutError:
            await interaction.followup.send("⏱️ タイムアウトしました", ephemeral=True)
            return

        raw = msg.content.strip()
        try:
            await msg.delete()
        except discord.HTTPException:
            pass

        if not raw.isdigit():
            await interaction.followup.send("❌ 無効なメッセージIDです", ephemeral=True)
            return
        message_id = int(raw)
        str_id = str(message_id)

        config = self._cog.data.setdefault(
            self._channel_id, {"enabled": False, "emojis": [], "detached": []}
        )
        config.setdefault("detached", [])

        if str_id in config["detached"]:
            await interaction.followup.send("⚠️ そのメッセージはすでに排除リストに含まれています", ephemeral=True)
            return

        removed = 0
        try:
            target = await interaction.channel.fetch_message(message_id)
            for reaction in target.reactions:
                try:
                    await target.remove_reaction(reaction.emoji, interaction.guild.me)
                    removed += 1
                    await asyncio.sleep(REACTION_DELAY)
                except discord.HTTPException:
                    pass
        except (discord.NotFound, discord.Forbidden):
            pass

        config["detached"].append(str_id)
        self._cog.save_data()

        await interaction.message.edit(view=make_main_view(self._cog, self._channel_id))
        await interaction.followup.send(
            f"🚫 メッセージ `{message_id}` を排除リストに追加しました（リアクション {removed} 件を削除）",
            ephemeral=True,
        )


def make_detach_view(cog, channel_id: str):
    class DetachInputView(discord.ui.LayoutView):
        container = discord.ui.Container(
            discord.ui.TextDisplay(
                "## 🚫 メッセージを排除\n"
                "指定したメッセージからBotのリアクションを削除し、\n"
                "今後 `apply` からも適用されなくなります。"
            ),
            discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
            discord.ui.ActionRow(
                DetachInputButton(cog, channel_id),
                BackButton(cog, channel_id),
            ),
            accent_colour=discord.Colour.red(),
        )
    return DetachInputView(timeout=300)


# ───────────────────────────────────────────────
#  Cog
# ───────────────────────────────────────────────

class Emoji(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.data = self.load_data()

    def load_data(self) -> dict:
        if not os.path.exists(DATA_PATH):
            return {}
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_data(self):
        os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
        with open(DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

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

    @commands.command(name="react-ctrl")
    async def react_ctrl(self, ctx: commands.Context):
        if not is_staff(ctx):
            await ctx.send("❌ この操作にはスタッフロールが必要です", delete_after=5)
            return
        cid = str(ctx.channel.id)
        await ctx.send(view=make_main_view(self, cid))


async def setup(bot: commands.Bot):
    await bot.add_cog(Emoji(bot))