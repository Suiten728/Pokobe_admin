# discord.py 2.6.4 — Component v2 (LayoutView) 注意点まとめ

---

## 今回発生したエラー一覧

### ❌ エラー1: `TypeError: 'module' object is not callable`

**原因:** ファイル名にハイフン（`-`）が入っていた。

```
cogs/test/dcv2-test.py  ← ❌
```

Python はモジュール名にハイフンを使えない。  
`cogs.test.dcv2-test` を import しようとすると `dcv2 - test`（引き算）として解釈される。

**対策:** ファイル名はアンダースコアのみ使う。

```
cogs/test/dcv2_test.py  ← ✅
```

---

### ❌ エラー2: `TypeError: Separator.__init__() got an unexpected keyword argument 'divider'`

**原因:** `discord.py 2.6.4` の `Separator` に `divider` 引数は存在しない。

```python
# ❌
discord.ui.Separator(divider=True)

# ✅ spacing のみ使用可能
discord.ui.Separator(spacing=discord.SeparatorSpacing.large)
discord.ui.Separator(spacing=discord.SeparatorSpacing.small)
```

**`SeparatorSpacing` の値:**

| 値 | 間隔 |
|---|---|
| `SeparatorSpacing.small` | 小（デフォルト） |
| `SeparatorSpacing.large` | 大 |

---

### ❌ エラー3: `AttributeError: module 'discord.ui' has no attribute 'string_select'`

**原因:** `LayoutView` では通常の `View` で使えるデコレータ構文（`@discord.ui.button` / `@discord.ui.string_select`）が使えない。

```python
# ❌ LayoutView では使えない
class MyView(discord.ui.LayoutView):
    @discord.ui.string_select(placeholder="選択", options=[...])
    async def callback(self, interaction, select): ...
```

**対策:** コンポーネントをサブクラス化して `callback` を定義し、`ActionRow` に入れる。

```python
# ✅ LayoutView での正しい書き方
class MySelect(discord.ui.Select):
    def __init__(self):
        super().__init__(placeholder="選択", options=[...])

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message("完了！", ephemeral=True)

class MyView(discord.ui.LayoutView):
    container = discord.ui.Container(
        discord.ui.ActionRow(MySelect()),
    )
```

---

### ❌ エラー4: `AttributeError: module 'discord.ui' has no attribute 'StringSelect'`

**原因:** `discord.ui.StringSelect` は discord.py のバージョンによって存在しない。

```python
# ❌
class MySelect(discord.ui.StringSelect): ...

# ✅ 2.6.4 では Select を使う
class MySelect(discord.ui.Select): ...
```

---

### ❌ エラー5: `TypeError: cannot pickle '_asyncio.Future' object`

**原因:** `LayoutView` は `__init__` 時に `container` のクラス変数を `deepcopy` する。  
コンポーネント（ボタン・セレクト）が `cog` への参照を持っている場合、  
`cog.bot` の内部に `asyncio.Future`（コピー不可能なオブジェクト）が含まれているためエラーになる。

```python
# ❌ cog を self._cog として持つボタンを container に入れると爆発する
class MyButton(discord.ui.Button):
    def __init__(self, cog):
        self._cog = cog  # ← bot を間接的に持つ
        super().__init__(label="ボタン")

class MyView(discord.ui.LayoutView):
    container = discord.ui.Container(
        discord.ui.ActionRow(MyButton(cog))  # ← deepcopy 時に死ぬ
    )
```

**対策:** `NoCopy` ミックスインを使って `deepcopy` をスキップする。

```python
# ✅
class NoCopy:
    def __deepcopy__(self, memo):
        return self  # deepcopy をスキップして自分自身を返す

class MyButton(NoCopy, discord.ui.Button):
    def __init__(self, cog):
        self._cog = cog
        super().__init__(label="ボタン")

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message("完了！", ephemeral=True)
```

`NoCopy` を継承したコンポーネントは `deepcopy` を素通りするため、  
`cog` や `bot` を持っていても問題なく動く。  
**cog を受け取るコンポーネントには必ず `NoCopy` を付ける。**

---

## LayoutView の正しい構造（テンプレート）

```python
import discord
from discord.ext import commands


# ── コンポーネント定義（サブクラスで callback を定義）──────────────

class MySelect(discord.ui.Select):
    def __init__(self):
        super().__init__(
            placeholder="選択してください",
            options=[
                discord.SelectOption(label="A", value="a"),
                discord.SelectOption(label="B", value="b"),
            ],
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(
            f"選択: {self.values[0]}", ephemeral=True
        )


class MyButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="ボタン", style=discord.ButtonStyle.primary)

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message("完了！", ephemeral=True)


# ── LayoutView 本体 ────────────────────────────────────────────────

class MyView(discord.ui.LayoutView):
    container = discord.ui.Container(
        discord.ui.TextDisplay("# タイトル"),
        discord.ui.Separator(spacing=discord.SeparatorSpacing.large),
        discord.ui.TextDisplay("説明文"),
        discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
        discord.ui.ActionRow(MySelect()),
        discord.ui.ActionRow(MyButton()),
        accent_colour=discord.Colour.blurple(),
    )


# ── Cog ───────────────────────────────────────────────────────────

class MyCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command(name="test")
    async def test(self, ctx: commands.Context) -> None:
        await ctx.send(view=MyView())


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MyCog(bot))
```

---

## 動的データを使う LayoutView（ファクトリ関数パターン）

`LayoutView` の `container` はクラス変数でなければならないため、  
**実行時に決まる値（channel_id、cog、ユーザー名など）を渡したい場合は、  
ファクトリ関数の中でクラスを定義してインスタンスを返す**のが正しいパターン。

```python
# ❌ インスタンス変数に container を入れても動かない
class MyView(discord.ui.LayoutView):
    def __init__(self, text: str):
        self.container = discord.ui.Container(  # NG：クラス変数でないと無視される
            discord.ui.TextDisplay(text),
        )
        super().__init__()

# ❌ super().__init__() より前に設定しても動かない（同じ理由）
class MyView(discord.ui.LayoutView):
    def __init__(self, text: str):
        self.container = discord.ui.Container(...)  # NG
        super().__init__()

# ✅ ファクトリ関数でクラスごと動的に生成する
def make_my_view(text: str):
    class MyView(discord.ui.LayoutView):
        container = discord.ui.Container(   # ← クラス変数として定義
            discord.ui.TextDisplay(text),   # ← 外側の変数をクロージャで参照
        )
    return MyView(timeout=300)
```

**なぜクラス変数でないといけないのか:**  
`LayoutView` はメタクラスの仕組みで**クラス定義の時点**で `container` をスキャンして  
コンポーネントを内部登録する。`self.container` はクラス定義後に追加されるため、  
タイミングに関わらず永遠に拾われない。

---

## 通常の View との構造比較

| | 通常の `View` | `LayoutView` |
|---|---|---|
| ボタン追加 | `@discord.ui.button` デコレータ | `Button` をサブクラス化して `ActionRow` に入れる |
| セレクト追加 | `@discord.ui.select` デコレータ | `Select` をサブクラス化して `ActionRow` に入れる |
| レイアウト | Discordが自動配置 | `Container` / `TextDisplay` / `Separator` で手動構成 |
| 送信方法 | `ctx.send(view=view)` | 同じ |
| Embed との共存 | `ctx.send(embed=embed, view=view)` | `Container` が Embed 相当のため不要（同時使用不可） |
| 動的データの渡し方 | `__init__` に引数を渡す | ファクトリ関数でクラスごと生成する |
| cog の保持 | そのまま `self._cog = cog` でOK | `NoCopy` ミックスインが必要 |

---

## 永続化（Bot再起動後もボタンを動かす）

通常 `View` はBot再起動すると反応しなくなる。永続化するには **`custom_id` を固定** して `bot.add_view()` を呼ぶ。

### ① custom_id を固定する

```python
class PersistButton(discord.ui.Button):
    def __init__(self):
        # custom_id を固定文字列にする（動的な値はNG）
        super().__init__(
            label="永続ボタン",
            style=discord.ButtonStyle.primary,
            custom_id="my_persistent_button",  # ← ここが重要
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message("永続ボタン動作！", ephemeral=True)


class PersistSelect(discord.ui.Select):
    def __init__(self):
        super().__init__(
            placeholder="永続セレクト",
            custom_id="my_persistent_select",  # ← ここが重要
            options=[
                discord.SelectOption(label="A", value="a"),
            ],
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(f"選択: {self.values[0]}", ephemeral=True)
```

### ② LayoutView に `timeout=None` を設定する

```python
class PersistView(discord.ui.LayoutView):
    # timeout=None にしないと再起動後に機能しない
    def __init__(self):
        super().__init__(timeout=None)

    container = discord.ui.Container(
        discord.ui.TextDisplay("# 永続ビュー"),
        discord.ui.ActionRow(PersistButton()),
        discord.ui.ActionRow(PersistSelect()),
    )
```

### ③ on_ready で bot.add_view() を呼ぶ

```python
class MyCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        # Bot起動時に永続Viewを登録する（送信は不要、登録だけでOK）
        self.bot.add_view(PersistView())

    @commands.command(name="persist")
    async def persist(self, ctx: commands.Context) -> None:
        await ctx.send(view=PersistView())
```

### 永続化の注意点

| 注意点 | 内容 |
|---|---|
| `custom_id` は一意にする | 同じBotの別Viewと重複するとどちらが反応するか不定 |
| `custom_id` は変えない | 変えると既存のメッセージのボタンが反応しなくなる |
| `timeout=None` 必須 | デフォルトは180秒でタイムアウトする |
| `on_ready` で `add_view` | 起動時に必ず登録しないと再起動後に反応しない |
| `add_view` に `message_id` を渡すと限定的になる | 特定メッセージのみ反応させたい場合に使う |

---

## よく使うコンポーネント一覧（2.6.4 対応）

```python
# テキスト表示（Markdown対応）
discord.ui.TextDisplay("# 見出し\n本文テキスト")

# 区切り線
discord.ui.Separator(spacing=discord.SeparatorSpacing.large)
discord.ui.Separator(spacing=discord.SeparatorSpacing.small)

# コンテナ（Embed相当）
discord.ui.Container(
    *children,
    accent_colour=discord.Colour.blurple(),  # 左端のアクセントカラー
)

# ボタンをまとめる行（1行に最大5つ）
discord.ui.ActionRow(Button1(), Button2(), Button3())

# セレクトメニュー（ActionRowに単体で入れる）
discord.ui.ActionRow(MySelect())
```

---

## エラーが無音で握りつぶされるケース

discord.py の `commands.command` は、コマンドハンドラ内で発生した例外を  
**デフォルトでは `on_command_error` に渡して処理する**。  
`on_command_error` が定義されていない場合は標準エラー出力に出るが、  
ロギングの設定や Bot フレームワーク次第では**コンソールに何も出ずに無音で失敗する**ことがある。

コマンドが呼ばれているのに何も起きない場合、まず `try/except` で明示的にキャッチして確認する。

```python
@commands.command(name="mycommand")
async def mycommand(self, ctx: commands.Context):
    try:
        # 処理
        await ctx.send(view=make_my_view(self, str(ctx.channel.id)))
    except Exception as e:
        import traceback
        traceback.print_exc()
        await ctx.send(f"```\n{type(e).__name__}: {e}\n```")
```

---

## ファイル名・モジュール名のルール

```
✅ 使える文字 : アルファベット、数字、アンダースコア（_）
❌ 使えない文字: ハイフン（-）、スペース、ドット（拡張子除く）

✅ dcv2.py
✅ dcv2_test.py
✅ my_cog_v2.py
❌ dcv2-test.py   ← ロード時に引き算として解釈されエラー
❌ my cog.py      ← スペース不可
```