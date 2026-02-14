import discord
from discord.ext import commands
from discord.ui import View, Button


class AIControlView(View):
    """AI制御用のビューボタン"""
    
    def __init__(self, bot):
        super().__init__(timeout=300)  # 5分でタイムアウト
        self.bot = bot

    @discord.ui.button(label="🟢 AI起動", style=discord.ButtonStyle.success, custom_id="ai_on")
    async def ai_on_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """AIを起動"""
        # 管理者権限チェック
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "⚠️ この操作には管理者権限が必要です。",
                ephemeral=True
            )
            return
        
        self.bot.talk_enabled = True
        
        # Embedを更新
        embed = self.create_status_embed()
        await interaction.response.edit_message(embed=embed, view=self)
        
        # 確認メッセージ
        await interaction.followup.send(
            "✅ **AIを起動しました。**",
            ephemeral=True
        )

    @discord.ui.button(label="🔴 AI停止", style=discord.ButtonStyle.danger, custom_id="ai_off")
    async def ai_off_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """AIを停止"""
        # 管理者権限チェック
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "⚠️ この操作には管理者権限が必要です。",
                ephemeral=True
            )
            return
        
        self.bot.talk_enabled = False
        
        # Embedを更新
        embed = self.create_status_embed()
        await interaction.response.edit_message(embed=embed, view=self)
        
        # 確認メッセージ
        await interaction.followup.send(
            "⚠️ **AIを緊急停止しました。**",
            ephemeral=True
        )

    @discord.ui.button(label="🔄 ステータス更新", style=discord.ButtonStyle.primary, custom_id="ai_refresh")
    async def ai_refresh_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """ステータスを更新"""
        embed = self.create_status_embed()
        await interaction.response.edit_message(embed=embed, view=self)
        
        await interaction.followup.send(
            "🔄 **ステータスを更新しました。**",
            ephemeral=True
        )

    def create_status_embed(self):
        """現在のステータスを表示するEmbedを作成"""
        status = "🟢 **稼働中**" if self.bot.talk_enabled else "🔴 **停止中**"
        color = discord.Color.green() if self.bot.talk_enabled else discord.Color.red()
        
        embed = discord.Embed(
            title="🤖 AI制御パネル",
            description=f"現在のAI状態: {status}",
            color=color
        )
        
        embed.add_field(
            name="💡 使い方",
            value=(
                "🟢 **AI起動**: AIを起動します（管理者のみ）\n"
                "🔴 **AI停止**: AIを緊急停止します（管理者のみ）\n"
                "🔄 **ステータス更新**: 現在のステータスを更新します"
            ),
            inline=False
        )
        
        # 統計情報を取得して表示
        try:
            stats = self.get_statistics_from_bot()
            
            # 統計情報フィールド
            stats_text = (
                f"📊 **総利用回数**: {stats['total_messages']:,}回\n"
                f"📅 **今日の利用**: {stats['today_messages']:,}回\n"
            )
            
            if stats['last_used']:
                from datetime import datetime
                try:
                    last_time = datetime.fromisoformat(stats['last_used'])
                    stats_text += f"🕐 **最終利用**: {last_time.strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
                except:
                    stats_text += f"🕐 **最終利用**: {stats['last_used']}\n"
            
            embed.add_field(
                name="📈 利用統計",
                value=stats_text,
                inline=False
            )
            
            # チャンネル別統計（利用回数が多い上位3件）
            if stats['channel_stats']:
                channel_text = ""
                for i, (channel_id, count) in enumerate(stats['channel_stats'], 1):
                    channel = self.bot.get_channel(int(channel_id))
                    channel_name = channel.name if channel else f"ID: {channel_id}"
                    channel_text += f"{i}. #{channel_name}: {count:,}回\n"
                
                embed.add_field(
                    name="🏆 チャンネル別利用TOP3",
                    value=channel_text,
                    inline=False
                )
        except Exception as e:
            print(f"統計表示エラー: {e}")
        
        embed.set_footer(text="風真いろはAI v1.14 制御システム")
        
        return embed
    
    def get_statistics_from_bot(self):
        """Botから統計情報を取得"""
        import sqlite3
        from datetime import datetime
        
        DB_PATH = "data/ai_memory.db"
        
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            
            # 総メッセージ数（ユーザーからのメッセージのみ）
            c.execute("SELECT COUNT(*) FROM memory WHERE role='user'")
            total_messages = c.fetchone()[0]
            
            # 今日のメッセージ数
            today = datetime.utcnow().date().isoformat()
            c.execute(
                "SELECT COUNT(*) FROM memory WHERE role='user' AND DATE(timestamp) = ?",
                (today,)
            )
            today_messages = c.fetchone()[0]
            
            # 最終利用時刻
            c.execute("SELECT MAX(timestamp) FROM memory WHERE role='user'")
            last_used = c.fetchone()[0]
            
            # チャンネル別利用数（上位3件）
            c.execute("""
                SELECT channel_id, COUNT(*) as count 
                FROM memory 
                WHERE role='user' 
                GROUP BY channel_id 
                ORDER BY count DESC 
                LIMIT 3
            """)
            channel_stats = c.fetchall()
            
            conn.close()
            
            return {
                "total_messages": total_messages,
                "today_messages": today_messages,
                "last_used": last_used,
                "channel_stats": channel_stats
            }
        except Exception as e:
            print(f"統計取得エラー: {e}")
            return {
                "total_messages": 0,
                "today_messages": 0,
                "last_used": None,
                "channel_stats": []
            }


class AIControlCog(commands.Cog):
    """AI制御用のCog"""
    
    def __init__(self, bot):
        self.bot = bot
        
        # TalkCog が最初から稼働状態であることを保証
        if not hasattr(self.bot, "talk_enabled"):
            self.bot.talk_enabled = True

    @commands.command(name="ai-ctrl")
    async def ai_ctrl(self, ctx):
        """AI制御パネルを表示"""
        view = AIControlView(self.bot)
        embed = view.create_status_embed()
        
        await ctx.send(embed=embed, view=view)


async def setup(bot):
    await bot.add_cog(AIControlCog(bot))