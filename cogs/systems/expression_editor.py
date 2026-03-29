# cogs/ees/expression_editor.py
# ExpressionEditorSystem (EES) — discord.py 2.6.4 / Components V2 LayoutView
# ============================================================================
#
# .env に以下を設定してください:
#   EES_CI_ROLE_ID      = 運営ロールのID（0 = 全員許可）
#   EES_YOUTUBE_URL     = ガイド動画の YouTube URL
#   EES_EMOJI_RULE_URL  = 絵文字命名規則ページの URL
#
# assets/main/ees_logo.png にロゴ画像を配置してください。
# ============================================================================

from __future__ import annotations

import os
import traceback

import discord
from discord.ext import commands

# ── .env 設定値 ────────────────────────────────────────────────────────────
# ※ bot.py 側で load_dotenv() 済み前提。未設定時のデフォルトも明示。

CI_ROLE_ID: int     = int(os.getenv("EES_CI_ROLE_ID", "0"))
YOUTUBE_URL: str    = os.getenv("EES_YOUTUBE_URL", "https://www.youtube.com/watch?v=AAAAAA")
EMOJI_RULE_URL: str = os.getenv("EES_EMOJI_RULE_URL", "https://example.com")

IMAGE_PATH: str     = "assets/main/ees_logo.png"
IMAGE_FILENAME: str = "ees_logo.png"

SYSTEM_DESC: str = (
    "ExpressionEditorSystem(EES)は絵文字・ステッカー・サウンドボードを"
    "簡易的に編集可能な運営メンバー限定のシステムです。"
)

# Discordのブースト段階ごとのステッカー上限
_STICKER_LIMITS: dict[int, int] = {0: 5, 1: 15, 2: 30, 3: 60}


# ── 権限チェック ────────────────────────────────────────────────────────────

def _has_ci_role(member: discord.Member) -> bool:
    """CI_ROLE_ID が 0 の場合は全員許可、それ以外はロール所持を確認する。"""
    if CI_ROLE_ID == 0:
        return True
    return any(role.id == CI_ROLE_ID for role in member.roles)


# ── NoCopy ミックスイン ─────────────────────────────────────────────────────
# LayoutView は container をクラス変数として deepcopy するため、
# asyncio.Future を間接的に保持するオブジェクト（cog, bot など）を
# 持つコンポーネントには必ずこのミックスインを付ける。

class NoCopy:
    def __deepcopy__(self, memo):
        return self


# ── ロゴ画像ブロック生成ヘルパー ────────────────────────────────────────────
#
# discord.py 2.6.4 の Components V2 では MediaGallery が利用可能です。
# もし AttributeError が発生する場合は、以下のように Section + Thumbnail に変更:
#
#   discord.ui.Section(
#       discord.ui.TextDisplay("**ExpressionEditorSystem**"),
#       accessory=discord.ui.Thumbnail(media=f"attachment://{IMAGE_FILENAME}"),
#   )
#
# その場合、タイトルテキストとロゴが左右に並ぶレイアウトになります。

def _logo_gallery() -> discord.ui.MediaGallery:
    return discord.ui.MediaGallery(
        discord.ui.MediaGalleryItem(media=f"attachment://{IMAGE_FILENAME}"),
    )


# ────────────────────────────────────────────────────────────────────────────
# ボタン定義
# ────────────────────────────────────────────────────────────────────────────

class _NotesButton(NoCopy, discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="注意事項",
            emoji="🚫",
            style=discord.ButtonStyle.danger,
            custom_id="ees_notes_btn",
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        try:
            file = discord.File(IMAGE_PATH, filename=IMAGE_FILENAME)
            await interaction.response.edit_message(
                view=_make_notes_view(), attachments=[file]
            )
        except Exception as e:
            traceback.print_exc()
            await interaction.response.send_message(f"エラー: {e}", ephemeral=True)


class _GuideButton(NoCopy, discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="ガイド動画を見る",
            emoji="📽",
            style=discord.ButtonStyle.success,
            custom_id="ees_guide_btn",
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        try:
            file = discord.File(IMAGE_PATH, filename=IMAGE_FILENAME)
            await interaction.response.edit_message(
                view=_make_guide_view(), attachments=[file]
            )
        except Exception as e:
            traceback.print_exc()
            await interaction.response.send_message(f"エラー: {e}", ephemeral=True)


class _BackToMainButton(NoCopy, discord.ui.Button):
    """注意事項・ガイド・各エディタ共通の「戻る」ボタン。"""
    def __init__(self):
        super().__init__(
            label="戻る",
            emoji="◀",
            style=discord.ButtonStyle.secondary,
            custom_id="ees_back_btn",
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        try:
            file = discord.File(IMAGE_PATH, filename=IMAGE_FILENAME)
            await interaction.response.edit_message(
                view=_make_main_view(), attachments=[file]
            )
        except Exception as e:
            traceback.print_exc()
            await interaction.response.send_message(f"エラー: {e}", ephemeral=True)


class _EmojiRuleButton(discord.ui.Button):
    """.env の URL へ飛ぶリンクボタン（コールバックなし）。"""
    def __init__(self):
        super().__init__(
            label="絵文字名ルール",
            emoji="📌",
            style=discord.ButtonStyle.link,
            url=EMOJI_RULE_URL,
        )


# ────────────────────────────────────────────────────────────────────────────
# セレクトメニュー定義
# ────────────────────────────────────────────────────────────────────────────

class _CategorySelect(NoCopy, discord.ui.Select):
    def __init__(self):
        super().__init__(
            placeholder="編集するカテゴリを選択してください",
            custom_id="ees_category_select",
            options=[
                discord.SelectOption(label="絵文字を編集",         value="emoji",      emoji="🎨"),
                discord.SelectOption(label="ステッカーを編集",     value="sticker",    emoji="📎"),
                discord.SelectOption(label="サウンドボードを編集", value="soundboard", emoji="🎵"),
            ],
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        guild  = interaction.guild
        choice = self.values[0]

        try:
            if choice == "emoji":
                normal = len([e for e in guild.emojis if not e.animated])
                anime  = len([e for e in guild.emojis if e.animated])
                limit  = guild.emoji_limit
                view   = _make_emoji_editor_view(normal, anime, limit, limit)
                await interaction.response.edit_message(view=view, attachments=[])

            elif choice == "sticker":
                limit   = _STICKER_LIMITS.get(guild.premium_tier, 5)
                _anim   = {
                    discord.StickerFormatType.apng,
                    discord.StickerFormatType.lottie,
                    discord.StickerFormatType.gif,
                }
                stickers = guild.stickers   # キャッシュから取得（API 呼び出しなし）
                normal   = len([s for s in stickers if s.format not in _anim])
                anime    = len([s for s in stickers if s.format in _anim])
                view     = _make_sticker_editor_view(normal, anime, limit, limit)
                await interaction.response.edit_message(view=view, attachments=[])

            elif choice == "soundboard":
                sounds = getattr(guild, "soundboard_sounds", [])
                count  = len(sounds)
                # サウンドボード上限はブースト段階に関わらず 8（カスタム音声）
                limit  = 8
                view   = _make_sb_editor_view(count, limit)
                await interaction.response.edit_message(view=view, attachments=[])

        except Exception as e:
            traceback.print_exc()
            if not interaction.response.is_done():
                await interaction.response.send_message(f"エラー: {e}", ephemeral=True)


class _EmojiActionSelect(NoCopy, discord.ui.Select):
    def __init__(self):
        super().__init__(
            placeholder="編集内容を選択してください",
            custom_id="ees_emoji_action_select",
            options=[
                discord.SelectOption(label="追加",     value="add",     emoji="➕"),
                discord.SelectOption(label="削除",     value="remove",  emoji="➖"),
                discord.SelectOption(label="置き換え", value="replace", emoji="🔄"),
            ],
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        _labels = {"add": "追加", "remove": "削除", "replace": "置き換え"}
        await interaction.response.send_message(
            f"絵文字の **{_labels[self.values[0]]}** 機能は現在準備中です。",
            ephemeral=True,
        )


class _StickerActionSelect(NoCopy, discord.ui.Select):
    def __init__(self):
        super().__init__(
            placeholder="編集内容を選択してください",
            custom_id="ees_sticker_action_select",
            options=[
                discord.SelectOption(label="追加",     value="add",     emoji="➕"),
                discord.SelectOption(label="削除",     value="remove",  emoji="➖"),
                discord.SelectOption(label="置き換え", value="replace", emoji="🔄"),
            ],
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        _labels = {"add": "追加", "remove": "削除", "replace": "置き換え"}
        await interaction.response.send_message(
            f"ステッカーの **{_labels[self.values[0]]}** 機能は現在準備中です。",
            ephemeral=True,
        )


class _SBActionSelect(NoCopy, discord.ui.Select):
    def __init__(self):
        super().__init__(
            placeholder="編集内容を選択してください",
            custom_id="ees_sb_action_select",
            options=[
                discord.SelectOption(label="追加",     value="add",     emoji="➕"),
                discord.SelectOption(label="削除",     value="remove",  emoji="➖"),
                discord.SelectOption(label="置き換え", value="replace", emoji="🔄"),
            ],
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        _labels = {"add": "追加", "remove": "削除", "replace": "置き換え"}
        await interaction.response.send_message(
            f"サウンドボードの **{_labels[self.values[0]]}** 機能は現在準備中です。",
            ephemeral=True,
        )


# ────────────────────────────────────────────────────────────────────────────
# View ファクトリ関数
#
# LayoutView の container はメタクラスがクラス定義時にスキャンする「クラス変数」
# でなければならない。動的な値（カウント等）を埋め込むため、ファクトリ関数内で
# クラスを毎回定義するパターンを採用している（dcv2_notes.md 参照）。
# ────────────────────────────────────────────────────────────────────────────

def _make_main_view() -> discord.ui.LayoutView:
    """メインボード（カテゴリ選択・注意事項・ガイドへの入口）。"""

    class MainView(discord.ui.LayoutView):
        container = discord.ui.Container(
            # ── ヘッダー ──
            discord.ui.TextDisplay("**ExpressionEditorSystem**"),
            _logo_gallery(),
            discord.ui.TextDisplay(SYSTEM_DESC),
            discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
            # ── 横並びリンク行（Section = テキスト左・ボタン右） ──
            discord.ui.Section(
                discord.ui.TextDisplay("利用上の注意事項："),
                accessory=_NotesButton(),
            ),
            discord.ui.Section(
                discord.ui.TextDisplay("利用方法ガイド："),
                accessory=_GuideButton(),
            ),
            discord.ui.Separator(spacing=discord.SeparatorSpacing.large),
            # ── カテゴリ選択 ──
            discord.ui.TextDisplay("以下のプルダウンから編集したいカテゴリーを選択してください。"),
            discord.ui.ActionRow(_CategorySelect()),
            accent_colour=discord.Colour.from_str("#00b0f4"),   # シアン
        )

    return MainView(timeout=None)


def _make_notes_view() -> discord.ui.LayoutView:
    """利用上の注意事項ボード（赤アクセント）。"""

    class NotesView(discord.ui.LayoutView):
        container = discord.ui.Container(
            discord.ui.TextDisplay("**ExpressionEditorSystem**"),
            _logo_gallery(),
            discord.ui.TextDisplay(SYSTEM_DESC),
            discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
            discord.ui.TextDisplay(
                "## 🚫 利用上の注意\n"
                "EESを利用する際は以下の注意事項に注意して操作してください。\n"
                "- サーバールールに厳守すること\n"
                "- 原則運営以外に教えないこと\n"
                "- 削除時は最善の注意を払うこと\n"
                "- 登録ルールに従った名前にすること\n"
                "- わかりやすい名前にすること\n"
                "- 不適切な画像や音楽は使用しないこと"
            ),
            discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
            discord.ui.ActionRow(_BackToMainButton()),
            accent_colour=discord.Colour.from_str("#ed4245"),   # 赤
        )

    return NotesView(timeout=None)


def _make_guide_view() -> discord.ui.LayoutView:
    """利用方法ガイドボード（緑アクセント）。YouTube URL は .env から。"""

    class GuideView(discord.ui.LayoutView):
        container = discord.ui.Container(
            discord.ui.TextDisplay("**ExpressionEditorSystem**"),
            _logo_gallery(),
            discord.ui.TextDisplay(SYSTEM_DESC),
            discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
            discord.ui.TextDisplay(
                f"## 📽 利用方法ガイド\n"
                f"以下のYouTubeリンクをタップすることでガイド動画を見ることができます。\n\n"
                f"{YOUTUBE_URL}"
            ),
            discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
            discord.ui.ActionRow(_BackToMainButton()),
            accent_colour=discord.Colour.from_str("#57f287"),   # 緑
        )

    return GuideView(timeout=None)


def _make_emoji_editor_view(
    emoji_count: int,
    anime_count: int,
    emoji_max: int,
    anime_max: int,
) -> discord.ui.LayoutView:
    """絵文字エディタボード（緑アクセント）。"""

    class EmojiEditorView(discord.ui.LayoutView):
        container = discord.ui.Container(
            # ── ヘッダー ──
            discord.ui.TextDisplay("**EmojiEditor**"),
            discord.ui.TextDisplay(
                "絵文字を編集するモードです。命名規則に沿って絵文字をBot名義で追加・削除・置き換えが可能です。"
            ),
            discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
            # ── 現在の登録数 ──
            discord.ui.TextDisplay(
                f"現在登録済みの絵文字数：　{emoji_count}個/{emoji_max}個\n"
                f"アニメーション絵文字数：　{anime_count}個/{anime_max}個"
            ),
            # ── 命名規則リンク（横並び） ──
            discord.ui.Section(
                discord.ui.TextDisplay("命名規則を見る："),
                accessory=_EmojiRuleButton(),
            ),
            discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
            # ── 操作一覧ラベル ──
            discord.ui.TextDisplay("＋ 追加\nー 削除\n🔄 置き換え"),
            discord.ui.ActionRow(_EmojiActionSelect()),
            discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
            discord.ui.ActionRow(_BackToMainButton()),
            accent_colour=discord.Colour.from_str("#57f287"),   # 緑
        )

    return EmojiEditorView(timeout=None)


def _make_sticker_editor_view(
    sticker_count: int,
    anime_count: int,
    sticker_max: int,
    anime_max: int,
) -> discord.ui.LayoutView:
    """ステッカーエディタボード（青アクセント）。"""

    class StickerEditorView(discord.ui.LayoutView):
        container = discord.ui.Container(
            discord.ui.TextDisplay("**StickerEditor**"),
            discord.ui.TextDisplay(
                "ステッカーを編集するモードです。命名規則に沿って絵文字をBot名義で追加・削除・置き換えが可能です。"
            ),
            discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
            discord.ui.TextDisplay(
                f"現在登録済みのステッカー数：　{sticker_count}個/{sticker_max}個\n"
                f"アニメーションステッカー数：　{anime_count}個/{anime_max}個"
            ),
            discord.ui.Section(
                discord.ui.TextDisplay("命名規則を見る："),
                accessory=_EmojiRuleButton(),
            ),
            discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
            discord.ui.TextDisplay("＋ 追加\nー 削除\n🔄 置き換え"),
            discord.ui.ActionRow(_StickerActionSelect()),
            discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
            discord.ui.ActionRow(_BackToMainButton()),
            accent_colour=discord.Colour.from_str("#5865f2"),   # Discord ブルー
        )

    return StickerEditorView(timeout=None)


def _make_sb_editor_view(sb_count: int, sb_max: int) -> discord.ui.LayoutView:
    """サウンドボードエディタボード（紫アクセント）。"""

    class SBEditorView(discord.ui.LayoutView):
        container = discord.ui.Container(
            discord.ui.TextDisplay("**SoundBoardEditor**"),
            discord.ui.TextDisplay(
                "サウンドボードを編集するモードです。命名規則に沿って絵文字をBot名義で追加・削除・置き換えが可能です。"
            ),
            discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
            discord.ui.TextDisplay(
                f"現在登録済みのサウンドボード数：　{sb_count}個/{sb_max}個"
            ),
            discord.ui.Section(
                discord.ui.TextDisplay("命名規則を見る："),
                accessory=_EmojiRuleButton(),
            ),
            discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
            discord.ui.TextDisplay("＋ 追加\nー 削除\n🔄 置き換え"),
            discord.ui.ActionRow(_SBActionSelect()),
            discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
            discord.ui.ActionRow(_BackToMainButton()),
            accent_colour=discord.Colour.from_str("#9b59b6"),   # 紫
        )

    return SBEditorView(timeout=None)


# ────────────────────────────────────────────────────────────────────────────
# Cog
# ────────────────────────────────────────────────────────────────────────────

class ExpressionEditorCog(commands.Cog, name="ExpressionEditor"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    # ── on_ready: 永続 View の登録 ───────────────────────────────────────
    # Bot 再起動後もボタン・セレクトが反応するよう、全 custom_id を登録する。
    # ファクトリ関数はダミー値で呼び出す（guild データは callback 時に取得）。

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        self.bot.add_view(_make_main_view())
        self.bot.add_view(_make_notes_view())
        self.bot.add_view(_make_guide_view())
        self.bot.add_view(_make_emoji_editor_view(0, 0, 50, 50))
        self.bot.add_view(_make_sticker_editor_view(0, 0, 5, 5))
        self.bot.add_view(_make_sb_editor_view(0, 8))

    # ── !ees コマンド ─────────────────────────────────────────────────────

    @commands.command(name="ees", aliases=["EES"])
    async def ees(self, ctx: commands.Context) -> None:
        """ExpressionEditorSystem を起動します（CIロール限定）。"""

        # 権限チェック
        if not _has_ci_role(ctx.author):
            await ctx.reply(
                "⛔ このコマンドは運営メンバー（CIロール所持者）限定です。",
                mention_author=False,
            )
            return

        # 画像ファイル存在確認
        if not os.path.exists(IMAGE_PATH):
            await ctx.reply(
                f"⚠️ ロゴ画像が見つかりません: `{IMAGE_PATH}`\n"
                "`assets/main/` に EES ロゴ画像（`ees_logo.png`）を配置してください。",
                mention_author=False,
            )
            return

        try:
            file = discord.File(IMAGE_PATH, filename=IMAGE_FILENAME)
            await ctx.send(view=_make_main_view(), file=file)
        except Exception as e:
            traceback.print_exc()
            await ctx.reply(
                f"```\n{type(e).__name__}: {e}\n```",
                mention_author=False,
            )


# ────────────────────────────────────────────────────────────────────────────
# setup
# ────────────────────────────────────────────────────────────────────────────

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ExpressionEditorCog(bot))
