import discord
from discord.ext import commands
from utils.components_v2 import (
    MessageBuilder, Section, Button, Select, SelectOption
)

class TestCV2(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="cv2test")
    @commands.command()
    async def cv2_cmd(self, ctx):
        builder = MessageBuilder()

        builder.add_section(
            Section(
                label="操作メニュー",
                description="Embed内に配置されたように見えるボタン＆セレクト",
                buttons=[
                    Button("OK", "ok"),
                    Button("Cancel", "cancel")
                ],
                selects=[
                    Select("選んでください", "sel", [
                        SelectOption("A"),
                        SelectOption("B")
                    ])
                ]
            )
        )

        embeds, views = builder.build()

        # 1つのメッセージにまとめて送信
        msg = await ctx.send(embeds=embeds, view=views[0])


    # コンポーネント応答
    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.component:
            return

        cid = interaction.data.get("custom_id")

        if cid == "ok":
            await interaction.response.send_message("OK!", ephemeral=True)

        elif cid == "cancel":
            await interaction.response.send_message("キャンセル！", ephemeral=True)

        elif cid == "sel":
            value = interaction.data["values"][0]
            await interaction.response.send_message(f"選択: {value}", ephemeral=True)


# ==== これが重要（B方式） ====
async def setup(bot):
    await bot.add_cog(TestCV2(bot))
