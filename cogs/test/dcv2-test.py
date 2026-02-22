import discord
from discord.ext import commands


# ═══════════════════════════════════════════════════════════════
#  Component v2 LayoutView
# ═══════════════════════════════════════════════════════════════
class DCV2View(discord.ui.LayoutView):
    """
    Component v2 の LayoutView テストビュー。
    Container の中に TextDisplay / Separator / StringSelect / Button を配置。
    """

    @discord.ui.container(accent_colour=discord.Colour.blurple())
    class MainContainer(discord.ui.Container):

        # ── ヘッダー ────────────────────────────────────────────────────
        header = discord.ui.TextDisplay("# 🧪 Component v2 動作テスト")

        sep_top = discord.ui.Separator(
            spacing=discord.SeparatorSpacing.large,
            divider=True,
        )

        # ── 説明文 ──────────────────────────────────────────────────────
        description = discord.ui.TextDisplay(
            "**discord.py 2.6.4 / Component v2 (LayoutView)** のテスト画面です。\n"
            "以下のコンポーネントをそれぞれ操作して動作確認してください。\n\n"
            "- 🔽 **セレクトメニュー** — 選択肢を選ぶ\n"
            "- 📨 **送信テスト** — Primaryボタンで送信確認\n"
            "- ✅ / ⛔ **スタイル確認** — Success / Danger ボタン"
        )

        sep_1 = discord.ui.Separator(divider=True)

        # ── StringSelect ────────────────────────────────────────────────
        @discord.ui.string_select(
            placeholder="🔽 オプションを選択してください",
            options=[
                discord.SelectOption(
                    label="オプション A",
                    value="a",
                    emoji="🔴",
                    description="赤いオプション",
                ),
                discord.SelectOption(
                    label="オプション B",
                    value="b",
                    emoji="🟡",
                    description="黄色いオプション",
                ),
                discord.SelectOption(
                    label="オプション C",
                    value="c",
                    emoji="🟢",
                    description="緑のオプション",
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

        sep_2 = discord.ui.Separator()

        # ── ボタン：Primary ─────────────────────────────────────────────
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

        # ── ボタン：Success ─────────────────────────────────────────────
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

        # ── ボタン：Danger ──────────────────────────────────────────────
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

        sep_foot = discord.ui.Separator(divider=True)

        # ── フッター ────────────────────────────────────────────────────
        footer = discord.ui.TextDisplay(
            "-# Component v2 テスト  |  discord.py 2.6.4  |  LayoutView"
        )


# ═══════════════════════════════════════════════════════════════
#  Cog
# ═══════════════════════════════════════════════════════════════
class DCV2Cog(commands.Cog, name="DCV2"):
    """Component v2 LayoutView のテストコマンドを提供するCog。"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command(name="dcv2")
    async def dcv2(self, ctx: commands.Context) -> None:
        """Component v2 (LayoutView) の動作テストを送信します。"""
        view = DCV2View()
        await ctx.send(view=view)


# ═══════════════════════════════════════════════════════════════
#  setup (必須)
# ═══════════════════════════════════════════════════════════════
async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(DCV2Cog(bot))
