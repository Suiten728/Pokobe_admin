# cogs/test/welcome_test.py
# ウェルカムカード画像の見た目確認用（一時ファイル）
# /welcome で自分自身に対してカードを生成して送信する

import discord
from discord.ext import commands
from discord import app_commands
import io
import aiohttp
from PIL import Image, ImageDraw, ImageFont


WELCOME_BG_PATH = "assets/welcome_bg.png"


def _get_font(size: int) -> ImageFont.FreeTypeFont:
    candidates = [
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJKjp-Regular.otf",
        "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


async def generate_welcome_card(member: discord.Member) -> bytes:
    bg = Image.open(WELCOME_BG_PATH).convert("RGBA")
    bg_w, bg_h = bg.size

    async with aiohttp.ClientSession() as session:
        async with session.get(str(member.display_avatar.url)) as resp:
            avatar_bytes = await resp.read()

    avatar_size = min(bg_h // 2, 350)
    avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA").resize((avatar_size, avatar_size))
    mask = Image.new("L", (avatar_size, avatar_size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, avatar_size, avatar_size), fill=255)
    avatar.putalpha(mask)

    av_x = 900
    av_y = 250
    bg.paste(avatar, (av_x, av_y), avatar)

    draw = ImageDraw.Draw(bg)
    font_name = _get_font(60)
    font_tag  = _get_font(40)

    name_text = member.display_name
    tag_text  = f"@{member.name}"
    text_x    = av_x + avatar_size + 20
    name_y    = av_y + avatar_size // 2 - 28
    tag_y     = name_y + 42

    draw.text((text_x + 2, name_y + 2), name_text, font=font_name, fill=(0, 0, 0, 160))
    draw.text((text_x + 2, tag_y  + 2), tag_text,  font=font_tag,  fill=(0, 0, 0, 120))
    draw.text((text_x, name_y), name_text, font=font_name, fill=(255, 255, 255, 255))
    draw.text((text_x, tag_y),  tag_text,  font=font_tag,  fill=(200, 200, 200, 220))

    output = io.BytesIO()
    bg.convert("RGBA").save(output, format="PNG")
    output.seek(0)
    return output.read()


class WelcomeTestCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="welcome", description="ウェルカムカードの見た目を確認する（テスト用）")
    async def welcome_preview(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        try:
            img_bytes = await generate_welcome_card(interaction.user)
            file = discord.File(io.BytesIO(img_bytes), filename="welcome_card.png")
            await interaction.followup.send(
                content="ウェルカムカードのプレビューです。位置・サイズを確認してください。",
                file=file,
                ephemeral=True,
            )
        except Exception as e:
            await interaction.followup.send(f"エラー: `{e}`", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(WelcomeTestCog(bot))