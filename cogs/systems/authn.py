import os
import random
import string
from typing import Optional
import discord
from discord.ext import commands
from discord.ui import View, Button, Select
from dotenv import load_dotenv

load_dotenv(dotenv_path="ci/.env") # .envファイルをすべて読み込む
SERVER_OWNER_ID = int(os.getenv("SERVER_OWNER_ID"))
VERIFY_CHANNEL_ID = int(os.getenv("VERIFY_CHANNEL_ID"))
VERIFIED_ROLE_ID  = int(os.getenv("VERIFIED_ROLE_ID"))
LOG_CHANNEL_ID = int(os.getenv("AUTH_LOG_CHANNEL_ID"))

# ユーザー -> 発行済みキーワード（再起動で消える想定）
verification_keywords: dict[int, str] = {}


def generate_keyword(length: int = 6) -> str:
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))


# ---- ガイド埋め込み（簡略化。必要なら元の長文に差し替え可） ----
def build_guides():
    owner = f"<@{SERVER_OWNER_ID}>"

    def pages(steps):
        embeds = []
        total = len(steps)
        for i, (title, desc) in enumerate(steps, start=1):
            e = discord.Embed(
                title=title,
                description=desc.format(
                    channel=f"<#{VERIFY_CHANNEL_ID}>",
                    SERVER_OWNER=owner
                ),
                color=discord.Color.blue()
            )
            e.set_footer(text=f"{i} / {total}")
            embeds.append(e)
        return embeds

    return {
        "jp": pages([
            ("📖 認証方法ガイド",
             "このサーバーでは、セキュリティ上認証パネルを設置しています。\n"
             "認証を行うことで **閲覧・発言できるチャンネルが開放** されます。\n\n"
             "認証ができなかった場合は、{SERVER_OWNER} までご連絡ください。"),
            ("🟢 ステップ1",
             "認証の利便性を考慮し、デバイスごとにボタンが分かれています。\n"
             "ご利用の端末に応じた **認証開始ボタン** を押してください。\n\n"
             "✅ DMが届けば成功です\n"
             "❌ 届かない場合は **DMを許可** してください"),
            ("🟡 ステップ2",
             "DMに **認証キーワード** が送信されます。\n\n"
             "・スマホ：キーワード部分を長押ししてコピー\n"
             "・PC：コードブロック右上のボタンを押してコピー"),
            ("🔵 ステップ3",
             "{channel} に **キーワードを送信** してください。\n\n"
             "記号（##など）が付いていても問題ありません。"),
            ("⚠ 注意事項",
             "・キーワードは **1回限り** です。認証後は無効になります。\n"
             "・認証に失敗した場合、キーワードを再発行してください。\n"
             "・他人に絶対に共有しないでください。")
        ]),

        "en": pages([
            ("📖 Authentication Guide",
             "This server uses an authentication panel for security purposes.\n"
             "By completing authentication, **viewing and chatting channels will be unlocked**.\n\n"
             "If authentication fails, please contact {SERVER_OWNER}."),
            ("🟢 Step 1",
             "Buttons are separated by device for convenience.\n"
             "Press the **authentication button** that matches your device.\n\n"
             "✅ DM received = success\n"
             "❌ If not, please **allow DMs**"),
            ("🟡 Step 2",
             "You will receive an **authentication keyword** via DM.\n\n"
             "• Mobile: long-press the keyword to copy\n"
             "• PC: click the copy button on the code block"),
            ("🔵 Step 3",
             "Send the **keyword** to {channel}.\n\n"
             "Symbols such as ## do not matter."),
            ("⚠ Notes",
             "• Keywords are **one-time use only**.\n"
             "• If authentication fails, reissue a new keyword.\n"
             "• Never share your keyword with others.")
        ]),

        "zh": pages([
            ("📖 认证指南",
             "本服务器出于安全原因设置了认证面板。\n"
             "完成认证后，**即可查看和发言频道**。\n\n"
             "若认证失败，请联系 {SERVER_OWNER}。"),
            ("步骤 1",
             "根据设备类型区分了不同的认证按钮。\n"
             "请选择适合您设备的 **认证按钮**。\n\n"
             "✅ 收到DM表示成功\n"
             "❌ 未收到请开启DM"),
            ("步骤 2",
             "认证关键词将通过 DM 发送。\n\n"
             "・手机：长按复制\n"
             "・PC：点击代码框右上角复制"),
            ("步骤 3",
             "请将关键词发送到 {channel}。\n\n"
             "包含符号（如 ##）也没有问题。"),
            ("注意事项",
             "・关键词 **只能使用一次**。\n"
             "・失败时请重新获取关键词。\n"
             "・请勿与他人共享。")
        ]),

        "ko": pages([
            ("📖 인증 가이드",
             "이 서버는 보안을 위해 인증 패널을 사용합니다.\n"
             "인증을 완료하면 **채널 열람 및 채팅이 가능** 합니다.\n\n"
             "인증에 실패하면 {SERVER_OWNER} 에게 문의하세요."),
            ("1단계",
             "기기별로 인증 버튼이 나뉘어 있습니다.\n"
             "사용 중인 기기에 맞는 **인증 버튼** 을 누르세요.\n\n"
             "✅ DM 수신 = 성공\n"
             "❌ 수신 안 되면 DM 허용"),
            ("2단계",
             "DM으로 **인증 키워드** 가 전송됩니다.\n\n"
             "・모바일: 길게 눌러 복사\n"
             "・PC: 코드 블록 복사 버튼 클릭"),
            ("3단계",
             "{channel} 에 키워드를 보내세요.\n\n"
             "기호(## 등)가 붙어 있어도 문제 없습니다."),
            ("주의사항",
             "・키워드는 **1회용** 입니다.\n"
             "・실패 시 재발급하세요。\n"
             "・절대 공유하지 마세요.")
        ]),

        "fr": pages([
            ("📖 Guide d’authentification",
             "Ce serveur utilise un panneau d’authentification pour des raisons de sécurité.\n"
             "Après authentification, **les salons seront accessibles**.\n\n"
             "En cas de problème, contactez {SERVER_OWNER}."),
            ("Étape 1",
             "Les boutons sont séparés par type d’appareil.\n"
             "Appuyez sur le **bouton approprié**.\n\n"
             "✅ DM reçu = succès\n"
             "❌ Autorisez les DM si nécessaire"),
            ("Étape 2",
             "Un **mot-clé d’authentification** sera envoyé par DM."),
            ("Étape 3",
             "Envoyez le mot-clé dans {channel}."),
            ("Attention",
             "• Mot-clé **à usage unique**.\n"
             "• Régénérez-le en cas d’échec.\n"
             "• Ne le partagez jamais.")
        ]),

        "de": pages([
            ("📖 Authentifizierungsanleitung",
             "Dieser Server nutzt ein Authentifizierungspanel aus Sicherheitsgründen.\n"
             "Nach erfolgreicher Authentifizierung werden **Kanäle freigeschaltet**.\n\n"
             "Bei Problemen wenden Sie sich an {SERVER_OWNER}."),
            ("Schritt 1",
             "Buttons sind nach Gerätetyp getrennt.\n"
             "Drücken Sie den **passenden Button**."),
            ("Schritt 2",
             "Sie erhalten ein **Authentifizierungskennwort** per DM."),
            ("Schritt 3",
             "Senden Sie das Kennwort an {channel}."),
            ("Hinweis",
             "• Einmalig gültig.\n"
             "• Bei Fehler neu generieren.\n"
             "• Nicht weitergeben.")
        ]),

        "id": pages([
            ("📖 Panduan Otentikasi",
             "Server ini menggunakan panel otentikasi demi keamanan.\n"
             "Setelah otentikasi, **saluran akan terbuka**.\n\n"
             "Jika gagal, hubungi {SERVER_OWNER}."),
            ("Langkah 1",
             "Tombol dibedakan berdasarkan perangkat.\n"
             "Tekan **tombol yang sesuai**."),
            ("Langkah 2",
             "Anda akan menerima **kata sandi otentikasi** via DM."),
            ("Langkah 3",
             "Kirim ke {channel}."),
            ("Catatan",
             "• Sekali pakai.\n"
             "• Buat ulang jika gagal.\n"
             "• Jangan dibagikan.")
        ]),

        "es": pages([
            ("📖 Guía de Autenticación",
             "Este servidor utiliza un panel de autenticación por seguridad.\n"
             "Tras autenticarte, **los canales se desbloquearán**.\n\n"
             "Si falla, contacta a {SERVER_OWNER}."),
            ("Paso 1",
             "Los botones están separados por dispositivo.\n"
             "Pulsa el **botón adecuado**."),
            ("Paso 2",
             "Recibirás una **clave de autenticación** por DM."),
            ("Paso 3",
             "Envíala a {channel}."),
            ("Nota",
             "• Uso único.\n"
             "• Regenera si falla.\n"
             "• No compartir.")
        ]),

        "pt_BR": pages([
            ("📖 Guia de Autenticação",
             "Este servidor utiliza um painel de autenticação por segurança.\n"
             "Após autenticar, **os canais serão liberados**.\n\n"
             "Se falhar, entre em contato com {SERVER_OWNER}."),
            ("Passo 1",
             "Os botões são separados por dispositivo.\n"
             "Pressione o **botão correto**."),
            ("Passo 2",
             "Você receberá uma **chave de autenticação** por DM."),
            ("Passo 3",
             "Envie para {channel}."),
            ("Aviso",
             "• Uso único.\n"
             "• Regerar se falhar.\n"
             "• Não compartilhe.")
        ])
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
            label="📖 認証方法ガイド / Authn method guide",
            style=discord.ButtonStyle.primary,
            custom_id="wp:verify:guide"
        )

    async def callback(self, interaction: discord.Interaction):
        view = discord.ui.View(timeout=60)
        view.add_item(LanguageSelect())
        await interaction.response.send_message(
            "🌐 言語を選択してください / Select a language:",
            view=view,
            ephemeral=True
        )


 # ---- Guide言語選択用Select ----
class LanguageSelect(Select):
    def __init__(self):
        super().__init__(
            placeholder="🌐 言語を選択 / Select a language",
            options=[
                discord.SelectOption(label="日本語", value="jp",emoji="🇯🇵"),
                discord.SelectOption(label="English", value="en",emoji="🇺🇸"),
                discord.SelectOption(label="中文", value="zh",emoji="🇨🇳"),
                discord.SelectOption(label="한국어", value="ko",emoji="🇰🇷"),
                discord.SelectOption(label="Français", value="fr",emoji="🇫🇷"),
                discord.SelectOption(label="Deutsch", value="de",emoji="🇩🇪"),
                discord.SelectOption(label="Bahasa Indonesia", value="id",emoji="🇮🇩"),
                discord.SelectOption(label="Español", value="es",emoji="🇪🇸"),
                discord.SelectOption(label="Português (BR)", value="pt_BR",emoji="🇧🇷"),
            ]
        )

    async def callback(self, interaction: discord.Interaction):
        pages = GUIDES[self.values[0]]
        await interaction.response.send_message(
            embed=pages[0],
            view=GuidePager(pages),
            ephemeral=True
        )


# ----Guideのページ送り用View----
class GuidePager(View):
    def __init__(self, embeds):
        super().__init__(timeout=120)
        self.embeds = embeds
        self.index = 0

    async def update(self, interaction):
        await interaction.response.edit_message(
            embed=self.embeds[self.index],
            view=self
        )

    @discord.ui.button(label="⬅", style=discord.ButtonStyle.secondary)
    async def prev(self, interaction: discord.Interaction, _):
        self.index = (self.index - 1) % len(self.embeds)
        await self.update(interaction)

    @discord.ui.button(label="➡", style=discord.ButtonStyle.secondary)
    async def next(self, interaction: discord.Interaction, _):
        self.index = (self.index + 1) % len(self.embeds)
        await self.update(interaction)


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
                f"キーワードは <#{VERIFY_CHANNEL_ID}>にて送信してください。\n\n"
                f"Please start authentication using the buttons below according to your device.\n"
                f"The keyword will be sent to your DM. Please check if your DM is open.\n"
                f"Please send the keyword to <#{VERIFY_CHANNEL_ID}>."
            ),
            color=discord.Color.green()
        ).set_footer(text="©2025-2026 かざま隊の集いの場")

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
                    await message.channel.send("⚠ ロール付与に失敗しました。サーバーオーナーまでご連絡ください。", delete_after=8)
            else:
                await message.channel.send("⚠ ロールが見つかりませんでした。サーバーオーナーまでご連絡ください。さ", delete_after=8)

            try:
                await message.author.send("✅ 認証が完了しました！ようこそ！")

                # ここでログを出す
                joined_at = message.author.joined_at.strftime("%Y-%m-%d %H:%M:%S") if message.author.joined_at else "不明"
                created_at = message.author.created_at.strftime("%Y-%m-%d %H:%M:%S")
                verified_at = discord.utils.utcnow().strftime("%Y-%m-%d %H:%M:%S")

                await log.send(
                    f"✅ {message.author.mention} が認証されました！\n"
                    f"👤ユーザー名: {message.author} (ID: {message.author.id})\n"
                    f"📅アカウント作成日: {created_at}"
                    f"🔍サーバー参加時刻: {joined_at}\n"
                    f"🏵認証時刻: {verified_at}\n"
                )

            except discord.Forbidden:
                pass

            verification_keywords.pop(user_id, None)
        else:
            try:
                await message.author.send("❌ 認証に失敗しました。キーワードが正しいか、送信先チャンネルが正しいか確認してください。", ephemeral=True)
            except discord.Forbidden:
                pass


async def setup(bot: commands.Bot):
    await bot.add_cog(VerificationCog(bot))

