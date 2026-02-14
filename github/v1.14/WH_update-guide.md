# Bot v1.14 アップデートガイド

## 新機能: Web Hook送信システム

### 概要
v1.14では、Discord Web Hookを使用したメッセージ転送システムが追加されました。
このシステムにより、運営スタッフが質問対応などを行う際に、事前に設定したWeb Hookの名前とアバターを使用してメッセージを送信できます。

### 主な特徴
- シンプルな対話型フロー（メッセージIDのみ入力）
- .envファイルでWeb Hook URLを一元管理
- Web Hookの名前、アバター、送信先チャンネルはDiscord UIで設定
- **即時メッセージ削除**: 各メッセージがすぐに削除されるため、チャンネルが常にクリーン
- メッセージIDの検証機能
- 確認画面による誤送信防止

---

## インストール手順

### 1. ファイルの配置
`webhook_sender.py` を Bot のディレクトリに配置してください。

```
your-bot/
├── main.py
├── .env               # ← Web Hook URL設定ファイル
├── webhook_sender.py  # ← 新規追加
└── cogs/
```

### 2. .envファイルの設定

プロジェクトのルートディレクトリに `.env` ファイルを作成し、Web Hook URLを設定します：

```env
# Discord Bot Token
DISCORD_TOKEN=your_discord_bot_token_here

# Web Hook URL（運営募集用など）
WEBHOOK_URL=https://discord.com/api/webhooks/1234567890/abcdefghijklmnopqrstuvwxyz
```

**⚠️ 重要:** `.env` ファイルは `.gitignore` に追加して、Gitにコミットしないようにしてください！

```.gitignore
.env
__pycache__/
*.pyc
```

### 3. Web Hookの作成と設定

#### Web Hookの作成手順

1. **送信先チャンネルでWeb Hookを作成**
   - 送信先にしたいチャンネルの設定を開く
   - 連携サービス → ウェブフック
   - 「新しいウェブフック」をクリック

2. **名前とアバターを設定**
   - 名前: 例）`運営質問担当`、`面接担当者` など
   - アバター: 運営用のアイコン画像をアップロード
   - これらの設定が送信時に使用されます

3. **Web Hook URLをコピー**
   - 「ウェブフックURLをコピー」をクリック
   - `.env` ファイルの `WEBHOOK_URL` に貼り付け

4. **保存**
   - 「変更を保存」をクリック

**重要:** Web Hookを作成したチャンネルが送信先になります。送信先を変更したい場合は、Discord UIでWeb Hookのチャンネルを変更してください。

#### Web Hookの送信先チャンネルを変更する方法

1. チャンネル設定 → 連携サービス → ウェブフック
2. 編集したいWeb Hookをクリック
3. 「チャンネル」ドロップダウンから新しい送信先を選択
4. 「変更を保存」

### 4. 必要なライブラリのインストール

以下のライブラリが必要です：

```bash
pip install discord.py aiohttp python-dotenv
```

requirements.txt に追加する場合：
```
discord.py>=2.0.0
aiohttp>=3.8.0
python-dotenv>=1.0.0
```

### 5. メインファイルへの統合

**main.py** に以下のコードを追加してください：

```python
import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

# .envファイルを読み込む
load_dotenv()

# Botの設定
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Cogのロード
async def load_extensions():
    await bot.load_extension('webhook_sender')

@bot.event
async def on_ready():
    await load_extensions()
    print(f'{bot.user} がログインしました')

# Botを起動
bot.run(os.getenv('DISCORD_TOKEN'))
```

---

## 使用方法

### 基本的な流れ

1. **コマンドの実行**
   ```
   WH送信
   ```
   → メッセージがすぐに削除され、「送信するメッセージIDを送信してください」と表示

2. **メッセージIDの入力**
   ```
   1234567890123456789
   ```
   → メッセージと案内文がすぐに削除され、確認画面が表示

3. **確認画面**
   ```
   以下の内容で送信します。送信しますか？
   
   📝 名前: `運営質問担当`
   🖼️ アバター: [URL]
   📢 送信先チャンネル: #質問チャンネル
   
   [はい] [いいえ]
   ```

4. **送信実行**
   - 「はい」ボタンをクリックすると送信されます
   - 「いいえ」ボタンでキャンセルできます
   - **どちらの場合も確認メッセージが削除されます**

### 即時メッセージ削除について

このシステムでは、以下のタイミングでメッセージが削除されます：

| アクション | 削除されるもの |
|-----------|---------------|
| 「WH送信」と入力 | → すぐに削除 |
| メッセージID入力 | → ユーザーのメッセージと前の案内文がすぐに削除 |
| 「はい」or「いいえ」 | → 確認画面が削除 |

**メリット:**
- ✅ チャンネルが常にクリーン
- ✅ プライバシー保護（IDが残らない）
- ✅ 複数人が同時使用しても混乱しない

**注意**: メッセージ削除には「メッセージを管理」権限が必要です。

### IDの取得方法

**メッセージIDの取得:**
1. Discord の設定 → 詳細設定 → 開発者モードをON
2. メッセージを右クリック → IDをコピー

---

## 運営募集での使用例

### シナリオ: 質問対応スタッフとしての使用

#### 準備
1. 質問受付チャンネルでWeb Hookを作成
2. 名前を「運営質問担当」、アバターに運営ロゴを設定
3. Web Hook URLを`.env`ファイルに設定

#### 実際の使用
1. 運営用チャンネルで応募者への返信メッセージを作成
2. そのメッセージのIDをコピー
3. 質問受付チャンネルで `WH送信` と入力（すぐ消える）
4. メッセージIDを入力（すぐ消える）
5. 確認画面で「はい」をクリック
6. → 「運営質問担当」名義で返信が送信される
7. すべてのメッセージが削除され、チャンネルはクリーンなまま

### 複数のWeb Hookを使い分ける場合

異なる用途で複数のWeb Hookを使用したい場合は、`.env` ファイルで複数設定できます：

```env
# 質問対応用
WEBHOOK_URL_QUESTIONS=https://discord.com/api/webhooks/111111/aaaaa

# 面接担当用
WEBHOOK_URL_INTERVIEW=https://discord.com/api/webhooks/222222/bbbbb

# 運営代表用
WEBHOOK_URL_ADMIN=https://discord.com/api/webhooks/333333/ccccc
```

この場合、`webhook_sender.py` を修正して、使用するWeb Hookを選択できるようにする必要があります。

---

## 技術的な仕組み

### Web Hookの管理

このシステムでは、Web Hookの設定（名前、アバター、送信先チャンネル）はすべてDiscord UIで管理します。Bot側では：

1. `.env` から Web Hook URL を読み込み
2. Discord APIでWeb Hookの情報（名前、アバター、チャンネル）を取得
3. 確認画面に表示
4. そのまま送信（チャンネル変更なし）

**送信先を変更したい場合:**
Discord UIでWeb Hookのチャンネル設定を変更してください。Bot側での変更は不要です。

### 即時削除の仕組み

各メッセージは受信直後に削除されます：

```python
# ユーザーのメッセージをすぐに削除
try:
    await message.delete()
except:
    pass

# 前のBotメッセージも削除
if "bot_message" in session:
    try:
        await session["bot_message"].delete()
    except:
        pass
```

これにより、チャンネルには最新の案内文または確認画面のみが表示されます。

---

## エラー対処

### よくあるエラー

**❌ 無効なメッセージIDです**
- 原因: 数字以外の文字が含まれている
- 対処: 数字のみで構成されたIDを入力してください
- メッセージは自動削除され、再入力を促されます

**⚠️ 警告: WEBHOOK_URLが.envファイルに設定されていません**
- 原因: `.env` ファイルに `WEBHOOK_URL` が設定されていない
- 対処: `.env` ファイルに `WEBHOOK_URL=...` を追加してください

**❌ 指定されたメッセージが見つかりませんでした**
- 原因: メッセージIDが間違っているか、Botがアクセスできない
- 対処: 
  - メッセージIDを確認
  - Botにメッセージ履歴を読む権限があるか確認

**❌ メッセージの削除に失敗しました**
- 原因: Botに「メッセージを管理」権限がない
- 対処: Botのロールに「メッセージを管理」権限を追加してください
- 注意: この権限がない場合、送信は成功しますが、メッセージの自動削除が行われません

---

## 必要な権限

Botに以下の権限が必要です：

- ✅ メッセージを読む
- ✅ メッセージ履歴を読む
- ✅ ウェブフックを管理（情報取得のみ）
- ✅ メッセージを送信
- ✅ **メッセージを管理**（即時削除機能に必要）

**権限の確認方法:**
1. サーバー設定 → ロール
2. Botのロールを選択
3. 上記の権限がすべてONになっているか確認

---

## セキュリティに関する注意

### 1. .envファイルの管理
- `.env` ファイルは絶対にGitにコミットしないでください
- `.gitignore` に `.env` を追加してください
- Web Hook URLは機密情報として扱ってください

### 2. Web Hook URLの取り扱い
- Web Hook URLを知っている人は、誰でもそのWeb Hookを使用してメッセージを送信できます
- 不要になったWeb Hookは必ず削除してください
- Web Hook URLが漏洩した場合は、すぐに削除して新しく作成してください

### 3. 権限の制限（推奨）
このコマンドを使用できるユーザーを制限することを強く推奨します。

**例: 特定のロールのみが使用可能にする**

```python
# webhook_sender.py の on_message 内に追加
if message.content == "WH送信":
    # 運営ロールのIDを指定
    allowed_role_id = 1234567890  # ← 実際のロールIDに変更
    
    # ロールチェック
    if not any(role.id == allowed_role_id for role in message.author.roles):
        try:
            await message.delete()
        except:
            pass
        error_msg = await message.channel.send("❌ このコマンドを使用する権限がありません。")
        await asyncio.sleep(3)
        await error_msg.delete()
        return
    
    # ... 以下続く
```

---

## カスタマイズ

### 1. コマンドトリガーの変更

`webhook_sender.py` の以下の部分を編集：

```python
if message.content == "WH送信":  # ← ここを変更
    # 例: "!webhook" に変更したい場合
    # if message.content == "!webhook":
```

### 2. タイムアウトの変更

確認画面の表示時間を変更する場合：

```python
class WebhookSendView(discord.ui.View):
    def __init__(self, ...):
        super().__init__(timeout=60)  # ← 秒数を変更（デフォルト: 60秒）
```

### 3. セッションキャンセルコマンドの追加

誤って開始したセッションをキャンセルできるようにする：

```python
# webhook_sender.py の on_message 内に追加
if message.content == "WH送信キャンセル":
    try:
        await message.delete()
    except:
        pass
    
    if user_id in user_sessions:
        # 保存されているBotメッセージを削除
        if "bot_message" in user_sessions[user_id]:
            try:
                await user_sessions[user_id]["bot_message"].delete()
            except:
                pass
        del user_sessions[user_id]
        cancel_msg = await message.channel.send("✅ セッションをキャンセルしました。")
        await asyncio.sleep(3)
        await cancel_msg.delete()
    return
```

---

## トラブルシューティング

### Q1: Web Hookの名前やアバターが反映されない
**A:** Web Hookの設定を変更した場合、Botを再起動する必要があります。また、Discord側のキャッシュが原因の場合もあるため、数分待ってから試してください。

### Q2: 送信先チャンネルを変更したい
**A:** Discord UIでWeb Hookのチャンネル設定を変更してください：
1. チャンネル設定 → 連携サービス → ウェブフック
2. Web Hookを編集
3. 「チャンネル」ドロップダウンから新しい送信先を選択
4. 変更を保存

### Q3: メッセージが削除されない
**A:** Botに「メッセージを管理」権限があるか確認してください。この権限がないと、メッセージの削除ができません。

### Q4: 複数人が同時に使用すると混乱する
**A:** 即時削除機能により、各ユーザーには自分の案内文のみが表示されます。ただし、確認画面が同時に複数表示される可能性があるため、専用チャンネルでの使用を推奨します。

### Q5: エラーメッセージが消えない
**A:** エラーメッセージは意図的に残しています。エラーを確認してから再試行してください。自動削除したい場合は、コードを修正してください。

---

## パフォーマンスに関する注意

### メッセージ検索の最適化

現在の実装では、メッセージIDからメッセージを取得する際、すべてのチャンネルを順番に検索しています。サーバーのチャンネル数が多い場合、パフォーマンスに影響する可能性があります。

**改善案:**
- キャッシュを使用して、最近使用したチャンネルを優先的に検索する
- メッセージが存在するチャンネルを特定のカテゴリに限定する

---

## 更新履歴

### v1.14.2 (2025-02-14)
- **変更**: チャンネルID入力フローを削除
  - Discord UIでWeb Hookのチャンネルを変更する方式に変更
  - よりシンプルで直感的なフローに
- **改善**: 即時メッセージ削除機能を強化
  - 各メッセージを受信直後に削除
  - チャンネルが常にクリーンな状態を維持
- **削除**: Bot側でのチャンネル変更API呼び出しを削除
  - エラーの原因となっていた機能を削除

### v1.14.1 (2025-02-14)
- **バグ修正**: `NoneType has no len()` エラーを修正
- **バグ修正**: チャンネルID入力後のセッション処理を改善
- **新機能**: 自動メッセージ削除機能を追加
- **改善**: エラーハンドリングの強化

### v1.14.0 (2025-02-14)
- Web Hook送信システムの追加
- .envファイルによるWeb Hook URL管理
- 対話型メッセージフロー実装
- ID検証機能の実装
- 確認画面（View）の実装

---

## FAQ（よくある質問）

**Q: Web Hookは1つしか作れませんか？**
A: いいえ、複数作成できます。用途に応じて複数のWeb Hookを作成し、`.env` ファイルで使い分けることができます。

**Q: 送信先チャンネルを変更するには？**
A: Discord UIでWeb Hookの設定を開き、チャンネルを変更してください。Bot側での操作は不要です。

**Q: メッセージを編集することはできますか？**
A: 現在のバージョンでは、新規メッセージの送信のみに対応しています。編集機能は今後のアップデートで検討されます。

**Q: 予約送信はできますか？**
A: 現在のバージョンでは対応していません。今後のアップデートで検討されます。

**Q: 送信履歴は記録されますか？**
A: 現在のバージョンでは記録されません。必要に応じて、ログ機能を追加してください。

**Q: エラーメッセージも削除したい**
A: デフォルトではエラーメッセージは残りますが、コードを修正することで削除できます。ユーザーがエラーを確認する時間を確保するため、現在の仕様としています。

---

## サポート

問題が発生した場合は、以下を確認してください：

1. ✅ Discord.pyのバージョン（2.0以降が必要）
2. ✅ Botの権限設定（特に「メッセージを管理」）
3. ✅ Web Hook URLの設定（.envファイル）
4. ✅ Web Hookの存在確認（Discord UI）
5. ✅ エラーログの内容

それでも解決しない場合は、エラーメッセージとともに開発チームにお問い合わせください。