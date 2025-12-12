<div align="center">
    <h1>ぽこべぇ管理人Bot</h1>
    <img src="https://suiten-8ckghymktw.edgeone.dev/1000004028-removebg-preview.png" alt="Pokobe_admin Logo" width="200" height="200">
    <h2>📕総合ガイド</h2>

[![license](https://img.shields.io/github/license/ryo-ma/github-profile-trophy)](https://github.com/Suiten728/Pokobe_admin/blob/main/LICENSE)
[![Discord](https://img.shields.io/discord/1363116304764112966?logo=discord&logoColor=white)](https://discord.gg/2wF8e8YuQY)

</div>

ぽこべぇ管理人Botはかざま隊の集いの場の管理をします。こちらは、1サーバー専用のため、ハードコードが含まれる可能性があります。詳しくはSuitenまでご連絡下さい。また、こちらのコードを公開しないようにお願いします。</br>


## 🛠機能
ぽこべぇ管理人Botにはたくさんの機能が備え付けられています。追加予定及び追加済機能は以下のとおりです。</br>
💡実装済みは🔵、未実装又は協議中は🔴で分けています。</br>
### 🔵P!おみくじ│/おみくじ
風真いろはのコメント付きのおみくじができます。</br>
### 🔵P!ping｜/ping
レイテンシーを計測します。速度によって文字が変わります。</br>
### 🔵P!omikuji_control
おみくじ情報をコントロールします。サーバーオーナーのみ使用可能です。</br>
テスターモード : 一日複数利用可能</br>
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

- **メインボット** : [ぽこべぇ管理人#4459](https://github.com/Suiten728/Pokobe_admin)
- **開発ボット** : ﾃｽﾄﾎﾞｯﾄ#4839
- **音楽ボット** : [いろはMusic#0080](https://github.com/Suiten728/Iroha_Music)
- **ギルドサーバー** : [かざま隊の集いの場](https://discord.gg/2wF8e8YuQY)
- **言語** : Python 3.12+ , discord.py 2.6+
  
## ⚙️開発・ライセンス
このBotは[LICENSE](https://github.com/Suiten728/Pokobe_admin/blob/main/LICENSE)に基づいて公開します。</br>
作者(Suiten)は一切の責任を負いません。また、犯罪及び荒らしに関わる使用は禁止します。


## 🗒備考
現在開発途中の内部機能</br>
以下は正常に動かない場合があります。使用する際はブランチをbetaにすると動く可能性があります。</br>
(betaは開発途中のコードも含むため推奨はしません)
- Welcomeメッセージ(cogs/systems/welcome.py)
- TikTokのウェブフック(cogs/systems/tiktok.py)
- 多言語機能付きテキスト(cogs/systems/pulldown.py)
- メンシプ認証
- 匿名目安箱(cogs/systems/tokumei-feedback.py)
- ランク機能(cogs/commands/rank.py)

<div align="center">
  <p>©2025 Pokobe_admin Powered by Suiten</p>
</div>
