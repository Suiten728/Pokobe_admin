# cogs/commands/omikuji.py
import discord
from discord.ext import commands
import random

class OmikujiCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # おみくじ結果
        self.results = [
            "大吉", "中吉", "小吉", "吉", "末吉", "凶"
        ]

        # 結果ごとの風真いろはメッセージ（3つずつ）
        self.iroha_messages = {
            "大吉": [
                "やったでござる！今日はきっといいことがあるでござるよ！",
                "大吉とは強い…！拙者も嬉しい気持ちでござる！",
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
                "吉は良いでござる！拙者も応援してるでござるよ！",
                "落ち着いた運気でござる、ゆったりいくでござる！"
            ],
            "末吉": [
                "ちょっと控えめでござるが、悪くないでござるよ！",
                "じわじわ上がっていくタイプでござるな！",
                "今日は様子見でござる！でもきっと大丈夫でござる！"
            ],
            "凶": [
                "凶でも気にしないでござる！ここから上がるだけでござるよ！",
                "運気が低いかもだが、拙者は味方でござる！",
                "落ち込まずにいくでござるよ！明日はきっと良いでござる！"
            ]
        }

    # ハイブリッドコマンド
    @commands.hybrid_command(name="おみくじ", description="風真いろはのコメント付きおみくじを引く！")
    async def omikuji(self, ctx):
        # ランダム結果
        result = random.choice(self.results)

        # 該当結果の3つからランダムにメッセージ
        iroha_msg = random.choice(self.iroha_messages[result])

        # ランダムカラー
        color = discord.Color.random()

        # 埋め込み
        embed = discord.Embed(
            title="🎍 おみくじの結果でござる！",
            description=f"**結果：||{result}||**\n\n**風真いろはからのメッセージ：**\n{iroha_msg}",
            color=color
        )

        # フッター
        embed.set_footer(text="©2025 かざま隊の集いの場")

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(OmikujiCog(bot))
