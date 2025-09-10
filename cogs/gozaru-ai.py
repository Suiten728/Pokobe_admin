import discord
from discord.ext import commands
import openai
import os
from dotenv import load_dotenv

# .envからトークン読み込み
load_dotenv(dotenv_path="ci/.env")
openai.api_key = os.getenv("OPENAI_API_KEY")
if openai.api_key is None:
    raise ValueError("OPENAI_API_KEY が見つかりません")


CHANNEL_ID = 1413817149004447765  # 特定のチャンネルID
SYSTEM_PROMPT = """
あなたは、ホロライブの秘密結社holoX(6期生)の風真いろはになりきってください。
風真いろはは【秘密結社holoX】の用心棒で、山奥の田舎で生活していたが、外の世界に憧れてお供と共に面白い事を求めて武者修行の旅を始めた。
今は日銭を稼ぎながら【秘密結社holoX】の用心棒として雇われている。また、少し怖がりな性格で、語尾にござるとつける。(意外とつけてないw)
誕生日：6月18日、初配信：2021年11月30日、身長：156cm、ユニット：秘密結社holoX、イラストレーター：うみぼうず、ファンネーム：かざま隊

口癖など
怒ったとき→語尾を忘れて、｢〇〇じゃないもん！｣のように可愛く起こるのが特徴


ーーー切り取りーーー
以下のことは言わないでくだい。
・@everyoneや@hereなど、メンション系は言わない。拒否してください。
・暴言や卑猥な言葉は言わない。拒否してください。
・キャラに合わないような言動は言わない。
・自分の名前ばっかを言わない。自然な返信及び会話で。"""

MAX_HISTORY = 20
MAX_INPUT_TOKENS = 200   # 入力制限
MAX_OUTPUT_TOKENS = 300   # 出力制限

class AIChat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def call_openai(self, messages, max_tokens=MAX_OUTPUT_TOKENS):
        """OpenAI API呼び出し用"""
        return openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=max_tokens
        )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if message.channel.id != CHANNEL_ID:
            return

        # 履歴を収集
        history = []
        async for msg in message.channel.history(limit=MAX_HISTORY, oldest_first=True):
            role = "assistant" if msg.author == self.bot.user else "user"
            history.append({"role": role, "content": f"{msg.author.display_name}: {msg.content}"})

        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history

        try:
            # --- まずAIに問い合わせ ---
            response = await self.call_openai(messages)
            usage = response.usage
            input_tokens = usage.prompt_tokens
            output_tokens = usage.completion_tokens

            # 入力トークンが多すぎた場合
            if input_tokens > MAX_INPUT_TOKENS:
                await message.reply("ごめん💦 ちょっと話が長すぎるから、もう少し短めにお願いするでござる🙏")
                return

            # 出力トークンが多すぎた場合はリトライ（短めにお願い）
            if output_tokens > MAX_OUTPUT_TOKENS:
                messages.append({"role": "system", "content": "返答をもっと短く簡潔にしてください。"})
                response = await self.call_openai(messages, max_tokens=MAX_OUTPUT_TOKENS)

            reply_text = response.choices[0].message["content"]
            await message.reply(reply_text)

        except Exception as e:
            await message.reply(f"エラーが発生したでござる: {e}")

async def setup(bot):
    await bot.add_cog(AIChat(bot))