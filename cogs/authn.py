import os
import random
import string
from typing import Optional

import discord
from discord.ext import commands
from discord.ui import View, Button, Select

# ====== ここを環境に合わせて設定 ======
VERIFY_CHANNEL_ID = 1412072178639442081    # 認証キーワードを送るチャンネルID
VERIFIED_ROLE_ID  = 1363454584919691284    # 認証付与するロールID
LOG_CHANNEL_ID = 1413154721593688075
# =====================================

# ユーザー -> 発行済みキーワード（再起動で消える想定）
verification_keywords: dict[int, str] = {}


def generate_keyword(length: int = 6) -> str:
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))


# ---- ガイド埋め込み（簡略化。必要なら元の長文に差し替え可） ----
def build_guides():
    return {
        "ja": discord.Embed(
            title="認証方法ガイド",
            description="認証方法ガイドへようこそ！\n\n"
                        "かざま隊の集いの場では、セキュリティ上認証を行うことでチャンネルにアクセスできるようになります。\n\n",
            color=discord.Color.blue()
         ).add_field(name="\n\n**__ステップ1__**\n\n",value="認証のしやすさを考慮してデバイスごとに分けています。まず初めにご利用中のデバイスにあった認証方法を選択してください。\n\nボタンを押して、「✅️DMを確認してください。」と表示されれば成功です。｢❌️DMを送信できません。DMを許可してください｣と表示されればDMを許可しているかご確認ください。", inline=False)
          .add_field(name="\n\n**__ステップ2__**\n\n",value="認証キーワードがDMで送信されます。\n\nスマホ版はキーワードを長押ししてコピーしてください。\nPC版は右側のボタンを押してコピーしてください。", inline=False)
          .add_field(name="\n\n**__ステップ3__**\n\n",value=" **<#{VERIFY_CHANNEL_ID}>** にキーワードを送信してください。\n\nキーワードに「##」などの記号がついていても問題ありません。また、キーワードは他人に絶対に伝えないでください。", inline=False)
          .add_field(name="\n\n**__⚠注意事項⚠__**\n\n",value="認証キーワードは一度しか使用できません。再度認証を行う場合は、再度ボタンを押して新しいキーワードを取得してください。\n\n認証に失敗した場合は、 __キーワードが正しいか、送信先チャンネルが正しいかを確認してください。", inline=False),
        "en": discord.Embed(
            title="Authentication Method Guide",
            description="Welcome to the authentication method guide!\n\n"
                        "In the WeatherPlanet fan server, you can access specific channels by completing authentication.\n\n",
            color=discord.Color.blue()
         ).add_field(name="\n\n**__Step 1__**\n\n",value="To make authentication easier, we have separated it by device type. Please select the appropriate authentication method for your device.\n\nPress the button and if you see '✅️Check your DM', it was successful. If you see '❌️Unable to send DM. Please allow DMs', please check if DMs are allowed.", inline=False)
          .add_field(name="\n\n**__Step 2__**\n\n",value="An authentication keyword will be sent to your DM.\n\nFor mobile devices, long-press to copy the keyword. For PC, press the button on the right to copy it.", inline=False)
          .add_field(name="\n\n**__Step 3__**\n\n",value="Send the keyword to **<#{VERIFY_CHANNEL_ID}>**.\n\nIt doesn't matter if the keyword has symbols like '##'. Also, never share the keyword with others.", inline=False)
          .add_field(name="\n\n**__⚠Notes⚠__**\n\n",value="The authentication keyword can only be used once. If you need to authenticate again, press the button again to get a new keyword.\n\nIf authentication fails, please check if the keyword is correct and if you are sending it to the correct channel.", inline=False),
        "zh": discord.Embed(
            title="认证方法指南",
            description="欢迎来到认证方法指南！\n\n"
                        "在WeatherPlanet粉丝服务器中，通过完成认证可以访问特定频道。\n\n",
            color=discord.Color.blue()
         ).add_field(name="\n\n**__步骤1__**\n\n",value="为了简化认证，我们按设备类型进行了分类。请选择适合您设备的认证方法。\n\n点击按钮，如果看到“✅️请检查您的DM”，则表示成功。如果看到“❌️无法发送DM。请允许DM”，请检查是否允许DM。", inline=False)
          .add_field(name="\n\n**__步骤2__**\n\n",value="认证关键词将发送到您的DM。\n\n对于手机设备，长按以复制关键词。对于PC，请点击右侧按钮复制。", inline=False)
          .add_field(name="\n\n**__步骤3__**\n\n",value="将关键词发送到 **<#{VERIFY_CHANNEL_ID}>**。\n\n关键词可以包含像 '##' 这样的符号。请勿与他人分享关键词。", inline=False)
          .add_field(name="\n\n**__⚠注意事项⚠__**\n\n",value="认证关键词只能使用一次。如果需要重新认证，请再次点击按钮获取新的关键词。\n\n如果认证失败，请检查关键词是否正确，以及是否发送到正确的频道。", inline=False),
        "ko": discord.Embed(
            title="인증 방법 가이드",
            description="인증 방법 가이드에 오신 것을 환영합니다!\n\n"
                        "WeatherPlanet 팬 서버에서는 인증을 완료하면 특정 채널에 접근할 수 있습니다.\n\n",
            color=discord.Color.blue()
         ).add_field(name="\n\n**__1단계__**\n\n",value="인증을 쉽게 하기 위해 기기 유형별로 분리되어 있습니다. 사용 중인 기기에 맞는 인증 방법을 선택하세요.\n\n버튼을 누르고 '✅️DM을 확인하세요'가 표시되면 성공입니다. '❌️DM을 보낼 수 없습니다. DM을 허용하세요'가 표시되면 DM이 허용되어 있는지 확인하세요.", inline=False)
          .add_field(name="\n\n**__2단계__**\n\n",value="인증 키워드가 DM으로 전송됩니다.\n\n모바일 기기는 키워드를 길게 눌러 복사하세요. PC는 오른쪽 버튼을 눌러 복사하세요.", inline=False)
          .add_field(name="\n\n**__3단계__**\n\n",value=" **<#{VERIFY_CHANNEL_ID}>** 에 키워드를 보내세요.\n\n키워드에 '##'와 같은 기호가 있어도 상관없습니다. 또한, 키워드를 절대 다른 사람에게 공유하지 마세요.", inline=False)
          .add_field(name="\n\n**__⚠주의 사항⚠__**\n\n",value="인증 키워드는 한 번만 사용할 수 있습니다. 다시 인증을 해야 하는 경우, 버튼을 다시 눌러 새 키워드를 받아야 합니다.\n\n인증에 실패한 경우, 키워드가 올바른지, 올바른 채널로 보내고 있는지 확인하세요。", inline=False),
        "id": discord.Embed(
            title="Panduan Metode Otentikasi",
            description="Selamat datang di panduan metode otentikasi!\n\n"
                        "Di server penggemar WeatherPlanet, Anda dapat mengakses saluran tertentu dengan menyelesaikan otentikasi.\n\n",
            color=discord.Color.blue()
         ).add_field(name="\n\n**__Langkah 1__**\n\n",value="Untuk memudahkan otentikasi, kami telah memisahkannya berdasarkan jenis perangkat. Silakan pilih metode otentikasi yang sesuai dengan perangkat Anda.\n\nTekan tombol dan jika Anda melihat '✅️Periksa DM Anda', itu berhasil. Jika Anda melihat '❌️Tidak dapat mengirim DM. Harap izinkan DM', silakan periksa apakah DM diizinkan.", inline=False)
          .add_field(name="\n\n**__Langkah 2__**\n\n",value="Kata kunci otentikasi akan dikirim ke DM Anda.\n\nUntuk perangkat seluler, tekan lama untuk menyalin kata kunci. Untuk PC, tekan tombol di sebelah kanan untuk menyalinnya.", inline=False)
          .add_field(name="\n\n**__Langkah 3__**\n\n",value="Kirim kata kunci ke **<#{VERIFY_CHANNEL_ID}>**.\n\nTidak masalah jika kata kunci memiliki simbol seperti '##'. Juga, jangan pernah membagikan kata kunci dengan orang lain.", inline=False)
          .add_field(name="\n\n**__⚠Catatan⚠__**\n\n",value="Kata kunci otentikasi hanya dapat digunakan sekali. Jika Anda perlu melakukan otentikasi lagi, tekan tombol lagi untuk mendapatkan kata kunci baru.\n\nJika otentikasi gagal, periksa apakah kata kunci benar dan apakah Anda mengirimnya ke saluran yang benar.", inline=False)
    }


GUIDES = build_guides()


async def send_dm_with_copy_instruction(user: discord.User, keyword: str, device_type: str) -> bool:
    """端末別の案内DMを送る。送れなければ False。"""
    try:
        if device_type == "mobile":
            await user.send(
                f"【かざま隊の集いの場 認証メッセージ（スマホ向け）】\n"
                f"以下のキーワードを <#{VERIFY_CHANNEL_ID}> に送信してください。\n\n"
                f"次のキーワードを長押ししてコピーしてください。"
            )
            await user.send(f"## {keyword}\n")
        else:
            await user.send(
                f"【かざま隊の集いの場 認証メッセージ（PC向け）】\n"
                f"以下のキーワードを <#{VERIFY_CHANNEL_ID}> に送信してください。\n\n"
                f"```{keyword}```\n"
                "コピーは、右側のボタンを押すとできます。"
            )
        return True
    except discord.Forbidden:
        return False


# ----------------- Persistent View Items -----------------
class MobileVerifyButton(Button):
    def __init__(self):
        super().__init__(
            label="📱認証開始(スマホ版)",
            style=discord.ButtonStyle.success,
            custom_id="wp:verify:mobile"  # 永続化には custom_id が必須
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=False)

        user = interaction.user
        keyword = generate_keyword()
        verification_keywords[user.id] = keyword

        ok = await send_dm_with_copy_instruction(user, keyword, device_type="mobile")
        if ok:
            await interaction.followup.send("✅ DMを確認してください。", ephemeral=True)
        else:
            await interaction.followup.send("❌ DMを送れませんでした。DMの受信を許可してください。", ephemeral=True)


class PCVerifyButton(Button):
    def __init__(self):
        super().__init__(
            label="🖥️認証開始(PC版)",
            style=discord.ButtonStyle.success,
            custom_id="wp:verify:pc"
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=False)

        user = interaction.user
        keyword = generate_keyword()
        verification_keywords[user.id] = keyword

        ok = await send_dm_with_copy_instruction(user, keyword, device_type="pc")
        if ok:
            await interaction.followup.send("✅ DMを確認してください。", ephemeral=True)
        else:
            await interaction.followup.send("❌ DMを送れませんでした。DMの受信を許可してください。", ephemeral=True)


class GuideButton(Button):
    def __init__(self):
        super().__init__(
            label="📖認証方法ガイド / Authn method guide",
            style=discord.ButtonStyle.primary,
            custom_id="wp:verify:guide"
        )

    async def callback(self, interaction: discord.Interaction):
        view = discord.ui.View(timeout=60)
        view.add_item(LanguageSelect())
        await interaction.response.send_message(
            "言語を選択してください / Select a language:",
            view=view,
            ephemeral=True
        )


class LanguageSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="日本語", value="ja", description="日本語のガイド"),
            discord.SelectOption(label="English", value="en", description="Guide in English"),
            discord.SelectOption(label="中文", value="zh", description="中文指南"),
            discord.SelectOption(label="한국어", value="ko", description="한국어 가이드"),
            discord.SelectOption(label="Bahasa Indonesia", value="id", description="Panduan Bahasa Indonesia"),
        ]
        super().__init__(
            placeholder="言語を選択 / Select a language",
            options=options,
            min_values=1,
            max_values=1,
        )

    async def callback(self, interaction: discord.Interaction):
        selected = self.values[0]
        embed = GUIDES.get(selected)
        if embed:
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message("その言語のガイドはありません。", ephemeral=True)


class VerifyView(View):
    """永続ビュー（ボタン3つ）"""
    def __init__(self):
        super().__init__(timeout=None)  # 永続
        self.add_item(MobileVerifyButton())
        self.add_item(PCVerifyButton())
        self.add_item(GuideButton())


# ----------------- Cog 本体 -----------------
class VerificationCog(commands.Cog):
    """認証ビュー＋認証検証を行う Cog"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # 再起動後でもすぐボタンが機能するように、ロード時に永続ビューを登録
    async def cog_load(self):
        self.bot.add_view(VerifyView())

    @commands.command(name="post_authn")
    @commands.has_permissions(administrator=True)
    async def post_verify(self, ctx: commands.Context, channel: Optional[discord.TextChannel] = None):
        """認証パネルを投稿する（管理者）: 例) !post_authn #verify"""
        channel = channel or ctx.channel

        embed = discord.Embed(
            title="ユーザー認証",
            description=(
                f"下のボタンからご利用の端末に応じて認証を開始してください。\n"
                f"DMに認証キーワードが送信されます。DMを開放しているかご確認ください。\n"
                f"キーワードは <#{VERIFY_CHANNEL_ID}>にて送信してください。\n"
            ),
            color=discord.Color.green()
        ).set_footer(text="©2025 かざま隊の集いの場 | authn panel")

        await channel.send(embed=embed, view=VerifyView())
        await ctx.message.add_reaction("✅")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """キーワード検証とロール付与"""
        if message.author.bot or not message.guild:
            return
        if message.channel.id != VERIFY_CHANNEL_ID:
            return

        user_id = message.author.id

        # 整形ルールは元コードを踏襲
        content = (
            message.content.strip()
            .replace('\n', '')
            .replace('##', '')
            .replace('```', '')
            .replace(' ', '')
            .upper()
        )

        if (kw := verification_keywords.get(user_id)) and kw == content:
            role = message.guild.get_role(VERIFIED_ROLE_ID)
            log = self.bot.get_channel(LOG_CHANNEL_ID)

            try:
                await message.delete()
            except discord.Forbidden:
                pass

            if role is not None:
                try:
                    await message.author.add_roles(role, reason="Verification passed")
                except discord.Forbidden:
                    await message.channel.send("⚠ ロール付与に失敗しました。Botの権限を確認してください。", delete_after=8)
            else:
                await message.channel.send("⚠ ロールが見つかりませんでした。VERIFIED_ROLE_ID を確認してください。", delete_after=8)

            try:
                await message.author.send("✅ 認証が完了しました！ようこそ！")

                # ここでログを出す
                joined_at = message.author.joined_at.strftime("%Y-%m-%d %H:%M:%S") if message.author.joined_at else "不明"
                created_at = message.author.created_at.strftime("%Y-%m-%d %H:%M:%S")
                verified_at = discord.utils.utcnow().strftime("%Y-%m-%d %H:%M:%S")

                await log.send(
                    f"✅ {message.author.mention} が認証されました！\n"
                    f"👤ユーザー名: {message.author} (ID: {message.author.id})\n"
                    f"🔍サーバー参加時刻: {joined_at}\n"
                    f"🏵認証時刻: {verified_at}\n"
                    f"📅アカウント作成日: {created_at}"
                )

            except discord.Forbidden:
                pass

            verification_keywords.pop(user_id, None)
        else:
            await self.bot.process_commands(message)


async def setup(bot: commands.Bot):
    await bot.add_cog(VerificationCog(bot))
