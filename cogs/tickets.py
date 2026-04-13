import disnake
from disnake.ext import commands
import asyncio
import os
import json
import datetime
import traceback
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class TicketLogger:
    """Система логирования тикетов"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logs_channel_id = int(os.getenv("TICKET_LOGS_CHANNEL_ID", 0))

    async def save_transcript(self, channel: disnake.TextChannel) -> Optional[str]:
        """Сохранение транскрипта тикета в файл"""
        try:
            messages = []
            async for message in channel.history(limit=None, oldest_first=True):
                if message.author.bot:
                    continue
                    
                content = message.content
                if message.attachments:
                    content += "\n" + "\n".join([f"📎 {att.url}" for att in message.attachments])
                
                messages.append(f"[{message.created_at.strftime('%Y-%m-%d %H:%M:%S')}] {message.author.name}: {content}")

            transcript = "\n".join(messages)
            filename = f"ticket_logs/transcript_{channel.name}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            
            os.makedirs("ticket_logs", exist_ok=True)
            
            with open(filename, "w", encoding="utf-8") as f:
                f.write(transcript)
                
            return filename
        except Exception as e:
            print(f"❌ Ошибка сохранения транскрипта: {str(e)}")
            print(traceback.format_exc())
            return None

    async def log_ticket(
        self, 
        ticket_channel: disnake.TextChannel, 
        action: str, 
        user: disnake.Member, 
        reason: Optional[str] = None
    ) -> None:
        """Логирование действий с тикетом"""
        try:
            if not self.logs_channel_id:
                print("⚠️ TICKET_LOGS_CHANNEL_ID не установлен")
                return

            logs_channel = ticket_channel.guild.get_channel(self.logs_channel_id)
            if not logs_channel:
                print(f"⚠️ Канал логов {self.logs_channel_id} не найден")
                return

            log_entry = {
                "timestamp": datetime.datetime.utcnow().isoformat(),
                "ticket_id": ticket_channel.id,
                "ticket_name": ticket_channel.name,
                "action": action,
                "user_id": user.id,
                "user_name": str(user),
                "reason": reason
            }

            embed = disnake.Embed(
                title="💎 AmethystCloud • Лог Тикета",
                color=disnake.Color.purple(),
                timestamp=datetime.datetime.utcnow()
            )
            
            embed.add_field(name="📌 Тикет", value=f"<#{ticket_channel.id}>", inline=False)
            embed.add_field(name="⚡ Действие", value=f"`{action}`", inline=True)
            embed.add_field(name="👤 Пользователь", value=f"{user.mention}\n`{user}`", inline=True)
            
            if reason:
                embed.add_field(name="📝 Причина", value=f"```\n{reason}\n```", inline=False)
            
            embed.set_footer(text=f"ID: {ticket_channel.id}")

            await logs_channel.send(embed=embed)

            log_file = f"ticket_logs/{ticket_channel.id}.json"
            os.makedirs("ticket_logs", exist_ok=True)

            existing_logs = []
            if os.path.exists(log_file):
                with open(log_file, 'r', encoding='utf-8') as f:
                    try:
                        existing_logs = json.load(f)
                    except json.JSONDecodeError:
                        print(f"❌ Ошибка чтения файла логов {log_file}")
                        existing_logs = []

            existing_logs.append(log_entry)

            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(existing_logs, f, ensure_ascii=False, indent=2)

            if action == "Закрыт":
                transcript_file = await self.save_transcript(ticket_channel)
                if transcript_file:
                    await logs_channel.send(
                        "📝 Транскрипт тикета:",
                        file=disnake.File(transcript_file)
                    )

            await logs_channel.send(
                file=disnake.File(log_file, filename=f"ticket_{ticket_channel.id}_logs.json")
            )

        except Exception as e:
            print(f"❌ Ошибка логирования тикета: {str(e)}")
            print(traceback.format_exc())

class CloseTicketModal(disnake.ui.Modal):
    """Модальное окно для закрытия тикета"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = TicketLogger(bot)
        components = [
            disnake.ui.TextInput(
                label="Причина закрытия",
                placeholder="Укажите причину закрытия тикета (например: Вопрос решен)",
                custom_id="reason",
                style=disnake.TextInputStyle.paragraph,
                required=True,
                max_length=1000
            )
        ]
        super().__init__(
            title="💎 Закрытие тикета",
            custom_id="close_ticket_modal",
            components=components
        )

    async def callback(self, inter: disnake.ModalInteraction):
        reason = inter.text_values["reason"]
        
        try:
            # Defer the response immediately
            await inter.response.defer()
            
            # Log ticket closure
            await self.logger.log_ticket(
                ticket_channel=inter.channel,
                action="Закрыт",
                user=inter.author,
                reason=reason
            )

            # Create transcript
            transcript_file = await self.logger.save_transcript(inter.channel)
            
            # Send confirmation with embed
            close_embed = disnake.Embed(
                title="🔒 Тикет закрывается...",
                description=f"**Причина закрытия:**\n```\n{reason}\n```\n\nТикет будет удален через несколько секунд.",
                color=0x9B59B6
            )
            close_embed.set_footer(text="Спасибо за обращение в AmethystCloud!")
            
            await inter.channel.send(embed=close_embed)
            
            # Wait a bit before deleting
            await asyncio.sleep(3)
            
            # Delete the channel
            await inter.channel.delete()
        except Exception as e:
            error_embed = disnake.Embed(
                title="❌ Ошибка",
                description=f"Произошла ошибка при закрытии тикета: {str(e)}",
                color=0xFF0000
            )
            try:
                await inter.followup.send(embed=error_embed, ephemeral=True)
            except:
                print(f"Error closing ticket: {e}")

class TicketModal(disnake.ui.Modal):
    """Модальное окно для создания тикета"""
    
    def __init__(self, bot: commands.Bot, category_id: int):
        self.bot = bot
        self.category_id = category_id
        self.logger = TicketLogger(bot)
        components = [
            disnake.ui.TextInput(
                label="Опишите ваш вопрос",
                placeholder="Подробно опишите вашу проблему или запрос...",
                custom_id="description",
                style=disnake.TextInputStyle.paragraph,
                required=True,
                max_length=1000
            )
        ]
        super().__init__(
            title="💎 Создание тикета",
            custom_id="create_ticket",
            components=components
        )

    async def callback(self, inter: disnake.ModalInteraction):
        try:
            description = inter.text_values["description"]
            
            # Create the ticket channel
            category = self.bot.get_channel(self.category_id)
            if not category:
                await inter.response.send_message(
                    "Ошибка: Категория для тикета не найдена. Пожалуйста, сообщите администратору.",
                    ephemeral=True
                )
                return
            
            # Create the ticket channel
            overwrites = {
                inter.guild.default_role: disnake.PermissionOverwrite(read_messages=False),
                inter.author: disnake.PermissionOverwrite(read_messages=True, send_messages=True),
                inter.guild.me: disnake.PermissionOverwrite(read_messages=True, send_messages=True)
            }

            # Add staff roles to the channel permissions
            staff_role_ids = [int(role_id) for role_id in os.getenv("STAFF_ROLE_IDS", "").split(",") if role_id]
            for role_id in staff_role_ids:
                staff_role = inter.guild.get_role(role_id)
                if staff_role:
                    overwrites[staff_role] = disnake.PermissionOverwrite(
                        read_messages=True,
                        send_messages=True,
                        manage_messages=True,
                        manage_channels=True
                    )

            channel = await inter.guild.create_text_channel(
                f"ticket-{inter.author.name}",
                category=category,
                overwrites=overwrites
            )

            # Log ticket creation
            await self.logger.log_ticket(
                ticket_channel=channel,
                action="Создан",
                user=inter.author,
                reason=description
            )

            # Send the initial message in the ticket channel
            embed = disnake.Embed(
                title="💎 AmethystCloud • Тикет Поддержки",
                description=f"Тикет создан для {inter.author.mention}\n\n"
                          f"**📋 Описание:**\n```\n{description}\n```\n\n"
                          f"✨ Наша команда скоро ответит на ваш запрос!",
                color=0x9B59B6
            )
            embed.set_footer(
                text="Для закрытия тикета используйте кнопку ниже",
                icon_url=self.bot.user.avatar.url if self.bot.user.avatar else self.bot.user.default_avatar.url
            )

            # Add buttons
            close_button = disnake.ui.Button(
                label="Закрыть тикет",
                style=disnake.ButtonStyle.danger,
                custom_id="close_ticket",
                emoji="🔒"
            )
            
            assign_button = disnake.ui.Button(
                label="Назначить",
                style=disnake.ButtonStyle.secondary,
                custom_id="assign_staff",
                emoji="👤"
            )

            view = disnake.ui.View(timeout=None)
            view.add_item(close_button)
            view.add_item(assign_button)

            await channel.send(embed=embed, view=view)
            
            # Send success message
            success_embed = disnake.Embed(
                title="✅ Тикет создан!",
                description=f"Перейдите в {channel.mention}",
                color=0x9B59B6
            )
            await inter.response.send_message(embed=success_embed, ephemeral=True)
        except Exception as e:
            await inter.response.send_message(
                f"Произошла ошибка при создании тикета: {str(e)}",
                ephemeral=True
            )
            print(traceback.format_exc())

class TicketSelect(disnake.ui.Select):
    def __init__(self, bot):
        self.bot = bot
        options = [
            disnake.SelectOption(
                label="Помощь",
                description="Получить помощь от нашей команды",
                value="help",
                emoji="❓"
            ),
            disnake.SelectOption(
                label="Покупка тарифа",
                description="Приобрести тарифный план",
                value="tariff",
                emoji="💎"
            )
        ]
        super().__init__(
            placeholder="Выберите категорию тикета",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="ticket_select"
        )

    async def callback(self, inter: disnake.MessageInteraction):
        try:
            # Check if user already has an open ticket
            for channel in inter.guild.channels:
                if isinstance(channel, disnake.TextChannel):
                    if f"ticket-{inter.author.name}" in channel.name:
                        await inter.response.send_message(
                            "У вас уже есть открытый тикет! Пожалуйста, закройте его перед созданием нового.",
                            ephemeral=True
                        )
                        return

            # Get the appropriate category ID
            if self.values[0] == "help":
                category_id = int(os.getenv("HELP_CATEGORY_ID", 0))
            else:
                category_id = int(os.getenv("TARIFF_CATEGORY_ID", 0))

            if category_id == 0:
                await inter.response.send_message(
                    "Ошибка: ID категории не настроен. Пожалуйста, сообщите администратору.",
                    ephemeral=True
                )
                return

            # Create and send the modal
            modal = TicketModal(self.bot, category_id)
            await inter.response.send_modal(modal)
        except Exception as e:
            await inter.response.send_message(
                f"Произошла ошибка: {str(e)}",
                ephemeral=True
            )
            print(traceback.format_exc())

class StaffSelect(disnake.ui.Select):
    def __init__(self, guild):
        self.guild = guild
        # Get all staff roles
        staff_role_ids = [int(role_id.strip()) for role_id in os.getenv("STAFF_ROLE_IDS", "").split(",") if role_id.strip()]
        options = []
        
        for role_id in staff_role_ids:
            role = guild.get_role(role_id)
            if role:
                options.append(
                    disnake.SelectOption(
                        label=role.name,
                        description=f"Выбрать роль {role.name}",
                        value=str(role.id),
                        emoji="👥"
                    )
                )
        
        if not options:
            options.append(
                disnake.SelectOption(
                    label="Нет доступных ролей",
                    description="Пожалуйста, сообщите администратору",
                    value="0",
                    emoji="⚠️"
                )
            )
        
        super().__init__(
            placeholder="Выберите роль для назначения",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="staff_select"
        )

    async def callback(self, inter: disnake.MessageInteraction):
        try:
            if not self.values:
                await inter.response.send_message(
                    "Не выбрано ни одной роли. Пожалуйста, выберите роль.",
                    ephemeral=True
                )
                return

            if self.values[0] == "0":
                await inter.response.send_message(
                    "Нет доступных ролей. Пожалуйста, сообщите администратору.",
                    ephemeral=True
                )
                return

            # Check if user has the selected role
            role_id = int(self.values[0])
            role = self.guild.get_role(role_id)
            
            if not role:
                await inter.response.send_message(
                    "Роль не найдена. Пожалуйста, попробуйте снова.",
                    ephemeral=True
                )
                return

            if role not in inter.author.roles:
                await inter.response.send_message(
                    "У вас нет прав для назначения себя ответственным за эту роль.",
                    ephemeral=True
                )
                return

            # Update channel permissions
            try:
                await inter.channel.set_permissions(
                    inter.author,
                    read_messages=True,
                    send_messages=True
                )
            except disnake.Forbidden:
                await inter.response.send_message(
                    "У бота нет прав для изменения разрешений канала.",
                    ephemeral=True
                )
                return

            # Create embed
            embed = disnake.Embed(
                title="💎 Назначение Ответственного",
                description=f"✅ {inter.author.mention} назначен ответственным",
                color=0x9B59B6
            )
            
            embed.add_field(
                name="👤 Ответственный",
                value=f"{inter.author.mention}",
                inline=True
            )
            
            embed.add_field(
                name="🏷️ Роль",
                value=f"{role.mention}",
                inline=True
            )
            
            # Send initial response
            success_embed = disnake.Embed(
                title="✅ Назначение успешно!",
                description=f"Вы назначены ответственным за тикет как {role.mention}",
                color=0x9B59B6
            )
            await inter.response.send_message(embed=success_embed, ephemeral=True)
            
            # Try to send or edit the status message
            try:
                # First try to find an existing status message
                async for message in inter.channel.history(limit=10):
                    if message.author == inter.guild.me and message.embeds:
                        await message.edit(embed=embed)
                        return
                
                # If no existing message found, send a new one
                await inter.channel.send(embed=embed)
            except Exception as e:
                print(f"Error updating status message: {e}")
                # Don't raise the error to the user as the main functionality is complete
                
        except Exception as e:
            print(f"Error in StaffSelect callback: {e}")
            try:
                await inter.response.send_message(
                    "Произошла ошибка при назначении ответственного. Пожалуйста, попробуйте позже.",
                    ephemeral=True
                )
            except:
                # If we can't send a response, just log the error
                pass

class TicketView(disnake.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
        self.add_item(TicketSelect(bot))

class Tickets(commands.Cog):
    """Система тикетов поддержки"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = TicketLogger(bot)
        self.help_category_id = int(os.getenv("HELP_CATEGORY_ID", 0))
        self.tariff_category_id = int(os.getenv("TARIFF_CATEGORY_ID", 0))
        self.ticket_panel_channel_id = int(os.getenv("TICKET_PANEL_CHANNEL_ID", 0))
        
        os.makedirs("ticket_logs", exist_ok=True)
        self.persistent_views_added = False

    async def cog_load(self):
        """Загрузка постоянных представлений при запуске"""
        if not self.persistent_views_added:
            self.bot.add_view(TicketView(self.bot))
            self.persistent_views_added = True
            print("✅ Постоянные представления тикетов добавлены")

    @commands.slash_command(name="setup_tickets", description="Настроить панель тикетов")
    @commands.has_permissions(administrator=True)
    async def setup_tickets(self, inter: disnake.ApplicationCommandInteraction):
        try:
            # Defer the response immediately to prevent timeout
            await inter.response.defer()
            
            embed = disnake.Embed(
                title="💎 AmethystCloud • Система Поддержки",
                description="Добро пожаловать в систему поддержки AmethystCloud!\n\n"
                          "**Выберите категорию тикета:**\n"
                          "❓ **Помощь** - Получить помощь от нашей команды\n"
                          "💎 **Покупка тарифа** - Приобрести тарифный план\n\n"
                          "Используйте меню ниже для создания тикета:",
                color=0x9B59B6
            )
            embed.set_footer(
                text="AmethystCloud Support System",
                icon_url=self.bot.user.avatar.url if self.bot.user.avatar else self.bot.user.default_avatar.url
            )
            embed.set_thumbnail(url=self.bot.user.avatar.url if self.bot.user.avatar else self.bot.user.default_avatar.url)
            
            # Create view with select menu
            view = TicketView(self.bot)
            
            await inter.channel.send(embed=embed, view=view)
            
            success_embed = disnake.Embed(
                title="✅ Успешно!",
                description="Панель тикетов успешно создана!",
                color=0x9B59B6
            )
            await inter.edit_original_response(embed=success_embed)
        except Exception as e:
            error_embed = disnake.Embed(
                title="❌ Ошибка",
                description=f"Произошла ошибка при создании панели тикетов: {str(e)}",
                color=0xFF0000
            )
            try:
                await inter.edit_original_response(embed=error_embed)
            except:
                await inter.response.send_message(embed=error_embed, ephemeral=True)
            print(traceback.format_exc())

    @commands.Cog.listener()
    async def on_button_click(self, inter: disnake.MessageInteraction):
        try:
            if inter.component.custom_id == "close_ticket":
                if "ticket-" in inter.channel.name:
                    # Create and send the close ticket modal
                    modal = CloseTicketModal(self.bot)
                    await inter.response.send_modal(modal)

            elif inter.component.custom_id == "assign_staff":
                if "ticket-" in inter.channel.name:
                    # Log staff assignment
                    await self.logger.log_ticket(
                        ticket_channel=inter.channel,
                        action="Назначен ответственный",
                        user=inter.author
                    )
                    # Create staff select menu
                    select = StaffSelect(inter.guild)
                    view = disnake.ui.View(timeout=None)
                    view.add_item(select)
                    
                    await inter.response.send_message(
                        "Выберите ответственного за тикет:",
                        view=view,
                        ephemeral=True
                    )
        except Exception as e:
            await inter.response.send_message(
                f"Произошла ошибка: {str(e)}",
                ephemeral=True
            )
            print(traceback.format_exc())

    @commands.Cog.listener()
    async def on_select(self, inter: disnake.MessageInteraction):
        try:
            if inter.component.custom_id == "ticket_select":
                # Create modal based on selected category
                if inter.values[0] == "help":
                    category_id = int(os.getenv("HELP_CATEGORY_ID", 0))
                else:
                    category_id = int(os.getenv("TARIFF_CATEGORY_ID", 0))
                
                modal = TicketModal(self.bot, category_id)
                await inter.response.send_modal(modal)
            elif inter.component.custom_id == "staff_select":
                # Handle staff selection
                select = StaffSelect(inter.guild)
                await select.callback(inter)
        except Exception as e:
            await inter.response.send_message(
                f"Произошла ошибка: {str(e)}",
                ephemeral=True
            )
            print(traceback.format_exc())

def setup(bot):
    bot.add_cog(Tickets(bot))
