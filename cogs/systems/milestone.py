import discord
from discord.ext import commands
import json
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(dotenv_path="ci/.env")  # .envファイルをすべて読み込む
MEMBER_NOTIFY_CHANNEL_ID = int(os.getenv("MEMBER_NOTIFY_CHANNEL_ID"))


class MilestoneCog(commands.Cog, name='Milestone'):
    """メンバー数マイルストーン通知機能"""
    
    def __init__(self, bot):
        self.bot = bot
        self.data_file = 'milestones.json'
        self.achieved_milestones = self.load_milestones()
        self.channel_id = MEMBER_NOTIFY_CHANNEL_ID
    
    def load_milestones(self):
        """保存されたマイルストーンデータを読み込む"""
        if os.path.exists(self.data_file):
            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return set(data)
        return set()
    
    def save_milestones(self):
        """マイルストーンデータを保存"""
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(list(self.achieved_milestones), f, ensure_ascii=False, indent=2)
    
    def get_milestone(self, member_count):
        """
        メンバー数がマイルストーンに該当するか判定
        
        マイルストーン:
        - 100, 200, 300, 400, 500
        - 1000以降は500刻み (1000, 1500, 2000, 2500...)
        """
        milestones = [100, 200, 300, 400, 500]
        
        # 1000以降は500刻み
        if member_count >= 1000:
            if member_count % 500 == 0:
                return member_count
        else:
            # 1000未満は指定の数値
            if member_count in milestones:
                return member_count
        
        return None
    
    @commands.Cog.listener()
    async def on_member_join(self, member):
        """メンバーが参加した時のイベント"""
        guild = member.guild
        member_count = guild.member_count
        milestone = self.get_milestone(member_count)
        milestone_key = f"{guild.id}-{milestone}"
        
        # マイルストーンに達していて、まだ通知していない場合
        if milestone and milestone_key not in self.achieved_milestones:
            self.achieved_milestones.add(milestone_key)
            self.save_milestones()
            
            try:
                channel = self.bot.get_channel(self.channel_id)
                
                if channel is None:
                    channel = await self.bot.fetch_channel(self.channel_id)
                
                if channel:
                    # 埋め込みメッセージを作成
                    embed = discord.Embed(
                        title=f"🎉 {milestone}人達成! 🎉",
                        description=f"サーバーの総人口が **{milestone}人** に達しました!\nご参加いただいている皆様、ありがとうございます!\n今後とも{guild.name}をよろしくお願いいたします！",
                        color=discord.Color.gold(),
                        timestamp=datetime.now()
                    )
                    embed.set_footer(text="©2025-2026 かざま隊の集いの場")
                    
                    await channel.send(embed=embed)
                    print(f"✅ {milestone}人達成の通知を送信しました ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
                    
            except Exception as e:
                print(f"❌ 通知送信エラー: {e}")
                # エラーが起きた場合は記録から削除して次回リトライできるようにする
                self.achieved_milestones.discard(milestone_key)
                self.save_milestones()
    
    @commands.command(name='milestone_info')
    @commands.has_permissions(administrator=True)
    async def milestone_info(self, ctx):
        """現在のマイルストーン情報を表示（管理者のみ）"""
        guild = ctx.guild
        current_count = guild.member_count
        
        # 次のマイルストーンを計算
        next_milestone = None
        milestones = [50, 100, 200, 300, 400, 500]
        
        for m in milestones:
            if current_count < m:
                next_milestone = m
                break
        
        if next_milestone is None:
            # 1000以降の次のマイルストーンを計算
            next_milestone = ((current_count // 500) + 1) * 500
        
        remaining = next_milestone - current_count
        
        embed = discord.Embed(
            title="📊 マイルストーン情報",
            color=discord.Color.blue()
        )
        embed.add_field(name="現在のメンバー数", value=f"{current_count}人", inline=False)
        embed.add_field(name="次のマイルストーン", value=f"{next_milestone}人", inline=True)
        embed.add_field(name="あと", value=f"{remaining}人", inline=True)
        embed.add_field(
            name="達成済みマイルストーン",
            value=f"{len(self.achieved_milestones)}件",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(name='milestone_reset')
    @commands.has_permissions(administrator=True)
    async def milestone_reset(self, ctx):
        """マイルストーンデータをリセット（管理者のみ）"""
        self.achieved_milestones.clear()
        self.save_milestones()
        
        embed = discord.Embed(
            title="🔄 リセット完了",
            description="マイルストーンデータをリセットしました。",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)


async def setup(bot):
    """Cogのセットアップ関数"""
    await bot.add_cog(MilestoneCog(bot))