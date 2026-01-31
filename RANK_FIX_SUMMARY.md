# ランク機能の修正サマリー

## 🔍 発見された問題

### 1. ファイル名の不一致
- **問題**: コードで `rank-bg.png` (ハイフン) を期待していたが、実際のファイル名は `rank_bg.png` (アンダースコア)
- **修正**: `RANK_BG_PATH` を `"assets/rankbg/rank_bg.png"` に変更

### 2. メッセージイベントリスナーの不足
- **問題**: メッセージ送信時に経験値を付与する `on_message` リスナーが実装されていなかった
- **修正**: `on_message` イベントリスナーを追加
  - メッセージ送信ごとに 5～15 EXP をランダムに付与
  - レベルアップ時に通知メッセージを送信
  - メンション設定に応じて通知の ON/OFF を切り替え

### 3. レベルアップ通知機能
- **追加**: レベルアップ時の自動通知機能
  - ユーザーがレベルアップしたときにチャンネルに通知
  - `/rank mention` コマンドで通知の有効/無効を切り替え可能

## ✅ 実装済み機能

### コマンド一覧

#### `/rank show [user]`
- 指定ユーザー（または自分）のランクカードを表示
- サーバー内順位、週間順位、経験値、レベルを表示

#### `/rank leaderboard [type]`
- ランキング表示（総合 or 週間）
- 上位10名までを表示

#### `/rank mention [enabled]`
- レベルアップ時のメンション通知の ON/OFF 設定

### 自動機能

#### メッセージ送信時の経験値付与
- メッセージ1件につき 5～15 EXP をランダム付与
- Bot のメッセージは対象外
- サーバー内のメッセージのみ対象

#### レベルアップ通知
- レベルが上がったときに自動でチャンネルに通知
- メンション設定に応じて通知の有無を制御

## 📦 必要なパッケージ

以下のパッケージが必要です（`requirements.txt` を作成済み）：

```
discord.py>=2.6.0
python-dotenv>=1.0.0
aiohttp>=3.9.0
Pillow>=10.0.0
```

インストールコマンド:
```bash
pip install -r requirements.txt
```

## 🗄️ データベース構造

### users テーブル
| カラム名 | 型 | 説明 |
|---------|-----|------|
| user_id | INTEGER (PK) | Discord ユーザーID |
| exp | INTEGER | 総経験値 |
| level | INTEGER | 現在のレベル |
| mention | INTEGER | メンション通知設定 (1=有効, 0=無効) |

### weekly_exp テーブル
| カラム名 | 型 | 説明 |
|---------|-----|------|
| user_id | INTEGER (PK) | Discord ユーザーID |
| exp | INTEGER | 週間経験値 |

## 📊 レベル計算式

```python
# レベル N に必要な総経験値
total_exp_for_level(N) = 20 × N × (N + 1)

# 例:
# Lv.1 → 40 EXP
# Lv.2 → 120 EXP
# Lv.3 → 240 EXP
# Lv.4 → 400 EXP
# Lv.5 → 600 EXP
```

## 🎨 必要なアセット

以下のファイルが必要です（すべて存在確認済み）：

### 画像
- `assets/rankbg/rank_bg.png` (2000 × 752 px)

### フォント
- `assets/font/NotoSansJP-Bold.ttf`
- `assets/font/NotoSansJP-Medium.ttf`
- `assets/font/NotoSansJP-Regular.ttf`

## 🚀 起動方法

1. 環境変数の設定:
```bash
cp .env.example ci/.env
# ci/.env を編集して DISCORD_BOT_TOKEN などを設定
```

2. パッケージのインストール:
```bash
pip install -r requirements.txt
```

3. Bot の起動:
```bash
python3 bot.py
```

## ⚠️ 注意事項

1. **データベースディレクトリ**: `data/rank/` ディレクトリは自動的に作成されます
2. **週間経験値のリセット**: 週間経験値は手動でリセットする必要があります（自動リセット機能は未実装）
3. **画像生成**: ランクカードは `/tmp/` ディレクトリに一時保存されます

## 🔧 今後の改善案

- [ ] 週間経験値の自動リセット機能（毎週月曜日0時など）
- [ ] ランクロールの自動付与機能
- [ ] カスタマイズ可能なランクカードデザイン
- [ ] 経験値倍率イベント機能
- [ ] クールダウン機能（連投による経験値稼ぎ防止）

## 📝 変更ファイル

- `cogs/rank/rank.py` - ランク機能の本体（修正済み）
- `requirements.txt` - 依存パッケージリスト（新規作成）
- `RANK_FIX_SUMMARY.md` - 本ドキュメント（新規作成）

---
修正日: 2026-01-31
