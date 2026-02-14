# Bot v1.14 アップデートガイド

## 新機能: Web Hook送信システム

### 概要
v1.14では、Discord Web Hookを使用したメッセージ転送システムが追加されました。
このシステムにより、運営スタッフが質問対応などを行う際に、事前に設定したWeb Hookの名前とアバターを使用してメッセージを送信できます。

### 主な特徴
- 対話型のメッセージフロー
- .envファイルでWeb Hook URLを一元管理
- Web Hookの名前とアバターはDiscord側で設定
- Bot側でWeb Hookの送信先チャンネルを動的に変更可能
- メッセージID・チャンネルIDの検証機能
- 確認画面による誤送信防止
- **自動メッセージ削除機能**: コマンドや入力したIDなど、すべてのやり取りが自動的に削除されます

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

1. **任意のチャンネルでWeb Hookを作成**
   - チャンネル設定 → 連携サービス → ウェブフック
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

**注意:** 最初に設定したチャンネルは任意で構いません。Bot側で送信先チャンネルを動的に変更するため、どのチャンネルでWeb Hookを作成しても問題ありません。

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
   → `送信するメッセージIDを送信してください。`

2. **メッセージIDの入力**
   ```
   1234567890123456789
   ```
   → `送信するチャンネルIDを送信してください。`

3. **チャンネルIDの入力**
   ```
   9876543210987654321
   ```
   → 確認画面が表示されます

4. **確認画面**
   ```
   以下の内容で送信します。送信しますか？
   
   📝 名前: `運営質問担当`
   🖼️ アバター: [URL]
   📢 送信先チャンネル: #質問チャンネル
   
   [はい] [いいえ]
   ```

5. **送信実行**
   - 「はい」ボタンをクリックすると送信されます
   - 「いいえ」ボタンでキャンセルできます
   - **送信完了またはキャンセル後、すべてのメッセージが自動的に削除されます**（「WH送信」コマンドから確認画面まで）

### 自動メッセージ削除について

プライバシーとチャンネルの整理のため、以下のメッセージが自動的に削除されます：

- ✅ 「WH送信」コマンド
- ✅ Botからの案内メッセージ（「メッセージIDを送信してください」など）
- ✅ ユーザーが入力したメッセージID
- ✅ ユーザーが入力したチャンネルID
- ✅ エラーメッセージ（IDが無効な場合など）
- ✅ 確認画面のメッセージ

**注意**: メッセージ削除には「メッセージを管理」権限が必要です。

### IDの取得方法

**メッセージIDの取得:**
1. Discord の設定 → 詳細設定 → 開発者モードをON
2. メッセージを右クリック → IDをコピー

**チャンネルIDの取得:**
1. Discord の設定 → 詳細設定 → 開発者モードをON
2. チャンネルを右クリック → IDをコピー

---

## 運営募集での使用例

### シナリオ: 質問対応スタッフとしての使用

#### 準備
1. Web Hookを作成し、名前を「運営質問担当」に設定
2. アバターに運営ロゴをアップロード
3. Web Hook URLを`.env`ファイルに設定

#### 実際の使用
1. 運営用チャンネルで応募者からの質問を確認
2. 応募者への返信メッセージを作成（送信はしない）
3. そのメッセージのIDをコピー
4. `WH送信` コマンドを実行
5. メッセージIDを入力
6. 応募者がいるチャンネルのIDを入力
7. 確認して「はい」をクリック
8. → 「運営質問担当」名義で応募者チャンネルに返信が送信される

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

### Web Hookのチャンネル変更

このシステムでは、Discord APIの機能を使用してWeb Hookの送信先チャンネルを動的に変更しています。

1. ユーザーがチャンネルIDを入力
2. Bot側でWeb Hook APIを呼び出し、`channel_id` を変更
3. 変更後、メッセージを送信

これにより、1つのWeb Hookで複数のチャンネルに送信できます。

### セッション管理

ユーザーごとにセッションを管理しているため、複数のユーザーが同時に使用しても問題ありません。

```python
user_sessions = {
    user_id_1: {"step": "waiting_message_id", ...},
    user_id_2: {"step": "waiting_channel_id", ...},
}
```

---

## エラー対処

### よくあるエラー

**❌ 無効なメッセージIDです**
- 原因: 数字以外の文字が含まれている
- 対処: 数字のみで構成されたIDを入力してください

**❌ 指定されたチャンネルが見つかりません**
- 原因: チャンネルIDが間違っているか、Botがアクセスできない
- 対処: チャンネルIDを確認し、Botの権限を確認してください

**❌ Web Hookのチャンネル変更に失敗しました**
- 原因: Botの権限不足、またはWeb Hook URLが無効
- 対処: 
  - Botに「ウェブフックを管理」権限があるか確認
  - `.env`ファイルのWeb Hook URLが正しいか確認

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

**以前のエラー（v1.14.1で修正済み）:**
- ~~❌ `object of type 'NoneType' has no len()`~~ → **修正済み**
- ~~確認画面後に「無効なチャンネルID」と表示される~~ → **修正済み**

---

## 必要な権限

Botに以下の権限が必要です：

- ✅ メッセージを読む
- ✅ メッセージ履歴を読む
- ✅ ウェブフックを管理
- ✅ メッセージを送信
- ✅ **メッセージを管理**（自動削除機能に必要）

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
        await message.channel.send("❌ このコマンドを使用する権限がありません。")
        return
    
    user_sessions[user_id] = {
        "step": "waiting_message_id",
        "channel_id": message.channel.id
    }
    await message.channel.send(f"{message.author.mention} 送信するメッセージIDを送信してください。")
    return
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
    if user_id in user_sessions:
        del user_sessions[user_id]
        await message.channel.send("✅ セッションをキャンセルしました。")
    else:
        await message.channel.send("❌ アクティブなセッションはありません。")
    return
```

### 4. 複数のWeb Hookを使い分ける

異なる用途で複数のWeb Hookを使用したい場合：

```python
# .env ファイル
WEBHOOK_URL_QUESTIONS=https://discord.com/api/webhooks/111111/aaaaa
WEBHOOK_URL_INTERVIEW=https://discord.com/api/webhooks/222222/bbbbb

# webhook_sender.py
class WebhookSenderCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.webhooks = {
            "質問": os.getenv('WEBHOOK_URL_QUESTIONS'),
            "面接": os.getenv('WEBHOOK_URL_INTERVIEW'),
        }
    
    # 使用時にどのWeb Hookを使うか選択させるロジックを追加
```

---

## トラブルシューティング

### Q1: Web Hookの名前やアバターが反映されない
**A:** Web Hookの設定を変更した場合、Botを再起動する必要があります。また、Discord側のキャッシュが原因の場合もあるため、数分待ってから試してください。

### Q2: 「Bot {bot_token}」というエラーが出る
**A:** Botのトークンが正しく読み込まれていない可能性があります。`.env` ファイルに `DISCORD_TOKEN` が正しく設定されているか確認してください。

### Q3: メッセージは送信されるが、添付ファイルが送信されない
**A:** 添付ファイルのサイズが大きすぎる可能性があります。Discord の添付ファイルサイズ制限（8MB または Nitroブーストで増加）を確認してください。

### Q4: チャンネルIDを入力しても何も起こらない
**A:** セッションがタイムアウトしている可能性があります。もう一度 `WH送信` から始めてください。

### Q5: 複数人が同時に使用すると混乱する
**A:** システムはユーザーごとにセッションを管理しているため、同時使用は問題ありません。ただし、同じチャンネルで複数人が使用すると見づらくなるため、専用チャンネルでの使用を推奨します。

---

## パフォーマンスに関する注意

### メッセージ検索の最適化

現在の実装では、メッセージIDからメッセージを取得する際、すべてのチャンネルを順番に検索しています。サーバーのチャンネル数が多い場合、パフォーマンスに影響する可能性があります。

**改善案:**
- メッセージIDの入力時に、そのメッセージがあるチャンネルIDも一緒に入力してもらう
- キャッシュを使用して、最近使用したチャンネルを優先的に検索する

---

## 更新履歴

### v1.14.1 (2025-02-14)
- **バグ修正**: `NoneType has no len()` エラーを修正
- **バグ修正**: チャンネルID入力後のセッション処理を改善
- **新機能**: 自動メッセージ削除機能を追加
  - コマンドから確認画面までのすべてのメッセージを自動削除
  - プライバシー保護とチャンネルの整理に貢献
- **改善**: エラーハンドリングの強化

### v1.14.0 (2025-02-14)
- Web Hook送信システムの追加
- .envファイルによるWeb Hook URL管理
- Bot側でWeb Hookの送信先チャンネルを動的に変更する機能
- 対話型メッセージフロー実装
- ID検証機能の実装
- 確認画面（View）の実装

---

## FAQ（よくある質問）

**Q: Web Hookは1つしか作れませんか？**
A: いいえ、複数作成できます。用途に応じて複数のWeb Hookを作成し、`.env` ファイルで使い分けることができます。

**Q: メッセージを編集することはできますか？**
A: 現在のバージョンでは、新規メッセージの送信のみに対応しています。編集機能は今後のアップデートで検討されます。

**Q: 予約送信はできますか？**
A: 現在のバージョンでは対応していません。今後のアップデートで検討されます。

**Q: 送信履歴は記録されますか？**
A: 現在のバージョンでは記録されません。必要に応じて、ログ機能を追加してください。

**Q: メッセージの自動削除を無効にできますか？**
A: コードを修正することで無効化できます。`webhook_sender.py` の `delete_messages()` メソッドの呼び出しをコメントアウトしてください。ただし、プライバシーとチャンネルの整理のため、自動削除を有効にすることを推奨します。

**Q: 削除されたメッセージを復元できますか？**
A: いいえ、削除されたメッセージは復元できません。これは Discord の仕様です。

**Q: 「メッセージを管理」権限がない場合はどうなりますか？**
A: Web Hook送信は正常に動作しますが、メッセージの自動削除が行われません。チャンネルにやり取りが残り続けます。

---

## サポート

問題が発生した場合は、以下を確認してください：

1. ✅ Discord.pyのバージョン（2.0以降が必要）
2. ✅ Botの権限設定
3. ✅ Web Hook URLの設定（.envファイル）
4. ✅ Web Hookの存在確認
5. ✅ エラーログの内容

それでも解決しない場合は、エラーメッセージとともに開発チームにお問い合わせください。