
import disnake
from disnake.ext import commands
import os
import json
import datetime
from dotenv import load_dotenv

load_dotenv()

class InviteLogger(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.invites = {}
        self.invite_logs_channel_id = int(os.getenv("INVITE_LOGS_CHANNEL_ID", 0))
        
        # Create invites data directory if it doesn't exist
        os.makedirs("invite_data", exist_ok=True)

    async def cog_load(self):
        """Load invite data when cog is loaded"""
        await self.bot.wait_until_ready()
        for guild in self.bot.guilds:
            try:
                self.invites[guild.id] = await guild.invites()
                print(f"Loaded {len(self.invites[guild.id])} invites for guild {guild.name}")
            except Exception as e:
                print(f"Error loading invites for guild {guild.name}: {e}")
                self.invites[guild.id] = []

    def load_invite_data(self, user_id: int):
        """Load invite data for a user"""
        try:
            with open(f"invite_data/{user_id}.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return {"total_invites": 0, "invited_users": []}

    def save_invite_data(self, user_id: int, data: dict):
        """Save invite data for a user"""
        try:
            with open(f"invite_data/{user_id}.json", "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving invite data for user {user_id}: {e}")

    def find_invite_by_code(self, guild_invites, code):
        """Find invite by code"""
        for invite in guild_invites:
            if invite.code == code:
                return invite
        return None

    def get_invite_difference(self, old_invites, new_invites):
        """Find which invite was used"""
        for new_invite in new_invites:
            old_invite = self.find_invite_by_code(old_invites, new_invite.code)
            if old_invite and new_invite.uses > old_invite.uses:
                return new_invite
        return None

    def format_time_ago(self, timestamp):
        """Format time difference in human readable format"""
        now = datetime.datetime.utcnow()
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=datetime.timezone.utc)
        
        diff = now.replace(tzinfo=datetime.timezone.utc) - timestamp
        days = diff.days
        
        if days >= 365:
            years = days // 365
            return f"{years} year{'s' if years != 1 else ''}"
        elif days >= 30:
            months = days // 30
            return f"{months} month{'s' if months != 1 else ''}"
        elif days > 0:
            return f"{days} day{'s' if days != 1 else ''}"
        else:
            hours = diff.seconds // 3600
            if hours > 0:
                return f"{hours} hour{'s' if hours != 1 else ''}"
            else:
                minutes = diff.seconds // 60
                return f"{minutes} minute{'s' if minutes != 1 else ''}"

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Handle member join event"""
        try:
            guild = member.guild
            
            # Get current invites
            current_invites = await guild.invites()
            old_invites = self.invites.get(guild.id, [])
            
            # Find which invite was used
            used_invite = self.get_invite_difference(old_invites, current_invites)
            
            # Update stored invites
            self.invites[guild.id] = current_invites
            
            # Get logs channel
            logs_channel = guild.get_channel(self.invite_logs_channel_id)
            if not logs_channel:
                return

            # Calculate account age
            account_age = self.format_time_ago(member.created_at)
            
            if used_invite and used_invite.inviter:
                inviter = used_invite.inviter
                
                # Load inviter data
                inviter_data = self.load_invite_data(inviter.id)
                inviter_data["total_invites"] += 1
                inviter_data["invited_users"].append({
                    "user_id": member.id,
                    "username": str(member),
                    "joined_at": datetime.datetime.utcnow().isoformat()
                })
                
                # Save inviter data
                self.save_invite_data(inviter.id, inviter_data)
                
                # Create welcome message
                message = (
                    f"Добро пожаловать, {member.mention} Надеюсь, вы к нам на долго :)\n\n"
                    f"Пригласил: {inviter.mention} ({inviter.name})\n"
                    f"Итого приглашений: {inviter_data['total_invites']}\n\n"
                    f"----------Доп. информация ({member.mention})----------\n"
                    f"ID пользователя: {member.id}\n"
                    f"Аккаунт создан: {member.created_at.strftime('%B %d, %Y, %I:%M:%S %p')}\n"
                    f"Аккаунт создан: {account_age} назад\n\n"
                    f"---------Доп. информация {inviter.mention} ({inviter.name})----------\n"
                    f"ID пользователя: {inviter.id}"
                )
            else:
                # Unknown inviter
                message = (
                    f"Добро пожаловать, {member.mention} Надеюсь, вы к нам на долго :)\n\n"
                    f"Пригласил: Неизвестно (возможно, прямая ссылка или исчезнувшее приглашение)\n\n"
                    f"----------Доп. информация ({member.mention})----------\n"
                    f"ID пользователя: {member.id}\n"
                    f"Аккаунт создан: {member.created_at.strftime('%B %d, %Y, %I:%M:%S %p')}\n"
                    f"Аккаунт создан: {account_age} назад"
                )
            
            await logs_channel.send(message)
            
        except Exception as e:
            print(f"Error in on_member_join: {e}")

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        """Handle member leave event"""
        try:
            guild = member.guild
            
            # Get logs channel
            logs_channel = guild.get_channel(self.invite_logs_channel_id)
            if not logs_channel:
                return

            # Find who invited this member
            inviter = None
            inviter_name = "неизвестный-пользователь"
            
            # Search through all user invite data
            for filename in os.listdir("invite_data"):
                if filename.endswith(".json"):
                    user_id = int(filename.replace(".json", ""))
                    user_data = self.load_invite_data(user_id)
                    
                    # Check if this user was invited by this person
                    for invited_user in user_data.get("invited_users", []):
                        if invited_user["user_id"] == member.id:
                            inviter = guild.get_member(user_id)
                            if inviter:
                                inviter_name = f"{inviter.mention} ({inviter.name})"
                                
                                # Remove user from invited list and decrease count
                                user_data["invited_users"] = [
                                    u for u in user_data["invited_users"] 
                                    if u["user_id"] != member.id
                                ]
                                user_data["total_invites"] = max(0, user_data["total_invites"] - 1)
                                self.save_invite_data(user_id, user_data)
                                
                                message = (
                                    f"Жаль, что покинул нас {member.mention}\n"
                                    f"Его пригласил: {inviter_name}\n"
                                    f"Итого приглашений: {user_data['total_invites']}"
                                )
                            else:
                                message = (
                                    f"Жаль, что покинул нас {member.mention}\n"
                                    f"Его пригласил: @неизвестный-пользователь\n"
                                    f"Итого приглашений: Неизвестно"
                                )
                            
                            await logs_channel.send(message)
                            return
            
            # If inviter not found
            message = (
                f"Жаль, что покинул нас {member.mention}\n"
                f"Его пригласил: @неизвестный-пользователь\n"
                f"Итого приглашений: Неизвестно"
            )
            
            await logs_channel.send(message)
            
        except Exception as e:
            print(f"Error in on_member_remove: {e}")

    @commands.Cog.listener()
    async def on_invite_create(self, invite):
        """Handle invite creation"""
        try:
            guild = invite.guild
            if guild.id not in self.invites:
                self.invites[guild.id] = []
            
            # Refresh invites list
            self.invites[guild.id] = await guild.invites()
            
        except Exception as e:
            print(f"Error in on_invite_create: {e}")

    @commands.Cog.listener()
    async def on_invite_delete(self, invite):
        """Handle invite deletion"""
        try:
            guild = invite.guild
            
            # Refresh invites list
            self.invites[guild.id] = await guild.invites()
            
        except Exception as e:
            print(f"Error in on_invite_delete: {e}")

    @commands.slash_command(name="invites", description="Посмотреть количество приглашений пользователя")
    async def invites_command(self, inter: disnake.ApplicationCommandInteraction, 
                            user: disnake.Member = None):
        """Show invite count for a user"""
        try:
            target_user = user or inter.author
            user_data = self.load_invite_data(target_user.id)
            
            embed = disnake.Embed(
                title="📊 Статистика приглашений",
                color=disnake.Color.blue()
            )
            
            embed.add_field(
                name="Пользователь",
                value=target_user.mention,
                inline=False
            )
            
            embed.add_field(
                name="Всего приглашений",
                value=user_data.get("total_invites", 0),
                inline=False
            )
            
            # Show recent invited users (last 5)
            recent_invites = user_data.get("invited_users", [])[-5:]
            if recent_invites:
                recent_list = []
                for invited in recent_invites:
                    member = inter.guild.get_member(invited["user_id"])
                    name = member.mention if member else f"@{invited['username']}"
                    recent_list.append(name)
                
                embed.add_field(
                    name="Последние приглашения",
                    value="\n".join(recent_list),
                    inline=False
                )
            
            await inter.response.send_message(embed=embed)
            
        except Exception as e:
            await inter.response.send_message(
                f"Произошла ошибка: {str(e)}",
                ephemeral=True
            )

    @commands.slash_command(name="leaderboard", description="Топ пользователей по приглашениям")
    async def leaderboard_command(self, inter: disnake.ApplicationCommandInteraction):
        """Show invite leaderboard"""
        try:
            # Collect all invite data
            leaderboard = []
            
            for filename in os.listdir("invite_data"):
                if filename.endswith(".json"):
                    user_id = int(filename.replace(".json", ""))
                    user_data = self.load_invite_data(user_id)
                    total_invites = user_data.get("total_invites", 0)
                    
                    if total_invites > 0:
                        member = inter.guild.get_member(user_id)
                        if member:
                            leaderboard.append((member, total_invites))
            
            # Sort by invite count
            leaderboard.sort(key=lambda x: x[1], reverse=True)
            
            embed = disnake.Embed(
                title="🏆 Топ приглашений",
                color=disnake.Color.gold()
            )
            
            if leaderboard:
                description = ""
                for i, (member, count) in enumerate(leaderboard[:10], 1):
                    medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                    description += f"{medal} {member.mention} - {count} приглашений\n"
                
                embed.description = description
            else:
                embed.description = "Пока нет данных о приглашениях"
            
            await inter.response.send_message(embed=embed)
            
        except Exception as e:
            await inter.response.send_message(
                f"Произошла ошибка: {str(e)}",
                ephemeral=True
            )

    @commands.slash_command(name="reset_invites", description="Сбросить приглашения пользователя")
    @commands.has_permissions(administrator=True)
    async def reset_invites_command(self, inter: disnake.ApplicationCommandInteraction, 
                                  user: disnake.Member):
        """Reset user's invite count (admin only)"""
        try:
            # Reset user data
            user_data = {"total_invites": 0, "invited_users": []}
            self.save_invite_data(user.id, user_data)
            
            embed = disnake.Embed(
                title="✅ Приглашения сброшены",
                description=f"Приглашения пользователя {user.mention} были сброшены",
                color=disnake.Color.green()
            )
            
            await inter.response.send_message(embed=embed)
            
        except Exception as e:
            await inter.response.send_message(
                f"Произошла ошибка: {str(e)}",
                ephemeral=True
            )

def setup(bot):
    bot.add_cog(InviteLogger(bot))
