import disnake
from disnake.ext import commands
import os
import json
import datetime
from typing import Optional, Dict, List
from dotenv import load_dotenv

load_dotenv()


class InviteLogger(commands.Cog):
    """Система отслеживания приглашений и статистики пользователей"""
    
    def __init__(self, bot):
        self.bot = bot
        self.invites: Dict[int, List[disnake.Invite]] = {}
        self.invite_logs_channel_id = int(os.getenv("INVITE_LOGS_CHANNEL_ID", 0))
        self.invite_data_dir = "invite_data"
        
        os.makedirs(self.invite_data_dir, exist_ok=True)

    async def cog_load(self):
        """Загрузка данных о приглашениях при запуске"""
        await self.bot.wait_until_ready()
        for guild in self.bot.guilds:
            try:
                self.invites[guild.id] = await guild.invites()
                print(f"✅ Загружено {len(self.invites[guild.id])} приглашений для сервера {guild.name}")
            except Exception as e:
                print(f"❌ Ошибка загрузки приглашений для {guild.name}: {e}")
                self.invites[guild.id] = []

    def load_invite_data(self, user_id: int) -> Dict:
        """Загрузка данных о приглашениях пользователя"""
        file_path = os.path.join(self.invite_data_dir, f"{user_id}.json")
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return {"total_invites": 0, "invited_users": []}

    def save_invite_data(self, user_id: int, data: Dict) -> None:
        """Сохранение данных о приглашениях пользователя"""
        file_path = os.path.join(self.invite_data_dir, f"{user_id}.json")
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"❌ Ошибка сохранения данных для пользователя {user_id}: {e}")

    def find_invite_by_code(self, guild_invites: List[disnake.Invite], code: str) -> Optional[disnake.Invite]:
        """Поиск приглашения по коду"""
        return next((invite for invite in guild_invites if invite.code == code), None)

    def get_invite_difference(self, old_invites: List[disnake.Invite], 
                             new_invites: List[disnake.Invite]) -> Optional[disnake.Invite]:
        """Определение использованного приглашения"""
        for new_invite in new_invites:
            old_invite = self.find_invite_by_code(old_invites, new_invite.code)
            if old_invite and new_invite.uses > old_invite.uses:
                return new_invite
        return None

    def format_time_ago(self, timestamp: datetime.datetime) -> str:
        """Форматирование времени в читаемый вид"""
        now = datetime.datetime.utcnow()
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=datetime.timezone.utc)
        
        diff = now.replace(tzinfo=datetime.timezone.utc) - timestamp
        days = diff.days
        
        if days >= 365:
            years = days // 365
            return f"{years} {'год' if years == 1 else 'года' if years < 5 else 'лет'}"
        elif days >= 30:
            months = days // 30
            return f"{months} {'месяц' if months == 1 else 'месяца' if months < 5 else 'месяцев'}"
        elif days > 0:
            return f"{days} {'день' if days == 1 else 'дня' if days < 5 else 'дней'}"
        else:
            hours = diff.seconds // 3600
            if hours > 0:
                return f"{hours} {'час' if hours == 1 else 'часа' if hours < 5 else 'часов'}"
            else:
                minutes = diff.seconds // 60
                return f"{minutes} {'минуту' if minutes == 1 else 'минуты' if minutes < 5 else 'минут'}"

    @commands.Cog.listener()
    async def on_member_join(self, member: disnake.Member):
        """Обработка входа нового участника"""
        try:
            guild = member.guild
            current_invites = await guild.invites()
            old_invites = self.invites.get(guild.id, [])
            used_invite = self.get_invite_difference(old_invites, current_invites)
            
            self.invites[guild.id] = current_invites
            
            logs_channel = guild.get_channel(self.invite_logs_channel_id)
            if not logs_channel:
                return

            account_age = self.format_time_ago(member.created_at)
            
            embed = disnake.Embed(
                title="👋 Новый участник!",
                color=disnake.Color.green(),
                timestamp=datetime.datetime.utcnow()
            )
            
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.add_field(name="Участник", value=f"{member.mention}\n`{member}`", inline=False)
            
            if used_invite and used_invite.inviter:
                inviter = used_invite.inviter
                inviter_data = self.load_invite_data(inviter.id)
                inviter_data["total_invites"] += 1
                inviter_data["invited_users"].append({
                    "user_id": member.id,
                    "username": str(member),
                    "joined_at": datetime.datetime.utcnow().isoformat()
                })
                self.save_invite_data(inviter.id, inviter_data)
                
                embed.add_field(
                    name="📨 Пригласил",
                    value=f"{inviter.mention}\n`{inviter}`",
                    inline=True
                )
                embed.add_field(
                    name="📊 Всего приглашений",
                    value=f"`{inviter_data['total_invites']}`",
                    inline=True
                )
            else:
                embed.add_field(
                    name="📨 Пригласил",
                    value="Неизвестно",
                    inline=False
                )
            
            embed.add_field(
                name="🆔 ID пользователя",
                value=f"`{member.id}`",
                inline=True
            )
            embed.add_field(
                name="📅 Аккаунт создан",
                value=f"{account_age} назад",
                inline=True
            )
            embed.add_field(
                name="👥 Участников на сервере",
                value=f"`{guild.member_count}`",
                inline=True
            )
            
            embed.set_footer(text=f"ID: {member.id}")
            
            await logs_channel.send(
                content=f"Добро пожаловать, {member.mention}! Надеюсь, вы к нам надолго :)",
                embed=embed
            )
            
        except Exception as e:
            print(f"❌ Ошибка в on_member_join: {e}")

    @commands.Cog.listener()
    async def on_member_remove(self, member: disnake.Member):
        """Обработка выхода участника"""
        try:
            guild = member.guild
            logs_channel = guild.get_channel(self.invite_logs_channel_id)
            if not logs_channel:
                return

            inviter = None
            inviter_data = None
            
            for filename in os.listdir(self.invite_data_dir):
                if not filename.endswith(".json"):
                    continue
                    
                user_id = int(filename.replace(".json", ""))
                user_data = self.load_invite_data(user_id)
                
                for invited_user in user_data.get("invited_users", []):
                    if invited_user["user_id"] == member.id:
                        inviter = guild.get_member(user_id)
                        user_data["invited_users"] = [
                            u for u in user_data["invited_users"] 
                            if u["user_id"] != member.id
                        ]
                        user_data["total_invites"] = max(0, user_data["total_invites"] - 1)
                        self.save_invite_data(user_id, user_data)
                        inviter_data = user_data
                        break
                
                if inviter:
                    break
            
            embed = disnake.Embed(
                title="👋 Участник покинул сервер",
                color=disnake.Color.red(),
                timestamp=datetime.datetime.utcnow()
            )
            
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.add_field(name="Участник", value=f"{member.mention}\n`{member}`", inline=False)
            
            if inviter and inviter_data:
                embed.add_field(
                    name="📨 Пригласил",
                    value=f"{inviter.mention}\n`{inviter}`",
                    inline=True
                )
                embed.add_field(
                    name="📊 Осталось приглашений",
                    value=f"`{inviter_data['total_invites']}`",
                    inline=True
                )
            else:
                embed.add_field(
                    name="📨 Пригласил",
                    value="Неизвестно",
                    inline=False
                )
            
            embed.add_field(
                name="👥 Участников на сервере",
                value=f"`{guild.member_count}`",
                inline=True
            )
            
            embed.set_footer(text=f"ID: {member.id}")
            
            await logs_channel.send(embed=embed)
            
        except Exception as e:
            print(f"❌ Ошибка в on_member_remove: {e}")

    @commands.Cog.listener()
    async def on_invite_create(self, invite: disnake.Invite):
        """Обработка создания приглашения"""
        try:
            guild = invite.guild
            if guild.id not in self.invites:
                self.invites[guild.id] = []
            self.invites[guild.id] = await guild.invites()
        except Exception as e:
            print(f"❌ Ошибка в on_invite_create: {e}")

    @commands.Cog.listener()
    async def on_invite_delete(self, invite: disnake.Invite):
        """Обработка удаления приглашения"""
        try:
            guild = invite.guild
            self.invites[guild.id] = await guild.invites()
        except Exception as e:
            print(f"❌ Ошибка в on_invite_delete: {e}")

    @commands.slash_command(name="invites", description="Посмотреть количество приглашений пользователя")
    async def invites_command(
        self, 
        inter: disnake.ApplicationCommandInteraction, 
        user: disnake.Member = None
    ):
        """Показать статистику приглашений пользователя"""
        try:
            target_user = user or inter.author
            user_data = self.load_invite_data(target_user.id)
            
            embed = disnake.Embed(
                title="📊 Статистика приглашений",
                color=disnake.Color.blue(),
                timestamp=datetime.datetime.utcnow()
            )
            
            embed.set_thumbnail(url=target_user.display_avatar.url)
            
            embed.add_field(
                name="👤 Пользователь",
                value=f"{target_user.mention}\n`{target_user}`",
                inline=False
            )
            
            embed.add_field(
                name="📨 Всего приглашений",
                value=f"**{user_data.get('total_invites', 0)}**",
                inline=True
            )
            
            embed.add_field(
                name="👥 Активных приглашений",
                value=f"**{len(user_data.get('invited_users', []))}**",
                inline=True
            )
            
            recent_invites = user_data.get("invited_users", [])[-5:]
            if recent_invites:
                recent_list = []
                for invited in recent_invites:
                    member = inter.guild.get_member(invited["user_id"])
                    name = member.mention if member else f"`{invited['username']}`"
                    recent_list.append(f"• {name}")
                
                embed.add_field(
                    name="🔹 Последние приглашения",
                    value="\n".join(recent_list),
                    inline=False
                )
            else:
                embed.add_field(
                    name="🔹 Последние приглашения",
                    value="*Нет данных*",
                    inline=False
                )
            
            embed.set_footer(text=f"ID: {target_user.id}")
            
            await inter.response.send_message(embed=embed)
            
        except Exception as e:
            await inter.response.send_message(
                f"❌ Произошла ошибка: {str(e)}",
                ephemeral=True
            )

    @commands.slash_command(name="leaderboard", description="Топ пользователей по приглашениям")
    async def leaderboard_command(self, inter: disnake.ApplicationCommandInteraction):
        """Показать таблицу лидеров по приглашениям"""
        try:
            leaderboard = []
            
            for filename in os.listdir(self.invite_data_dir):
                if not filename.endswith(".json"):
                    continue
                    
                user_id = int(filename.replace(".json", ""))
                user_data = self.load_invite_data(user_id)
                total_invites = user_data.get("total_invites", 0)
                
                if total_invites > 0:
                    member = inter.guild.get_member(user_id)
                    if member:
                        leaderboard.append((member, total_invites))
            
            leaderboard.sort(key=lambda x: x[1], reverse=True)
            
            embed = disnake.Embed(
                title="🏆 Топ приглашений",
                color=disnake.Color.gold(),
                timestamp=datetime.datetime.utcnow()
            )
            
            if leaderboard:
                description = ""
                for i, (member, count) in enumerate(leaderboard[:10], 1):
                    if i == 1:
                        medal = "🥇"
                    elif i == 2:
                        medal = "🥈"
                    elif i == 3:
                        medal = "🥉"
                    else:
                        medal = f"`{i}.`"
                    
                    description += f"{medal} {member.mention} — **{count}** приглашений\n"
                
                embed.description = description
                embed.set_footer(text=f"Всего участников в топе: {len(leaderboard)}")
            else:
                embed.description = "*Пока нет данных о приглашениях*"
            
            await inter.response.send_message(embed=embed)
            
        except Exception as e:
            await inter.response.send_message(
                f"❌ Произошла ошибка: {str(e)}",
                ephemeral=True
            )

    @commands.slash_command(name="reset_invites", description="Сбросить приглашения пользователя (только для администраторов)")
    @commands.has_permissions(administrator=True)
    async def reset_invites_command(
        self, 
        inter: disnake.ApplicationCommandInteraction, 
        user: disnake.Member
    ):
        """Сброс счетчика приглашений пользователя (только для администраторов)"""
        try:
            user_data = {"total_invites": 0, "invited_users": []}
            self.save_invite_data(user.id, user_data)
            
            embed = disnake.Embed(
                title="✅ Приглашения сброшены",
                description=f"Статистика приглашений пользователя {user.mention} была успешно сброшена",
                color=disnake.Color.green(),
                timestamp=datetime.datetime.utcnow()
            )
            
            embed.set_thumbnail(url=user.display_avatar.url)
            embed.set_footer(text=f"Сброшено администратором {inter.author}")
            
            await inter.response.send_message(embed=embed)
            
        except Exception as e:
            await inter.response.send_message(
                f"❌ Произошла ошибка: {str(e)}",
                ephemeral=True
            )

def setup(bot):
    bot.add_cog(InviteLogger(bot))
