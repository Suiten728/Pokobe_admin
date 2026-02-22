import discord
from discord.ext import commands


# ═══════════════════════════════════════════════════════════════
#  Component v2 LayoutView
# ═══════════════════════════════════════════════════════════════
class DCV2View(discord.ui.LayoutView):
    """Component v2 LayoutView テストビュー"""

    # Container をクラス属性として直接定義（ネストクラス不使用）
    container = discord.ui.Container(
        discord.ui.TextDisplay("# 🧪 Component v2 動作テスト"),
        discord.ui.Separator(
            spacing=discord.SeparatorSpacing.large,
            divider=True,
        ),
        discord.ui.TextDisplay(
            "**discord.py 2.6.4 / Component v2 (LayoutView)** のテスト画面です。\n"
            "以下のコンポーネントをそれぞれ操作して動作確認してください。\n\n"
            "- 🔽 **セレクトメニュー** — 選択肢を選ぶ\n"
            "- 📨 **送信テスト** — Primaryボタンで送信確認\n"
            "- ✅ / ⛔ **スタイル確認** — Success / Danger ボタン"
        ),
        discord.ui.Separator(divider=True),
        discord.ui.TextDisplay("-# Component v2 テスト  |  discord.py 2.6.4  |  LayoutView"),
        accent_colour=discord.Colour.blurple(),
    )

    # ── StringSelect ────────────────────────────────────────────
    @discord.ui.string_select(
        placeholder="🔽 オプションを選択してください",
        options=[
            discord.SelectOption(
                label="オプション A", value="a",
                emoji="🔴", description="赤いオプション",
            ),
            discord.SelectOption(
                label="オプション B", value="b",
                emoji="🟡", description="黄色いオプション",
            ),
            discord.SelectOption(
                label="オプション C", value="c",
                emoji="🟢", description="緑のオプション",
            ),
        ],
    )
    async def select_callback(
        self,
        interaction: discord.Interaction,
        select: discord.ui.StringSelect,
    ) -> None:
        chosen = select.values[0].upper()
        await interaction.response.send_message(
            f"✅ **セレクトテスト完了！** 選択: **オプション {chosen}**",
            ephemeral=True,
        )

    # ── ボタン：Primary ─────────────────────────────────────────
    @discord.ui.button(
        label="送信テスト",
        style=discord.ButtonStyle.primary,
        emoji="📨",
    )
    async def send_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        await interaction.response.send_message(
            "📨 **送信テスト完了！** Primaryボタンが正常に動作しました。",
            ephemeral=True,
        )

    # ── ボタン：Success ─────────────────────────────────────────
    @discord.ui.button(
        label="成功ボタン",
        style=discord.ButtonStyle.success,
        emoji="✅",
    )
    async def success_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        await interaction.response.send_message(
            "✅ **成功ボタンテスト完了！** Successスタイルが機能しています。",
            ephemeral=True,
        )

    # ── ボタン：Danger ──────────────────────────────────────────
    @discord.ui.button(
        label="危険ボタン",
        style=discord.ButtonStyle.danger,
        emoji="⛔",
    )
    async def danger_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        await interaction.response.send_message(
            "⛔ **危険ボタンテスト完了！** Dangerスタイルが機能しています。",
            ephemeral=True,
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
