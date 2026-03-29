# cogs/systems/ees/expression_editor.py
# ExpressionEditorSystem (EES) — discord.py 2.6.4 / Components V2 LayoutView
# ============================================================================
#
# .env に以下を設定してください:
#   CI_ROLE_ID      = 運営ロールのID（0 = 全員許可）
#   EES_YOUTUBE_URL = ガイド動画の YouTube URL
#
# ロゴ画像  : assets/main/ees_logo.png
# ルール JSON: data_public/ess/emojirules.json
#              data_public/ess/stickerrules.json
#              data_public/ess/sbrules.json
# ============================================================================

from __future__ import annotations

import json
import os
import traceback
from pathlib import Path
from typing import Any

import discord
from discord.ext import commands

# ── .env 設定値 ────────────────────────────────────────────────────────────

CI_ROLE_ID: int  = int(os.getenv("CI_ROLE_ID", "0"))
YOUTUBE_URL: str = os.getenv("EES_YOUTUBE_URL", "https://www.youtube.com/watch?v=AAAAAA")

IMAGE_PATH: str     = "assets/main/ees_logo.png"
IMAGE_FILENAME: str = "ees_logo.png"

SYSTEM_DESC: str = (
    "ExpressionEditorSystem(EES)は絵文字・ステッカー・サウンドボードを"
    "簡易的に編集可能な運営メンバー限定のシステムです。"
)

# ルール JSON パス
_RULES_PATH: dict[str, str] = {
    "emoji":   "data_public/ess/emojirules.json",
    "sticker": "data_public/ess/stickerrules.json",
    "sb":      "data_public/ess/sbrules.json",
}

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
# cog / bot を間接的に保持するコンポーネントには必ずこのミックスインを付ける。

class NoCopy:
    def __deepcopy__(self, memo):
        return self


# ── ロゴ画像ブロック ────────────────────────────────────────────────────────

def _logo_gallery():
    return discord.ui.Section(
        discord.ui.TextDisplay("**ExpressionEditorSystem**"),
        accessory=discord.ui.Thumbnail(media=f"attachment://{IMAGE_FILENAME}"),
    )


# ── JSON ルール読み込み ─────────────────────────────────────────────────────

def _load_rules_json(path: str) -> dict[str, Any]:
    """
    ルール JSON を読み込んで返す。
    ファイルが存在しない・不正な場合はフォールバックデータを返す。
    """
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            "color": "#ffffff",
            "hide": True,
            "content": [
                {"type": "title", "text": "ルールファイルが見つかりません"},
                {"type": "des",   "text": f"`{path}` が存在しません。\n管理者に連絡してください。"},
            ],
        }
    except json.JSONDecodeError as e:
        return {
            "color": "#ed4245",
            "hide": False,
            "content": [
                {"type": "title", "text": "JSONパースエラー"},
                {"type": "des",   "text": f"`{path}` の書式が不正です。\n```\n{e}\n```"},
            ],
        }


def _build_rule_components(data: dict[str, Any]) -> list:
    """
    JSON の content 配列を discord.py コンポーネントのリストに変換する。

    対応する type:
      "title" → TextDisplay(**太字**)
      "des"   → TextDisplay（Markdown そのまま）
      "lineL" → Separator(large)
      "lineS" → Separator(small)

    注意: content 内ではコンポーネント系（Button, Select）は使用禁止。
    戻るボタン一式（Separator large + ActionRow）は呼び出し元が付け足す。
    """
    components: list = []
    for i, item in enumerate(data.get("content", [])):
        t = item.get("type", "")
        if t == "title":
            text = item.get("text", "")
            components.append(discord.ui.TextDisplay(f"**{text}**"))
        elif t == "des":
            # 複数 des が存在してもリスト上は別要素なので重複しない
            text = item.get("text", "")
            components.append(discord.ui.TextDisplay(text))
        elif t == "lineL":
            components.append(
                discord.ui.Separator(spacing=discord.SeparatorSpacing.large)
            )
        elif t == "lineS":
            components.append(
                discord.ui.Separator(spacing=discord.SeparatorSpacing.small)
            )
        # 未知の type は無視（将来の拡張に備えて警告だけ出す）
        else:
            print(f"[EES] 未知の type: '{t}' (index={i}) in {data}")
    return components


# ────────────────────────────────────────────────────────────────────────────
# ボタン定義
# ────────────────────────────────────────────────────────────────────────────

# ── メインボード用 ──────────────────────────────────────────────────────────

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


# ── 注意事項・ガイド → メイン に戻るボタン ──────────────────────────────────

class _BackToMainButton(NoCopy, discord.ui.Button):
    """注意事項・ガイド共通の「戻る」ボタン（メインボードに戻る）。"""
    def __init__(self):
        super().__init__(
            label="戻る",
            emoji="◀",
            style=discord.ButtonStyle.secondary,
            custom_id="ees_back_to_main_btn",
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


# ── エディタ → メイン に戻るボタン（エディタ内の「戻る」） ──────────────────

class _BackEditorToMainButton(NoCopy, discord.ui.Button):
    """各エディタ画面からメインボードに戻るボタン。"""
    def __init__(self):
        super().__init__(
            label="戻る",
            emoji="◀",
            style=discord.ButtonStyle.secondary,
            custom_id="ees_editor_back_btn",
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


# ── ルールボタン（エディタ → 命名規則ビューへ）─────────────────────────────
# 各エディタで別の custom_id を持つことで、ルールビューの back ボタンが
# どのエディタに戻ればよいかを判別できる。

class _EmojiRuleButton(NoCopy, discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="命名時のルール",
            emoji="📌",
            style=discord.ButtonStyle.danger,
            custom_id="ees_emoji_rule_btn",
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        try:
            view = _make_rule_view("emoji")
            await interaction.response.edit_message(view=view, attachments=[])
        except Exception as e:
            traceback.print_exc()
            await interaction.response.send_message(f"エラー: {e}", ephemeral=True)


class _StickerRuleButton(NoCopy, discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="命名時のルール",
            emoji="📌",
            style=discord.ButtonStyle.danger,
            custom_id="ees_sticker_rule_btn",
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        try:
            view = _make_rule_view("sticker")
            await interaction.response.edit_message(view=view, attachments=[])
        except Exception as e:
            traceback.print_exc()
            await interaction.response.send_message(f"エラー: {e}", ephemeral=True)


class _SBRuleButton(NoCopy, discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="命名時のルール",
            emoji="📌",
            style=discord.ButtonStyle.danger,
            custom_id="ees_sb_rule_btn",
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        try:
            view = _make_rule_view("sb")
            await interaction.response.edit_message(view=view, attachments=[])
        except Exception as e:
            traceback.print_exc()
            await interaction.response.send_message(f"エラー: {e}", ephemeral=True)


# ── ルールビュー → 各エディタ に戻るボタン ──────────────────────────────────

class _BackRuleToEditorButton(discord.ui.Button):
    """
    ルールビューからエディタに戻るボタン。
    editor_type: "emoji" | "sticker" | "sb"

    cog / bot を保持しないため NoCopy 不要。
    コールバック内でギルドデータを再取得してエディタビューを再構築する。
    """

    def __init__(self, editor_type: str):
        self._editor_type = editor_type
        super().__init__(
            label="戻る",
            emoji="◀",
            style=discord.ButtonStyle.secondary,
            custom_id=f"ees_rule_back_{editor_type}",
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild
        try:
            view = _build_editor_view(guild, self._editor_type)
            await interaction.response.edit_message(view=view, attachments=[])
        except Exception as e:
            traceback.print_exc()
            await interaction.response.send_message(f"エラー: {e}", ephemeral=True)


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
        # セレクト value → editor_type の変換
        _val_map = {"emoji": "emoji", "sticker": "sticker", "soundboard": "sb"}
        editor_type = _val_map.get(choice, "emoji")

        try:
            view = _build_editor_view(guild, editor_type)
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
# エディタビュー構築ヘルパー（カテゴリセレクト・ルールback 共用）
# ────────────────────────────────────────────────────────────────────────────

def _build_editor_view(guild: discord.Guild, editor_type: str) -> discord.ui.LayoutView:
    """
    guild からリアルタイムのデータを取得し、対応するエディタビューを生成する。
    editor_type: "emoji" | "sticker" | "sb"
    """
    if editor_type == "emoji":
        normal = len([e for e in guild.emojis if not e.animated])
        anime  = len([e for e in guild.emojis if e.animated])
        limit  = guild.emoji_limit
        return _make_emoji_editor_view(normal, anime, limit, limit)

    elif editor_type == "sticker":
        limit = _STICKER_LIMITS.get(guild.premium_tier, 5)
        _anim = {
            discord.StickerFormatType.apng,
            discord.StickerFormatType.lottie,
            discord.StickerFormatType.gif,
        }
        stickers = guild.stickers
        normal   = len([s for s in stickers if s.format not in _anim])
        anime    = len([s for s in stickers if s.format in _anim])
        return _make_sticker_editor_view(normal, anime, limit, limit)

    else:  # "sb"
        sounds = getattr(guild, "soundboard_sounds", [])
        count  = len(sounds)
        return _make_sb_editor_view(count, 8)


# ────────────────────────────────────────────────────────────────────────────
# View ファクトリ関数
#
# LayoutView の container はメタクラスがクラス定義時にスキャンする「クラス変数」
# でなければならない。動的な値を埋め込むため、ファクトリ関数内でクラスを
# 毎回定義するパターンを使う（dcv2_notes.md ファクトリ関数パターン参照）。
# ────────────────────────────────────────────────────────────────────────────

def _make_main_view() -> discord.ui.LayoutView:
    """メインボード。"""

    class MainView(discord.ui.LayoutView):
        container = discord.ui.Container(
            _logo_gallery(),
            discord.ui.TextDisplay(SYSTEM_DESC),
            discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
            discord.ui.Section(
                discord.ui.TextDisplay("利用上の注意事項："),
                accessory=_NotesButton(),
            ),
            discord.ui.Section(
                discord.ui.TextDisplay("利用方法ガイド："),
                accessory=_GuideButton(),
            ),
            discord.ui.Separator(spacing=discord.SeparatorSpacing.large),
            discord.ui.TextDisplay("以下のプルダウンから編集したいカテゴリーを選択してください。"),
            discord.ui.ActionRow(_CategorySelect()),
            accent_colour=discord.Colour.from_str("#00b0f4"),
        )

    return MainView(timeout=None)


def _make_notes_view() -> discord.ui.LayoutView:
    """利用上の注意事項ボード（赤アクセント）。"""

    class NotesView(discord.ui.LayoutView):
        container = discord.ui.Container(
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
            discord.ui.Separator(spacing=discord.SeparatorSpacing.large),
            discord.ui.ActionRow(_BackToMainButton()),
            accent_colour=discord.Colour.from_str("#ed4245"),
        )

    return NotesView(timeout=None)


def _make_guide_view() -> discord.ui.LayoutView:
    """利用方法ガイドボード（緑アクセント）。"""

    class GuideView(discord.ui.LayoutView):
        container = discord.ui.Container(
            _logo_gallery(),
            discord.ui.TextDisplay(SYSTEM_DESC),
            discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
            discord.ui.TextDisplay(
                "## 📽 利用方法ガイド\n"
                "以下のYouTubeリンクをタップすることでガイド動画を見ることができます。\n\n"
                f"{YOUTUBE_URL}"
            ),
            discord.ui.Separator(spacing=discord.SeparatorSpacing.large),
            discord.ui.ActionRow(_BackToMainButton()),
            accent_colour=discord.Colour.from_str("#57f287"),
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
            discord.ui.TextDisplay("**EmojiEditor**"),
            discord.ui.TextDisplay(
                "絵文字を編集するモードです。命名規則に沿って絵文字をBot名義で追加・削除・置き換えが可能です。"
            ),
            discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
            discord.ui.TextDisplay(
                f"現在登録済みの絵文字数：　{emoji_count}個/{emoji_max}個\n"
                f"アニメーション絵文字数：　{anime_count}個/{anime_max}個"
            ),
            discord.ui.Section(
                discord.ui.TextDisplay("命名規則を見る："),
                accessory=_EmojiRuleButton(),
            ),
            discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
            discord.ui.TextDisplay("＋ 追加\nー 削除\n🔄 置き換え"),
            discord.ui.ActionRow(_EmojiActionSelect()),
            discord.ui.Separator(spacing=discord.SeparatorSpacing.large),
            discord.ui.ActionRow(_BackEditorToMainButton()),
            accent_colour=discord.Colour.from_str("#57f287"),
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
                "ステッカーを編集するモードです。命名規則に沿ってステッカーをBot名義で追加・削除・置き換えが可能です。"
            ),
            discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
            discord.ui.TextDisplay(
                f"現在登録済みのステッカー数：　{sticker_count}個/{sticker_max}個\n"
                f"アニメーションステッカー数：　{anime_count}個/{anime_max}個"
            ),
            discord.ui.Section(
                discord.ui.TextDisplay("命名規則を見る："),
                accessory=_StickerRuleButton(),
            ),
            discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
            discord.ui.TextDisplay("＋ 追加\nー 削除\n🔄 置き換え"),
            discord.ui.ActionRow(_StickerActionSelect()),
            discord.ui.Separator(spacing=discord.SeparatorSpacing.large),
            discord.ui.ActionRow(_BackEditorToMainButton()),
            accent_colour=discord.Colour.from_str("#5865f2"),
        )

    return StickerEditorView(timeout=None)


def _make_sb_editor_view(sb_count: int, sb_max: int) -> discord.ui.LayoutView:
    """サウンドボードエディタボード（紫アクセント）。"""

    class SBEditorView(discord.ui.LayoutView):
        container = discord.ui.Container(
            discord.ui.TextDisplay("**SoundBoardEditor**"),
            discord.ui.TextDisplay(
                "サウンドボードを編集するモードです。命名規則に沿って音声をBot名義で追加・削除・置き換えが可能です。"
            ),
            discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
            discord.ui.TextDisplay(
                f"現在登録済みのサウンドボード数：　{sb_count}個/{sb_max}個"
            ),
            discord.ui.Section(
                discord.ui.TextDisplay("命名規則を見る："),
                accessory=_SBRuleButton(),
            ),
            discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
            discord.ui.TextDisplay("＋ 追加\nー 削除\n🔄 置き換え"),
            discord.ui.ActionRow(_SBActionSelect()),
            discord.ui.Separator(spacing=discord.SeparatorSpacing.large),
            discord.ui.ActionRow(_BackEditorToMainButton()),
            accent_colour=discord.Colour.from_str("#9b59b6"),
        )

    return SBEditorView(timeout=None)


def _make_rule_view(editor_type: str) -> discord.ui.LayoutView:
    """
    data_public/ess/<editor_type>rules.json を読み込み、
    LayoutView をその場で構築して返す。

    editor_type: "emoji" | "sticker" | "sb"

    JSON の content を上から順に TextDisplay / Separator に変換し、
    末尾に「Separator(large) + 戻るボタン」を自動付加する。
    コンポーネント系（Button, Select）は content 内で使用禁止。
    """
    json_path = _RULES_PATH[editor_type]
    data      = _load_rules_json(json_path)

    # ── メタ情報 ──────────────────────────────────────────────────────────
    color_str = data.get("color", "#ffffff")
    hide      = data.get("hide", False)
    # hide=True → accent_colour なし（ボーダー非表示）
    accent = None if hide else discord.Colour.from_str(color_str)

    # ── content → コンポーネントリスト ────────────────────────────────────
    components = _build_rule_components(data)

    # ── 末尾に戻るボタン一式を付加（JSON には書かない） ──────────────────
    # 画像スクリーンショットと同じく「Separator(large) + 灰色戻るボタン」
    components.append(discord.ui.Separator(spacing=discord.SeparatorSpacing.large))
    components.append(discord.ui.ActionRow(_BackRuleToEditorButton(editor_type)))

    # ── ファクトリパターンでクラス変数として container を定義 ─────────────
    class RuleView(discord.ui.LayoutView):
        container = discord.ui.Container(*components, accent_colour=accent)

    return RuleView(timeout=None)


# ────────────────────────────────────────────────────────────────────────────
# Cog
# ────────────────────────────────────────────────────────────────────────────

class ExpressionEditorCog(commands.Cog, name="ExpressionEditor"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        # ── 全 View を永続登録 ──────────────────────────────────────────
        # ダミー値で各ビューを生成して custom_id を bot に認識させる。
        # 実際のギルドデータは各コールバック時に取得する。
        self.bot.add_view(_make_main_view())
        self.bot.add_view(_make_notes_view())
        self.bot.add_view(_make_guide_view())
        self.bot.add_view(_make_emoji_editor_view(0, 0, 50, 50))
        self.bot.add_view(_make_sticker_editor_view(0, 0, 5, 5))
        self.bot.add_view(_make_sb_editor_view(0, 8))
        self.bot.add_view(_make_rule_view("emoji"))
        self.bot.add_view(_make_rule_view("sticker"))
        self.bot.add_view(_make_rule_view("sb"))

    @commands.command(name="ees", aliases=["EES"])
    async def ees(self, ctx: commands.Context) -> None:
        """ExpressionEditorSystem を起動します（CIロール限定）。"""

        if not _has_ci_role(ctx.author):
            await ctx.reply(
                "⛔ このコマンドは運営メンバー（CIロール所持者）限定です。",
                mention_author=False,
            )
            return

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


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ExpressionEditorCog(bot))
