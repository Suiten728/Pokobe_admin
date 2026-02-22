import discord
from discord.ext import commands


# ═══════════════════════════════════════════════════════════════
#  インタラクティブコンポーネント（サブクラスで callback を定義）
# ═══════════════════════════════════════════════════════════════

class OptionSelect(discord.ui.StringSelect):
    def __init__(self):
        super().__init__(
            placeholder="🔽 オプションを選択してください",
            options=[
                discord.SelectOption(label="オプション A", value="a", emoji="🔴", description="赤いオプション"),
                discord.SelectOption(label="オプション B", value="b", emoji="🟡", description="黄色いオプション"),
                discord.SelectOption(label="オプション C", value="c", emoji="🟢", description="緑のオプション"),
            ],
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        chosen = self.values[0].upper()
        await interaction.response.send_message(
            f"✅ **セレクトテスト完了！** 選択: **オプション {chosen}**",
            ephemeral=True,
        )


class SendButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="送信テスト", style=discord.ButtonStyle.primary, emoji="📨")

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(
            "📨 **送信テスト完了！** Primaryボタンが正常に動作しました。",
            ephemeral=True,
        )


class SuccessButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="成功ボタン", style=discord.ButtonStyle.success, emoji="✅")

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(
            "✅ **成功ボタンテスト完了！** Successスタイルが機能しています。",
            ephemeral=True,
        )


class DangerButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="危険ボタン", style=discord.ButtonStyle.danger, emoji="⛔")

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(
            "⛔ **危険ボタンテスト完了！** Dangerスタイルが機能しています。",
            ephemeral=True,
        )


# ═══════════════════════════════════════════════════════════════
#  LayoutView（コンポーネントを ActionRow に入れて Container に配置）
# ═══════════════════════════════════════════════════════════════

class DCV2View(discord.ui.LayoutView):
    container = discord.ui.Container(
        # ── ヘッダー ──────────────────────────────────────────
        discord.ui.TextDisplay("# 🧪 Component v2 動作テスト"),
        discord.ui.Separator(spacing=discord.SeparatorSpacing.large),

        # ── 説明文 ────────────────────────────────────────────
        discord.ui.TextDisplay(
            "**discord.py 2.6.4 / Component v2 (LayoutView)** のテスト画面です。\n"
            "以下のコンポーネントをそれぞれ操作して動作確認してください。\n\n"
            "- 🔽 **セレクトメニュー** — 選択肢を選ぶ\n"
            "- 📨 **送信テスト** — Primaryボタンで送信確認\n"
            "- ✅ / ⛔ **スタイル確認** — Success / Danger ボタン"
        ),
        discord.ui.Separator(spacing=discord.SeparatorSpacing.small),

        # ── セレクトメニュー ──────────────────────────────────
        discord.ui.ActionRow(OptionSelect()),
        discord.ui.Separator(spacing=discord.SeparatorSpacing.small),

        # ── ボタン群 ──────────────────────────────────────────
        discord.ui.ActionRow(SendButton(), SuccessButton(), DangerButton()),
        discord.ui.Separator(spacing=discord.SeparatorSpacing.small),

        # ── フッター ──────────────────────────────────────────
        discord.ui.TextDisplay(
            "-# Component v2 テスト  |  discord.py 2.6.4  |  LayoutView"
        ),
        accent_colour=discord.Colour.blurple(),
    )


# ═══════════════════════════════════════════════════════════════
#  Cog
# ═══════════════════════════════════════════════════════════════

class DCV2Cog(commands.Cog, name="DCV2"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command(name="dcv2")
    async def dcv2(self, ctx: commands.Context) -> None:
        """P!dcv2 — Component v2 (LayoutView) の動作テストを送信"""
        view = DCV2View()
        await ctx.send(view=view)


# ═══════════════════════════════════════════════════════════════
#  setup
# ═══════════════════════════════════════════════════════════════

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(DCV2Cog(bot))
