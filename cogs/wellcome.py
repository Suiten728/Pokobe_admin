import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont
import aiohttp
import io

CHANNEL_ID = 1363499582578757752

LANGUAGES = {
    "ja": {
        "title": "🌸 ようこそ！",
        "description": "サーバーへようこそ！以下のボタンから確認してください。",
        "rules": "📜 ルールはこちら",
        "intro": "🙋‍♂️ 自己紹介はこちら"
    },
    "en": {
        "title": "🌸 Welcome!",
        "description": "Welcome to the server! Please check the buttons below.",
        "rules": "📜 Rules",
        "intro": "🙋‍♂️ Introduce Yourself"
    },
    "zh": {
        "title": "🌸 欢迎！",
        "description": "欢迎加入服务器！请点击下方按钮查看。",
        "rules": "📜 规则",
        "intro": "🙋‍♂️ 自我介绍"
    }
}


# --- ボタン + 言語選択付きのView ---
class WelcomeView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

        # リンクボタンは add_item() で追加
        self.add_item(discord.ui.Button(
            label="📜 ルールはこちら",
            style=discord.ButtonStyle.link,
            url="https://discord.com/channels/1363116304764112966/1363444914360156233"
        ))

        self.add_item(discord.ui.Button(
            label="🙋‍♂️ 自己紹介はこちら",
            style=discord.ButtonStyle.link,
            url="https://discord.com/channels/1363116304764112966/1363511340605509692"
        ))

        # 言語選択メニューを追加
        self.add_item(LanguageSelect())



class LanguageSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="日本語", value="ja", emoji="🇯🇵"),
            discord.SelectOption(label="English", value="en", emoji="🇺🇸"),
            discord.SelectOption(label="中文", value="zh", emoji="🇨🇳"),
        ]
        super().__init__(placeholder="🌐 言語を選択 / Select Language", options=options, custom_id="lang_select")

    async def callback(self, interaction: discord.Interaction):
        lang_code = self.values[0]
        content = LANGUAGES[lang_code]

        embed = discord.Embed(
            title=content["title"],
            description=content["description"],
            color=discord.Color.blurple()
        )

        new_view = WelcomeView()
        for item in new_view.children:
            if isinstance(item, discord.ui.Button):
                if "rules" in item.label.lower() or "ルール" in item.label or "规则" in item.label:
                    item.label = content["rules"]
                if "intro" in item.label.lower() or "紹介" in item.label or "介绍" in item.label:
                    item.label = content["intro"]

        await interaction.response.edit_message(embed=embed, view=new_view)


# --- 画像生成関数 ---
async def generate_welcome_image(member: discord.Member) -> discord.File:
    # ベース画像
    base = Image.open("assets/welcome_bg.png").convert("RGBA")  # 背景ファイルは事前に用意

    # ユーザーアイコンを取得
    async with aiohttp.ClientSession() as session:
        async with session.get(member.display_avatar.url) as resp:
            avatar_bytes = await resp.read()
    avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
    avatar = avatar.resize((200, 200))  # サイズ調整

    # 丸型に切り抜き
    mask = Image.new("L", avatar.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, avatar.size[0], avatar.size[1]), fill=255)
    avatar.putalpha(mask)

    # 貼り付け
    base.paste(avatar, (50, 50), avatar)

    # テキスト描画
    draw = ImageDraw.Draw(base)
    font_big = ImageFont.truetype("assets/NotoSansJP-Bold.otf", 60)
    font_small = ImageFont.truetype("assets/NotoSansJP-Regular.otf", 40)

    # 名前
    draw.text((300, 70), member.display_name, font=font_big, fill=(255, 255, 255, 255))
    # 固定文言
    draw.text((300, 150), "かざま隊の集いの場へようこそ！", font=font_small, fill=(255, 255, 255, 255))
    # 参加人数
    member_count = member.guild.member_count
    draw.text((300, 220), f"あなたは {member_count} 人目の仲間です！", font=font_small, fill=(255, 255, 255, 255))

    # 保存
    output = io.BytesIO()
    base.save(output, format="PNG")
    output.seek(0)
    return discord.File(fp=output, filename="welcome.png")


# --- Cog本体 ---
class WelcomeCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        lang_code = "ja"
        content = LANGUAGES[lang_code]

        embed = discord.Embed(
            title=content["title"],
            description=content["description"],
            color=discord.Color.blurple()
        )
        embed.set_image(url="attachment://welcome.png")  # 生成画像を添付する

        channel = self.get_channel(CHANNEL_ID)
        if channel:
            file = await generate_welcome_image(member)
            await channel.send(
                content=f"{member.mention} さんが参加しました！ 🎉",
                embed=embed,
                file=file,
                view=WelcomeView()
            )

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(WelcomeView())


async def setup(bot: commands.Bot):
    await bot.add_cog(WelcomeCog(bot))
