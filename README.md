<div align="center">
    <h1>ぽこべぇ管理人Bot</h1>
    <img src="https://suiten-8ckghymktw.edgeone.dev/1000004028-removebg-preview.png" alt="Pokobe_admin Logo" width="200" height="200">
    <h2>📕総合ガイド</h2>
</div>
[![Python](https://img.shields.io/github/pyhon)]

[![license](https://img.shields.io/github/license/ryo-ma/github-profile-trophy)](https://github.com/Suiten728/Pokobe_admin/blob/main/LICENSE)

[![Discord](https://img.shields.io/discord/308323056592486420?logo=discord&logoColor=white)]

ぽこべぇ管理人Botはかざま隊の集いの場の管理をします。こちらは、1サーバー専用のため、ハードコードが含まれる可能性があります。詳しくはSuitenまでご連絡下さい。また、こちらのコードを公開しないようにお願いします。</br>


## 🛠機能
ぽこべぇ管理人Botにはたくさんの機能が備え付けられています。追加予定及び追加済機能は以下のとおりです。</br>
💡実装済みは🔵、未実装又は協議中は🔴で分けています。</br>
### 🔵P!ping｜/ping
レイテンシーを計測します。速度によって文字が変わります。</br>
### 🔵P!lock [message_id]
そのチャンネルでそのメッセージを固定します。[message_id]はコマンド実行するチャンネル内にないとエラーが出ます。</br>
### 🔵P!unlock [message_id]
そのチャンネルでそのメッセージの固定を外します。[message_id]はぽこべぇ管理人がメッセージ固定中のidでも解除できます。　</br>
### 🔵P!locklist
そのチャンネルで固定されているリストを出力します。</br>
### 🔵P!post_[system_name]
authn.pyやrules.pyの送信用コマンドです。送信ができればコマンドメッセージにチェックマークのリアクションをします。</br>例）P!post_authn  ,  P!post_rules</br>
### 🔵P!eval
コード実行コマンドです。コードブロック(```)にしなくても動作します。サーバーオーナーのみ使用可能です。</br>
### 🔴P!rank｜/rank
自分のランクを画像で出力します。ランクの保存形式はJSONです。</br>
### 🔴P!rank_ctrl
ランクをコントロールします。増加、減少などを操作でき、運営メンバーのみ使用可能です。</br>

## 📊統計

- **メインボット** : ぽこべぇ管理人#4459
- **開発ボット** : ﾃｽﾄﾎﾞｯﾄ#4839
- **音楽ボット** : いろはMusic#0080
- **ギルドサーバー** : かざま隊の集いの場
- **言語** : Python 3.12+ , discord.py 2.6+


## 🗒備考
現在開発途中の内部機能
- Welcomeメッセージ(cogs/systems/welcome.py)
- TikTokのウェブフック(cogs/systems/tiktok.py)
- 多言語機能付きテキスト(cogs/systems/pulldown.py)
- メンシプ認証
- 匿名目安箱(cogs/systems/tokumei-feedback.py)
- ランク機能(cogs/commands/rank.py)

<div align="center">
©2025 Pokobe_admin Powered by Suiten
</div>