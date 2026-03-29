# ExpressionEditorSystem (EES)

絵文字・ステッカー・サウンドボードを簡易的に編集できる運営メンバー限定の Discord Bot システムです。  
discord.py **2.6.4** / **Components V2 (LayoutView)** ベースで実装されています。

---

## ファイル構成

```
cogs/
  ees/
    __init__.py
    expression_editor.py     ← メイン Cog
assets/
  main/
    ees_logo.png             ← EES ロゴ画像（要配置）
data_public/
  ess/
    emojirules.json          ← 絵文字 命名規則
    stickerrules.json        ← ステッカー 命名規則
    sbrules.json             ← サウンドボード 命名規則
.env                         ← 設定値
```

---

## セットアップ

### 1. 画像を配置する

`assets/main/ees_logo.png` にロゴ画像を配置してください。

### 2. .env を設定する

```env
CI_ROLE_ID=123456789012345678   # 運営ロールの ID（0 = 全員許可）
EES_YOUTUBE_URL=https://www.youtube.com/watch?v=XXXXXXX
```

| 変数名 | 説明 | デフォルト |
|--------|------|-----------|
| `CI_ROLE_ID` | 運営ロールの ID。`0` にすると全員使用可 | `0` |
| `EES_YOUTUBE_URL` | ガイド動画の YouTube URL | サンプル URL |

### 3. Cog を読み込む

```python
await bot.load_extension("cogs.ees.expression_editor")
```

---

## 使い方

```
!ees
```

CI_ROLE_ID で指定したロールを持つメンバーのみ使用可能です。

---

## 画面遷移

```
メインボード
├── [🚫 注意事項]        → 注意事項ボード     → [◀ 戻る] → メイン
├── [📽 ガイド動画を見る] → ガイドボード       → [◀ 戻る] → メイン
└── [カテゴリ選択]
    ├── 🎨 絵文字を編集
    │   ├── [📌 命名時のルール] → 絵文字ルールビュー → [◀ 戻る] → 絵文字エディタ
    │   └── [◀ 戻る]           → メイン
    ├── 📎 ステッカーを編集
    │   ├── [📌 命名時のルール] → ステッカールールビュー → [◀ 戻る] → ステッカーエディタ
    │   └── [◀ 戻る]           → メイン
    └── 🎵 サウンドボードを編集
        ├── [📌 命名時のルール] → サウンドボードルールビュー → [◀ 戻る] → サウンドボードエディタ
        └── [◀ 戻る]           → メイン
```

カテゴリ選択後・各画面遷移は **最初に送信したメッセージを `edit_message` で上書き** します。

---

## ルール JSON の書き方

### ファイル一覧

| ファイル | 対応エディタ |
|----------|-------------|
| `data_public/ess/emojirules.json` | 絵文字 |
| `data_public/ess/stickerrules.json` | ステッカー |
| `data_public/ess/sbrules.json` | サウンドボード |

---

### JSON 構造

```json
{
  "color": "#57f287",
  "hide": false,
  "content": [
    { "type": "title", "text": "ここにタイトル" },
    { "type": "des",   "text": "ここに本文（Markdown 使用可）" },
    { "type": "lineL" },
    { "type": "des",   "text": "続きの本文" },
    { "type": "lineS" }
  ]
}
```

---

### トップレベルキー

| キー | 型 | 説明 |
|------|----|------|
| `color` | string | アクセントカラー（16進カラーコード）例: `"#57f287"` |
| `hide` | bool | `true` にするとアクセントボーダーを非表示にする |
| `content` | array | 表示するコンポーネントを **上から順に** 並べる |

---

### content の各 type

| type | 必須キー | 説明 | 対応コンポーネント |
|------|----------|------|------------------|
| `"title"` | `text` | **太字** で表示されるタイトル | `TextDisplay(**text**)` |
| `"des"` | `text` | 本文テキスト。Markdown（`##` `- ` `` ` `` など）が使用可能 | `TextDisplay(text)` |
| `"lineL"` | なし | 大きな区切り線 | `Separator(large)` |
| `"lineS"` | なし | 小さな区切り線 | `Separator(small)` |

> **注意:**
> - `content` 内でボタン・セレクトなどのコンポーネントは使用禁止（サポート外）。
> - `"des"` キーは同じオブジェクト内に複数書けません（JSON の制約）。  
>   複数の段落は **別々のオブジェクト** として並べてください（例を参照）。
> - 戻るボタン（`Separator large` + 灰色の `◀ 戻る` ボタン）は JSON に書かなくても自動で末尾に付加されます。

---

### content の読み込み順

`content` 配列は **上から順番に** LayoutView のコンポーネントとして展開されます。

```
content[0] → 最上部
content[1] → その下
content[2] → さらにその下
  …
（自動）Separator(large) + ◀ 戻るボタン → 最下部
```

---

### 記述例（emojirules.json）

```json
{
  "color": "#57f287",
  "hide": false,
  "content": [
    { "type": "title", "text": "絵文字 命名規則" },
    { "type": "des",   "text": "絵文字を登録する際は以下の命名規則に従ってください。" },
    { "type": "lineL" },
    { "type": "des",   "text": "### 📌 基本ルール\n- 半角英数字・アンダースコアのみ\n- 最大32文字以内" },
    { "type": "lineS" },
    { "type": "des",   "text": "### ✅ 命名例\n`iroha_smile` `kazama_wave`" },
    { "type": "lineS" },
    { "type": "des",   "text": "### ❌ 使用禁止\n- 不適切・差別的な表現\n- 他サーバーのブランド名" }
  ]
}
```

この JSON は以下の順に展開されます:

```
[title]   → **絵文字 命名規則**
[des]     → 絵文字を登録する際は...
[lineL]   → ────────────────────（大）
[des]     → ### 📌 基本ルール...
[lineS]   → ────────────────────（小）
[des]     → ### ✅ 命名例...
[lineS]   → ────────────────────（小）
[des]     → ### ❌ 使用禁止...
（自動）  → ────────────────────（大）
（自動）  → ◀ 戻る
```

---

## 注意事項

### MediaGallery について

ロゴ画像に `discord.ui.MediaGallery` を使用しています。  
`AttributeError: module 'discord.ui' has no attribute 'MediaGallery'` が出た場合は、  
`_logo_gallery()` 関数を以下に差し替えてください:

```python
def _logo_gallery():
    return discord.ui.Section(
        discord.ui.TextDisplay("**ExpressionEditorSystem**"),
        accessory=discord.ui.Thumbnail(media=f"attachment://{IMAGE_FILENAME}"),
    )
```

その際、各 View 先頭の `TextDisplay("**ExpressionEditorSystem**")` 行を削除してください（重複するため）。

### Bot 再起動後の動作（永続化）

`on_ready` で `bot.add_view()` を呼び出しているため、再起動後もボタン・セレクトが動作します。  
**`custom_id` は変更しないでください**（変更すると既存メッセージのボタンが反応しなくなります）。
