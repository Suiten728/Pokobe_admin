import discord
from discord.ext import commands
import random
import json
import os
from datetime import datetime, timedelta

DATA_FILE = "data/omikuji.json"
CONTROL_FILE = "data/omikuji_control.json"  # ★テスターモード管理用

def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_control():
    if not os.path.exists(CONTROL_FILE):
        return {"tester": []}
    with open(CONTROL_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_control(data):
    with open(CONTROL_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

class OmikujiCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # おみくじ結果
        self.results = ["大吉", "中吉", "小吉", "吉", "末吉", "凶", "大凶"]

        # 結果ごとのコメント
        self.iroha_messages = {
            "大吉": [
                "やったでござる〜！今日はきっといいことがあるでござるよ！",
                "大吉だ！！ござるも嬉しいでござる〜！",
                "これは幸先良しでござるな！元気にいくでござる！"
            ],
            "中吉": [
                "なかなか良い運勢でござるな！気を抜かずにいくでござる！",
                "中吉なら安心でござる！今日もがんばるでござるよ！",
                "悪くないでござる！むしろ良い日になるでござる！"
            ],
            "小吉": [
                "控えめに良い感じでござるな！まったりいくでござる！",
                "小さいけど吉！じんわり運が味方してるでござる！",
                "無理せずいけばきっと良くなるでござるよ！"
            ],
            "吉": [
                "安定してるでござるな！気軽にいくでござる！",
                "吉は良いでござる！ござるも応援してるでござるよ！",
                "落ち着いた運気でござる、ゆったりいくでござる！"
            ],
            "末吉": [
                "ちょっと控えめでござるが、悪くないでござるよ！",
                "じわじわ上がっていくタイプでござるな！",
                "今日は様子見でござる！でもきっと大丈夫でござる！"
            ],
            "凶": [
                "凶でも気にしないでござる！ここから上がるだけでござるよ！",
                "運気が低いかもだが、ござるは味方でござる！",
                "落ち込まずにいくでござるよ！明日はきっと良いでござる！"
            ],
            "大凶": [
                "ぬわーっ！まさかの大凶でござるか…！でも、気を落とさないで！！",
                "大凶はむしろ珍しいでござる！ここから運気が上がる一方と考えれば、逆に縁起が良いかもでござるよ！",
                "今日は慎重にいくでござる！でも、ござるが傍についているから、きっと大丈夫でござる！"
            ]
        }

def get_omikuji_result(results):
    control = load_control()
    prob = control.get("probability", {})

    # 通常モード → 完全ランダム（今まで通り）
    if prob.get("mode", "normal") == "normal":
        return random.choice(results)

    # カスタムモード
    weights = prob.get("weights", {})
    weight_list = [weights.get(r, 1) for r in results]

    return random.choices(results, weights=weight_list, k=1)[0]

    @commands.hybrid_command(name="おみくじ", description="風真いろはのコメント付きおみくじ！")
    async def omikuji(self, ctx):
        user_id = str(ctx.author.id)
        today = datetime.now().date()

        data = load_data()
        control = load_control()

        is_tester = user_id in control.get("tester", [])

        # ★ テスターモードは回数無限 → 日付制限スキップ
        if not is_tester:
            if user_id in data:
                last_date = datetime.strptime(data[user_id]["last_date"], "%Y-%m-%d").date()

                if last_date == today:
                    return await ctx.reply("もう既に引いています。明日チャレンジしてね！")

                if last_date == today - timedelta(days=1):
                    data[user_id]["count"] += 1
                else:
                    del data[user_id]

        if user_id not in data:
            data[user_id] = {"last_date": today.strftime("%Y-%m-%d"), "count": 1}

        data[user_id]["last_date"] = today.strftime("%Y-%m-%d")
        streak = data[user_id]["count"]

        save_data(data)

        result = get_omikuji_result(self.results)
        iroha_msg = random.choice(self.iroha_messages[result])
        color = discord.Color.random()

        # ---- ★ メンションだけ先に送信 ----
        msg = await ctx.send(f"{ctx.author.mention}")

        # ---- ★ 埋め込み準備 ----
        embed = discord.Embed(
            title="🍃ござるおみくじ結果🍃",
            description="",
            color=color
        )

        # フッター（連続参拝日数入り）
        embed.set_footer(
            text=f"また明日もお参りください！│連続参拝 : {streak}日\n©2025 かざま隊の集いの場"
        )

        # 空の状態で送信
        await msg.edit(content=ctx.author.mention, embed=embed)

        # ---- ★ 1行ずつ表示する文章 ----
        texts = [
            "みこちがいるさくら神社に到着した...\n",
            "こちらをじっと見つめている...\n",
            "おみくじ代としてござるクッキーをあげた...\n",
            "**みこち**「今日も良いおみくじだといいにぇ〜！」\n",
            "目を閉じて良いものが出てくるよう祈りながらおみくじを選んだ。\n",
            "選んだおみくじを開く...\n",
            f"そこには **{result}** と書かれていた。\n",
            f"**風真いろはからのメッセージ**：\n{iroha_msg}"
        ]

        current_desc = ""

        # ---- ★ 1行ずつ1秒おきに編集 ----
        for line in texts:
            current_desc += line + "\n"
            embed.description = current_desc
            await msg.edit(content=ctx.author.mention, embed=embed)
            await discord.utils.sleep_until(datetime.now() + timedelta(seconds=1.5))


async def setup(bot):
    await bot.add_cog(OmikujiCog(bot))
