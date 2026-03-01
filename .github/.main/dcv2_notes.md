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

### ❌ エラー6: `400 Bad Request (error code: 50006): Cannot send an empty message`

**原因:** Component v2（LayoutView）のメッセージには Discord API に **IS_COMPONENTS_V2 フラグ**を明示する必要がある。  
フラグなしで送ると「空メッセージ」として弾かれる。

また、discord.py 2.6.4 の `Messageable.send()` には `flags` 引数が存在しないため、  
**`bot.http.request` で直接 Discord API を叩く**必要がある。

```python
# ❌ send() に flags は使えない（2.6.4 では未実装）
await ch.send(view=MyView(), flags=discord.MessageFlags(components_v2=True))

# ✅ HTTP 直送で IS_COMPONENTS_V2 フラグ（1 << 15）を付ける
await bot.http.request(
    discord.http.Route("POST", "/channels/{channel_id}/messages", channel_id=ch.id),
    json={
        "flags": 1 << 15,
        "components": [...],  # Component v2 の JSON
    }
)
```

---

### ❌ エラー7: `400 Bad Request (error code: 50035): Invalid Form Body — 'content' cannot be used with IS_COMPONENTS_V2`

**原因:** IS_COMPONENTS_V2 フラグを付けたメッセージでは `content` フィールドが使えない。  
メンションをメッセージの `content` に入れようとするとこのエラーになる。

```python
# ❌ IS_COMPONENTS_V2 と content は併用不可
json={
    "flags": 1 << 15,
    "content": member.mention,  # ← これが弾かれる
    "components": [...],
}

# ✅ メンションは Container 内の TextDisplay に入れる
{"type": 10, "content": f"{member.mention}さん、ようこそ！"}
```

---

### ❌ エラー8: `to_components()` が空リストを返す

**原因:** `LayoutView` の `container` はクラス変数として定義しなければ内部に登録されない。  
`__init__` 内で `self.container = ...` と書いてもメタクラスの処理タイミング上、  
永遠に拾われず `to_components()` が `[]` を返す。

```python
# ❌ インスタンス変数は無視される
class MyView(discord.ui.LayoutView):
    def __init__(self, text: str):
        super().__init__(timeout=None)
        self.container = discord.ui.Container(...)  # ← to_components() が [] になる
```

**対策A: ファクトリ関数でクラスごと動的生成する（LayoutView を使う場合）**

```python
# ✅
def make_view(text: str) -> discord.ui.LayoutView:
    class MyView(discord.ui.LayoutView):
        container = discord.ui.Container(
            discord.ui.TextDisplay(text),
        )
    return MyView(timeout=None)
```

**対策B: Component v2 の JSON を直接組み立てて HTTP 送信する（動的データが多い場合に推奨）**

```python
# ✅ JSON 直送方式（動的コンテンツと相性が良い）
def build_components_json(text: str) -> list:
    return [
        {
            "type": 17,  # Container
            "components": [
                {"type": 10, "content": text},  # TextDisplay
            ],
        }
    ]

await bot.http.request(
    discord.http.Route("POST", "/channels/{channel_id}/messages", channel_id=ch.id),
    json={"flags": 1 << 15, "components": build_components_json("テキスト")},
)
```

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

## Component v2 JSON 直送パターン（動的コンテンツ推奨）

動的コンテンツ（メンション、多言語テキスト、ランダム色など）を扱う場合は  
LayoutView を使わず **JSON を直接組み立てて `bot.http.request` で送る**方が素直。

### コンポーネントの type 番号一覧

| type | コンポーネント | 備考 |
|---|---|---|
| 1 | ActionRow | ボタン・セレクトをまとめる行 |
| 2 | Button | style: 5 = リンクボタン |
| 3 | StringSelect | セレクトメニュー |
| 9 | Section | TextDisplay + 右端に accessory（ボタン等） |
| 10 | TextDisplay | Markdown テキスト |
| 12 | MediaGallery | 画像表示 |
| 14 | Separator | spacing: 1=small / 2=large |
| 17 | Container | Embed 相当のコンテナ |

### Section（テキスト右端にボタンを置く）

```python
{
    "type": 9,  # Section
    "components": [
        {"type": 10, "content": "📕 ルールはこちら:"},
    ],
    "accessory": {
        "type": 2, "style": 5,
        "label": "RULES",
        "url": "https://discord.com/channels/...",
    },
}
```

### MediaGallery（画像表示）

```python
{
    "type": 12,
    "items": [{"media": {"url": "attachment://filename.png"}}],
}
```

### 画像付きメッセージの multipart 送信

```python
form = aiohttp.FormData()
form.add_field(
    "payload_json",
    json.dumps({
        "flags": 1 << 15,
        "attachments": [{"id": 0, "filename": "card.png"}],
        "components": build_components_json(...),
    }),
    content_type="application/json",
)
form.add_field(
    "files[0]",
    img_bytes,          # bytes
    filename="card.png",
    content_type="image/png",
)

await bot.http.request(
    discord.http.Route("POST", "/channels/{channel_id}/messages", channel_id=ch.id),
    data=form,
)
```

---

## 言語切り替え時の状態引き継ぎ

言語切り替えで PATCH するとき、初回送信時に埋め込んだ情報（メンション・accent_color・添付画像）を  
**既存メッセージの raw JSON から取得して引き継ぐ**必要がある。

```python
# GET でメッセージの生 JSON を取得
msg_data = await interaction.client.http.request(
    discord.http.Route(
        "GET",
        "/channels/{channel_id}/messages/{message_id}",
        channel_id=interaction.channel_id,
        message_id=interaction.message.id,
    )
)

# accent_color を取得
accent = msg_data["components"][0].get("accent_color")

# TextDisplay 内の <@userid> を正規表現で抽出
import re
for comp in msg_data["components"][0].get("components", []):
    if comp.get("type") == 10:
        match = re.search(r"<@!?\d+>", comp.get("content", ""))
        if match:
            mention = match.group(0)
            break

# 添付画像 URL を取得
card_url = interaction.message.attachments[0].url if interaction.message.attachments else None
```

---

## 永続化（Bot再起動後もボタンを動かす）

Component v2 を JSON 直送で送った場合、`LayoutView` はメッセージ送信に使わなくても  
**`add_view` のために `ui.View` サブクラスが必要**。

```python
class PersistentSelectView(ui.View):
    """add_view 登録専用。コンポーネントの callback を有効にするためだけに存在する。"""
    def __init__(self, guild_id: int):
        super().__init__(timeout=None)
        self.add_item(GuildLanguageSelect(guild_id))  # callback を持つ Select を登録
```

```python
@commands.Cog.listener()
async def on_ready(self) -> None:
    for guild in self.bot.guilds:
        self.bot.add_view(PersistentSelectView(guild.id))
```

### 永続化の注意点

| 注意点 | 内容 |
|---|---|
| `custom_id` は一意にする | 同じBotの別Viewと重複するとどちらが反応するか不定 |
| `custom_id` は変えない | 変えると既存のメッセージのボタンが反応しなくなる |
| `timeout=None` 必須 | デフォルトは180秒でタイムアウトする |
| `on_ready` で `add_view` | 起動時に必ず登録しないと再起動後に反応しない |
| JSON 直送の場合も `add_view` は必要 | 送信は HTTP 直送でも callback 受け取りには `add_view` が必要 |
| `add_view` に `message_id` を渡すと限定的になる | 特定メッセージのみ反応させたい場合に使う |

---

## 通常の View との構造比較

| | 通常の `View` | `LayoutView` |
|---|---|---|
| ボタン追加 | `@discord.ui.button` デコレータ | `Button` をサブクラス化して `ActionRow` に入れる |
| セレクト追加 | `@discord.ui.select` デコレータ | `Select` をサブクラス化して `ActionRow` に入れる |
| レイアウト | Discordが自動配置 | `Container` / `TextDisplay` / `Separator` で手動構成 |
| 送信方法 | `ctx.send(view=view)` | `bot.http.request` で JSON 直送（flags 必須） |
| Embed との共存 | `ctx.send(embed=embed, view=view)` | `Container` が Embed 相当のため不要（同時使用不可） |
| content フィールド | 使用可能 | IS_COMPONENTS_V2 フラグと併用不可 |
| 動的データの渡し方 | `__init__` に引数を渡す | ファクトリ関数 or JSON 直送 |
| cog の保持 | そのまま `self._cog = cog` でOK | `NoCopy` ミックスインが必要 |

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
