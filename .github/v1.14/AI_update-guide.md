# 風真いろはAI v1.14 UPDATE-GUIDE

## 📋 変更概要

このアップデートでは、以下の2つの主要な改善が行われました：

### 1. v1.14仕様への完全対応
既存のコードを`ai-gozaru_v1_14_spec.md`(事前企画書)の仕様に沿って全面的に改修しました。

### 2. AI制御コマンドの統合
従来の`ai_status`、`ai_off`、`ai_on`コマンドを、`P!ai-ctrl`という1つのコマンドに統合し、Embed + Viewボタンで操作できるようにしました。

---

## 🔄 主な変更点

### ai_reply.py（旧版からの変更）

#### ✅ データ構造の変更
**旧版:**
```python
DEFAULT_CHARACTER = "data_public/ai-image.txt"
HOLO_JSON = "data_public/holomembers.json"
```

**新版:**
```python
PROFILE_JSON = "data/profile.json"
RELATIONSHIPS_JSON = "data/relationships.json"
JOKES_JSON = "data/jokes.json"
SYSTEM_PROMPT_TXT = "data/system_prompt.txt"
```

#### ✅ メモリ制限の変更
**旧版:** 10往復分（MEMORY_LIMIT = 10）  
**新版:** 5往復分（MEMORY_LIMIT = 5）← v1.14仕様準拠

#### ✅ 新機能の追加

1. **検索判定機能**
```python
SEARCH_KEYWORDS = [
    "最新", "今日", "今", "ニュース", "株価", "価格", 
    "何年設立", "説明して", "いつ", "現在"
]

def needs_search(self, text: str) -> bool:
    """検索が必要かどうかを判定"""
    for keyword in SEARCH_KEYWORDS:
        if keyword in text:
            return True
    return False
```

2. **関係性に基づく呼称・話し方制御**
```python
def resolve_person(self, text: str, relationships: dict):
    """テキストから人物名を解決"""
    for person_name in relationships.keys():
        if person_name in text:
            return person_name
    return None
```

3. **ネタ検出システム**
```python
def check_jokes(self, text: str, jokes: dict):
    """ネタキーワードをチェック"""
    for joke_key, joke_data in jokes.items():
        keywords = joke_data.get("keywords", [])
        for keyword in keywords:
            if keyword in text:
                return joke_data
    return None
```

4. **v1.14準拠のプロンプト構築**
```python
def build_prompt(self, user_input: str, channel_id: int, profile: dict, 
                 relationships: dict, jokes: dict, system_prompt: str):
    """v1.14仕様に沿ったプロンプトを構築"""
    # プロフィール、会話履歴、人物認識、ネタ、検索判定をすべて統合
```

5. **AI稼働状態の制御**
```python
# AI停止中は無視
if not self.bot.talk_enabled:
    return
```

#### ✅ Geminiモデルの更新
**旧版:** `gemini-2.5-flash-lite`  
**新版:** `gemini-2.0-flash-exp`（より高性能なモデル）

---

### ai_control.py（新規作成）

#### 📌 統合制御パネルの特徴

**旧版の問題点:**
- 3つのコマンド（`ai_status`, `ai_off`, `ai_on`）が別々
- テキストベースのみ
- ステータスを確認するために別コマンドを実行する必要

**新版の改善:**
```python
@commands.command(name="ai-ctrl")
async def ai_ctrl(self, ctx):
    """AI制御パネルを表示"""
    view = AIControlView(self.bot)
    embed = view.create_status_embed()
    await ctx.send(embed=embed, view=view)
```

**機能:**
1. **🟢 AI起動ボタン**
   - 管理者権限チェック付き
   - ワンクリックで起動
   - 即座にEmbedが更新される

2. **🔴 AI停止ボタン**
   - 管理者権限チェック付き
   - 緊急停止に対応
   - 即座にEmbedが更新される

3. **🔄 ステータス更新ボタン**
   - 誰でも使用可能
   - リアルタイムで状態を確認

4. **視覚的なステータス表示**
```python
def create_status_embed(self):
    """現在のステータスを表示するEmbedを作成"""
    status = "🟢 **稼働中**" if self.bot.talk_enabled else "🔴 **停止中**"
    color = discord.Color.green() if self.bot.talk_enabled else discord.Color.red()
    # 色とアイコンで直感的に状態がわかる
```

---

## 📊 データファイルの構造

### profile.json
風真いろはの基本プロフィール情報を格納。AIがこの情報を参照して自己紹介や性格を表現します。

```json
{
  "name": "風真いろは",
  "unit": "秘密結社holoX",
  "traits": ["方向音痴", "意外と天然", "意外と負けず嫌い"],
  "likes": ["ゲーム", "歌", "お菓子作り", "ござるくっきー"]
}
```

### relationships.json
他のメンバーとの関係性と呼称を定義。

```json
{
  "星街すいせい": {
    "call": "すいせい先輩",
    "speech": "respect"  // 敬語使用
  },
  "ラプラス・ダークネス": {
    "call": "ツノガキ",
    "speech": "casual"  // タメ語
  }
}
```

### jokes.json
特定のキーワードに対するネタ反応を定義。

```json
{
  "suisei": {
    "keywords": ["すいせい", "すいちゃん"],
    "response": [
      "今日も可愛いでござる！",
      "すいせい先輩は最強なのでござる！"
    ]
  }
}
```

### system_prompt.txt
AIの振る舞いを詳細に定義するプロンプト。v1.14仕様に完全準拠。

---

## 🔄 移行手順

### ステップ1: バックアップ
```bash
# 既存のファイルをバックアップ
cp -r cogs cogs_backup
cp -r data data_backup
```

### ステップ2: 新ファイルの配置
```bash
# 新しいファイルを配置
cp ai_reply.py cogs/
cp ai_control.py cogs/

# データディレクトリの作成
mkdir -p data
cp profile.json data/
cp relationships.json data/
cp jokes.json data/
cp system_prompt.txt data/
```

### ステップ3: bot.pyの更新
```python
# 旧Cogをアンロード（必要に応じて）
# await bot.unload_extension("cogs.old_talk")

# 新Cogをロード
await bot.load_extension("cogs.ai_reply")
await bot.load_extension("cogs.ai_control")
```

### ステップ4: 動作確認
1. Botを起動
2. `P!ai-ctrl`コマンドを実行
3. 制御パネルが表示されることを確認
4. AIに話しかけて、応答を確認

---

## 🆕 新しい機能の使い方

### 1. AI制御パネル

**コマンド:**
```
P!ai-ctrl
```

**表示例:**
```
🤖 AI制御パネル
現在のAI状態: 🟢 稼働中

💡 使い方
🟢 AI起動: AIを起動します（管理者のみ）
🔴 AI停止: AIを緊急停止します（管理者のみ）
🔄 ステータス更新: 現在のステータスを更新します

[🟢 AI起動] [🔴 AI停止] [🔄 ステータス更新]
```

### 2. メンバー認識機能

**例:**
```
ユーザー: すいせい先輩はどう思う？
AI: すいせい先輩は最強でござる！かざまも見習いたいでござるな〜
```

AIは`relationships.json`を参照して、「すいせい先輩」と適切に呼称します。

### 3. ネタ反応

**例:**
```
ユーザー: ラプラスって知ってる？
AI: ツノガキめ！でも仲間でござる！
```

`jokes.json`のキーワードに反応します。

### 4. 検索判定

**例:**
```
ユーザー: 今日のニュース教えて
AI: （検索機能未実装のため、わからないと伝える）
```

検索が必要な質問を検出し、将来の検索API実装に備えます。

---

## 🎯 Webhook機能の維持

**重要:** 既存のWebhook機能は完全に維持されています。

```python
async def post_webhook_reply(self, message: discord.Message, content: str):
    payload = {
        "content": content,
        "username": WEBHOOK_NAME,
        "allowed_mentions": {"parse": []},
        "message_reference": {
            "message_id": str(message.id),
            "channel_id": str(message.channel.id)
        }
    }
    async with aiohttp.ClientSession() as session:
        await session.post(WEBHOOK_URL, json=payload)
```

この部分は旧版と同じコードを使用しています。

---

## 🔍 技術的な詳細

### 会話履歴の管理

**SQLiteデータベース構造:**
```sql
CREATE TABLE memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id INTEGER,
    role TEXT,           -- 'user' または 'assistant'
    content TEXT,
    timestamp TEXT
)
```

**取得方法:**
```python
def load_memory(self, channel_id: int) -> str:
    # 直近5往復分（10レコード）を取得
    c.execute(
        "SELECT role, content FROM memory WHERE channel_id=? ORDER BY id DESC LIMIT ?",
        (channel_id, MEMORY_LIMIT * 2)
    )
```

### プロンプト構築の流れ

1. システムプロンプトを読み込む
2. プロフィール情報を追加
3. 会話履歴を追加
4. 人物名を認識し、関係性情報を追加
5. ネタキーワードを検出し、候補を追加
6. 検索が必要か判定
7. ユーザー入力を追加
8. Gemini APIに送信

---

## ⚡ パフォーマンス最適化

### 1. メモリ削減
- 会話履歴を10往復→5往復に削減
- プロンプトサイズの最適化

### 2. 応答速度向上
- 不要な処理の削減
- 効率的なデータ読み込み

### 3. エラーハンドリング
```python
try:
    profile = self.load_profile()
    # ...
except FileNotFoundError:
    return {}  # ファイルがなくても続行
```

---

## 🛡️ セキュリティ

### 管理者権限チェック
```python
if not interaction.user.guild_permissions.administrator:
    await interaction.response.send_message(
        "⚠️ この操作には管理者権限が必要です。",
        ephemeral=True
    )
    return
```

### メンション防止
```python
"allowed_mentions": {"parse": []}
```

### 文字数制限
```python
user_input = message.content[:USER_MAX_LENGTH]
reply = reply[:GEMINI_MAX_LENGTH]
```

---

## 📝 まとめ

このv1.14アップデートにより、以下が実現されました：

✅ v1.14仕様への完全準拠  
✅ データ駆動型の柔軟な設定  
✅ 直感的なAI制御パネル  
✅ メンバー認識と適切な呼称  
✅ ネタ反応システム  
✅ 検索機能への対応準備  
✅ Webhook機能の完全維持  

これにより、風真いろはAIはより自然で、管理しやすく、拡張性の高いシステムになりました。