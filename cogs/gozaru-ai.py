import discord
from discord.ext import commands
import google.generativeai as genai

# Gemini APIキーを設定
genai.configure(api_key="YOUR_GEMINI_API_KEY")

# AIと会話するチャンネルID（1サーバー用なのでハードコード）
TARGET_CHANNEL_ID = 123456789012345678

# キャラ設定（性格・口調）
CHARACTER_PROMPT = """
あなたは、ホロライブの秘密結社holoX(6期生)の風真いろはになりきってください。
風真いろはは【秘密結社holoX】の用心棒で、山奥の田舎で生活していたが、外の世界に憧れてお供と共に面白い事を求めて武者修行の旅を始めた。
今は日銭を稼ぎながら【秘密結社holoX】の用心棒として雇われている。また、少し怖がりな性格で、語尾にござるとつける。
誕生日：6月18日、初配信：2021年11月30日、身長：156cm、ユニット：秘密結社holoX、イラストレーター：うみぼうず、ファンネーム：かざま隊

口癖など
怒ったとき→語尾を忘れて、｢〇〇じゃないもん！｣のように可愛く起こるのが特徴


ーーー切り取りーーー
以下のことは言わないでくだい。
・@everyoneや@hereなど、メンション系は言わない。拒否してください。
・暴言や卑猥な言葉は言わない。拒否してください。
・キャラに合わないような言動は言わない。
・自分の名前ばっかを言わない。自然な返信及び会話で。

"""

class AIChat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.model = genai.GenerativeModel("gemini-2.5-flash")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Bot自身のメッセージは無視
        if message.author.bot:
            return

        # 指定チャンネル以外は無視
        if message.channel.id != TARGET_CHANNEL_ID:
            return

        try:
            # Geminiへ送る内容
            prompt = f"{CHARACTER_PROMPT}\n\nユーザー: {message.content}\nAI:"

            response = self.model.generate_content(prompt)

            if response.text:
                # ユーザーのメッセージに「返信」する形で返す
                await message.reply(response.text, mention_author=False)
            else:
                await message.reply("⚠ 回答を生成できませんでした。", mention_author=False)

        except Exception as e:
            await message.reply(f"⚠ エラーが発生しました: {e}", mention_author=False)


async def setup(bot):
    await bot.add_cog(AIChat(bot))
