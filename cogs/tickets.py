import disnake
from disnake.ext import commands
import asyncio
import os
import json
import datetime
import traceback
from typing import Optional
from dotenv import load_dotenv
from .database import (
    add_ticket_log, get_ticket_logs, save_ticket_transcript, get_ticket_transcript, 
    save_ticket_message, get_tickets_by_user, get_tickets_by_user_count,
    get_recent_tickets_paginated, get_all_tickets_count,
    search_tickets_paginated, search_tickets_count
)

load_dotenv()


class TicketLogger:
    """Система логирования тикетов"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logs_channel_id = int(os.getenv("TICKET_LOGS_CHANNEL_ID", 0))

    async def save_transcript(self, channel: disnake.TextChannel) -> bool:
        """Сохранение транскрипта тикета в БД"""
        try:
            messages = []
            async for message in channel.history(limit=None, oldest_first=True):
                if message.author.bot:
                    continue
                    
                content = message.content
                if message.attachments:
                    content += "\n" + "\n".join([f"Attachment: {att.url}" for att in message.attachments])
                
                messages.append(f"[{message.created_at.strftime('%Y-%m-%d %H:%M:%S')}] {message.author.name}: {content}")

            transcript = "\n".join(messages)
            
            # Сохраняем в БД
            save_ticket_transcript(
                ticket_id=channel.id,
                ticket_name=channel.name,
                channel_name=channel.name,
                transcript=transcript
            )
            
            return True
        except Exception as e:
            print(f"Error saving transcript: {str(e)}")
            print(traceback.format_exc())
            return False

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

            # Сохраняем в БД
            add_ticket_log(
                ticket_id=ticket_channel.id,
                ticket_name=ticket_channel.name,
                action=action,
                user_id=user.id,
                user_name=str(user),
                reason=reason
            )



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

            if action == "Закрыт":
                await self.save_transcript(ticket_channel)

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
            await self.logger.save_transcript(inter.channel)
            
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

class TicketHistoryView(disnake.ui.View):
    """Пагинация для истории тикетов"""
    
    def __init__(self, tickets: list, page: int, total_pages: int, total_count: int, 
                 search_query: str = None, user_id: int = None):
        super().__init__(timeout=120)
        self.tickets = tickets
        self.page = page
        self.total_pages = total_pages
        self.total_count = total_count
        self.search_query = search_query
        self.user_id = user_id
        self._update_buttons()
    
    def _update_buttons(self):
        """Обновить кнопки пагинации"""
        self.clear_items()
        
        # Кнопка "Назад"
        if self.page > 1:
            back_button = disnake.ui.Button(
                label="◀️ Назад",
                style=disnake.ButtonStyle.secondary,
                custom_id="ticket_history_back"
            )
            self.add_item(back_button)
        
        # Кнопка "Вперед"
        if self.page < self.total_pages:
            next_button = disnake.ui.Button(
                label="Вперед ▶️",
                style=disnake.ButtonStyle.primary,
                custom_id="ticket_history_next"
            )
            self.add_item(next_button)


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
            # Кнопки пагинации истории тикетов
            if inter.component.custom_id in ["ticket_history_back", "ticket_history_next"]:
                await self.handle_ticket_history_pagination(inter)
                return
            
            if inter.component.custom_id == "close_ticket":
                if "ticket-" in inter.channel.name:
                    modal = CloseTicketModal(self.bot)
                    await inter.response.send_modal(modal)

            elif inter.component.custom_id == "assign_staff":
                if "ticket-" in inter.channel.name:
                    await self.logger.log_ticket(
                        ticket_channel=inter.channel,
                        action="Назначен ответственный",
                        user=inter.author
                    )
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

    async def handle_ticket_history_pagination(self, inter: disnake.MessageInteraction):
        """Обработка пагинации истории тикетов"""
        try:
            await inter.response.defer(ephemeral=True)
            
            # Получаем данные из текущего embed
            embed = inter.message.embeds[0] if inter.message.embeds else None
            if not embed:
                return
            
            # Определяем текущую страницу из footer
            footer_text = embed.footer.text if embed.footer else ""
            current_page = 1
            if "Страница" in footer_text:
                try:
                    current_page = int(footer_text.split("Страница ")[1].split("/")[0])
                except:
                    pass
            
            # Определяем тип контента из title
            title = embed.title or ""
            
            # Вычисляем новую страницу
            if inter.component.custom_id == "ticket_history_back":
                new_page = current_page - 1
            else:
                new_page = current_page + 1
            
            per_page = 10
            offset = (new_page - 1) * per_page
            
            # Определяем что загружать
            if "Пользователь" in title or "user" in title.lower():
                # Ищем user_id из предыдущего view
                old_view = inter.message.components[0].children[0] if inter.message.components else None
                # Пробуем получить user_id из footer или другого места
                # Пока используем простой поиск
                tickets = []
                total_count = 0
            elif "Поиск" in title or "search" in title.lower():
                # Извлекаем поисковый запрос
                search_query = title.split(": ")[1] if ": " in title else ""
                tickets = search_tickets_paginated(search_query, per_page, offset)
                total_count = search_tickets_count(search_query)
            else:
                tickets = get_recent_tickets_paginated(per_page, offset)
                total_count = get_all_tickets_count()
            
            total_pages = max(1, (total_count + per_page - 1) // per_page)
            
            if not tickets:
                await inter.followup.send(
                    "❌ Тикеты не найдены!",
                    ephemeral=True
                )
                return
            
            # Формируем новый embed
            new_embed = disnake.Embed(
                title=title,
                description=f"Всего тикетов: **{total_count}** | Страница **{new_page}/{total_pages}**",
                color=disnake.Color.purple(),
                timestamp=datetime.datetime.utcnow()
            )
            
            ticket_lines = []
            for t in tickets:
                dt = t.get("created_at", "?")[:10] if t.get("created_at") else "?"
                status = "🔒" if t.get("action") == "Закрыт" or t.get("closed_at") else "📂"
                ticket_name = t.get("ticket_name", "unknown")
                ticket_id = t.get("ticket_id", "?")
                user_name = t.get("user_name", "")
                
                line = f"{status} `{ticket_id}` - {ticket_name}\n   📅 {dt}"
                if user_name and "Пользователь" not in title:
                    line += f" • 👤 {user_name}"
                ticket_lines.append(line)
            
            # Сохраняем команды в embed
            if "Пользователь" not in title and "Поиск" not in title:
                new_embed.add_field(
                    name="💡 Команды",
                    value=(
                        "`/ticket_history ticket_id:ID` — Транскрипт тикета\n"
                        "`/ticket_history user:@user` — Тикеты пользователя\n"
                        "`/ticket_history search:запрос` — Поиск тикетов"
                    ),
                    inline=False
                )
            
            new_embed.add_field(
                name="📋 Тикеты",
                value="\n".join(ticket_lines),
                inline=False
            )
            
            new_embed.set_footer(
                text=f"Страница {new_page}/{total_pages} • Используйте кнопки для навигации",
                icon_url=self.bot.user.avatar.url if self.bot.user.avatar else self.bot.user.default_avatar.url
            )
            
            view = TicketHistoryView(tickets, new_page, total_pages, total_count)
            await inter.edit_original_response(embed=new_embed, view=view)
            
        except Exception as e:
            await inter.followup.send(
                f"❌ Ошибка: {str(e)}",
                ephemeral=True
            )

    @commands.Cog.listener()
    async def on_message(self, message: disnake.Message):
        """Сохранение всех сообщений в тикетах"""
        # Игнорируем сообщения от ботов
        if message.author.bot:
            return
        
        # Проверяем что это канал тикета
        if not message.channel.name or not message.channel.name.startswith("ticket-"):
            return
        
        try:
            # Получаем attachments
            attachments = None
            if message.attachments:
                attachments = "\n".join([att.url for att in message.attachments])
            
            # Сохраняем сообщение в БД
            save_ticket_message(
                ticket_id=message.channel.id,
                message_id=message.id,
                user_id=message.author.id,
                user_name=str(message.author),
                content=message.content or "",
                attachments=attachments
            )
        except Exception as e:
            print(f"Error saving ticket message: {e}")

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

    @commands.slash_command(name="ticket_history", description="Посмотреть историю тикетов")
    @commands.has_permissions(administrator=True)
    async def ticket_history(
        self, 
        inter: disnake.ApplicationCommandInteraction, 
        ticket_id: Optional[str] = None,
        search: Optional[str] = None,
        user: Optional[disnake.Member] = None,
        page: Optional[int] = 1
    ):
        """Просмотр истории тикетов с пагинацией"""
        try:
            await inter.response.defer(ephemeral=True)
            
            per_page = 10
            
            # Если указан ID тикета - показываем транскрипт
            if ticket_id:
                try:
                    tid = int(ticket_id)
                except ValueError:
                    await inter.followup.send(
                        "❌ Неверный ID тикета!",
                        ephemeral=True
                    )
                    return
                
                transcript = get_ticket_transcript(tid)
                logs = get_ticket_logs(tid)
                
                if not transcript and not logs:
                    await inter.followup.send(
                        f"❌ Тикет `{ticket_id}` не найден!",
                        ephemeral=True
                    )
                    return
                
                embed = disnake.Embed(
                    title=f"📜 История тикета #{ticket_id}",
                    color=disnake.Color.purple(),
                    timestamp=datetime.datetime.utcnow()
                )
                
                # Показываем логи действий (ограничиваем длину)
                if logs:
                    log_lines = []
                    for log in logs[:10]:
                        dt = log["created_at"][:16] if log["created_at"] else "?"
                        log_lines.append(f"`{dt}` **{log['action']}** - {log['user_name']}")
                    
                    log_value = "\n".join(log_lines)
                    if len(log_value) > 1024:
                        log_value = log_value[:1020] + "..."
                    
                    embed.add_field(
                        name="📋 Действия",
                        value=log_value,
                        inline=False
                    )
                
                # Если транскрипт слишком длинный - отправляем файлом
                if transcript:
                    if len(transcript) > 1000:
                        # Создаем временный файл
                        filename = f"ticket_{ticket_id}_transcript.txt"
                        with open(filename, "w", encoding="utf-8") as f:
                            f.write(transcript)
                        
                        file_size = os.path.getsize(filename)
                        if file_size < 1024:
                            size_str = f"{file_size} B"
                        elif file_size < 1024 * 1024:
                            size_str = f"{file_size / 1024:.2f} KB"
                        else:
                            size_str = f"{file_size / (1024 * 1024):.2f} MB"
                        
                        embed.add_field(
                            name="💬 Диалог",
                            value=f"Транскрипт слишком длинный для отображения.\nФайл: `{filename}` ({size_str})",
                            inline=False
                        )
                        
                        embed.set_footer(
                            text="AmethystCloud Ticket History",
                            icon_url=self.bot.user.avatar.url if self.bot.user.avatar else self.bot.user.default_avatar.url
                        )
                        
                        # Отправляем embed + файл
                        await inter.followup.send(
                            embed=embed,
                            file=disnake.File(filename, filename=filename),
                            ephemeral=True
                        )
                        
                        # Удаляем временный файл
                        os.remove(filename)
                    else:
                        # Транскрипт влезает в embed
                        embed.add_field(
                            name="💬 Диалог",
                            value=f"```\n{transcript}\n```",
                            inline=False
                        )
                        
                        embed.set_footer(
                            text="AmethystCloud Ticket History",
                            icon_url=self.bot.user.avatar.url if self.bot.user.avatar else self.bot.user.default_avatar.url
                        )
                        
                        await inter.followup.send(embed=embed, ephemeral=True)
                else:
                    embed.set_footer(
                        text="AmethystCloud Ticket History",
                        icon_url=self.bot.user.avatar.url if self.bot.user.avatar else self.bot.user.default_avatar.url
                    )
                    await inter.followup.send(embed=embed, ephemeral=True)
                
                return
            
            # Если указан пользователь - показываем его тикеты
            if user:
                offset = (page - 1) * per_page
                tickets = get_tickets_by_user(user.id, per_page, offset)
                total_count = get_tickets_by_user_count(user.id)
                total_pages = max(1, (total_count + per_page - 1) // per_page)
                
                if not tickets:
                    await inter.followup.send(
                        f"❌ Тикеты пользователя {user.mention} не найдены!",
                        ephemeral=True
                    )
                    return
                
                embed = disnake.Embed(
                    title=f"👤 Тикеты пользователя {user.name}",
                    description=f"Найдено тикетов: **{total_count}** | Страница **{page}/{total_pages}**",
                    color=disnake.Color.purple(),
                    timestamp=datetime.datetime.utcnow()
                )
                
                ticket_lines = []
                for t in tickets:
                    dt = t["created_at"][:10] if t["created_at"] else "?"
                    status = "🔒" if t["action"] == "Закрыт" else "📂"
                    ticket_lines.append(
                        f"{status} `{t['ticket_id']}` - {t['ticket_name']}\n"
                        f"   📅 {dt}"
                    )
                
                embed.add_field(
                    name="📋 Тикеты",
                    value="\n".join(ticket_lines),
                    inline=False
                )
                
                embed.set_footer(
                    text=f"Страница {page}/{total_pages} • Используйте кнопки для навигации",
                    icon_url=self.bot.user.avatar.url if self.bot.user.avatar else self.bot.user.default_avatar.url
                )
                
                view = TicketHistoryView(tickets, page, total_pages, total_count, user_id=user.id)
                await inter.followup.send(embed=embed, view=view, ephemeral=True)
                return
            
            # Если указан поисковый запрос
            if search:
                offset = (page - 1) * per_page
                tickets = search_tickets_paginated(search, per_page, offset)
                total_count = search_tickets_count(search)
                total_pages = max(1, (total_count + per_page - 1) // per_page)
                
                if not tickets:
                    await inter.followup.send(
                        f"❌ Тикеты по запросу `{search}` не найдены!",
                        ephemeral=True
                    )
                    return
                
                embed = disnake.Embed(
                    title=f"🔍 Результаты поиска: {search}",
                    description=f"Найдено тикетов: **{total_count}** | Страница **{page}/{total_pages}**",
                    color=disnake.Color.purple(),
                    timestamp=datetime.datetime.utcnow()
                )
                
                ticket_lines = []
                for t in tickets:
                    dt = t["created_at"][:10] if t["created_at"] else "?"
                    status = "🔒" if t["action"] == "Закрыт" else "📂"
                    ticket_lines.append(
                        f"{status} `{t['ticket_id']}` - {t['ticket_name']}\n"
                        f"   👤 {t['user_name']} • 📅 {dt}"
                    )
                
                embed.add_field(
                    name="📋 Тикеты",
                    value="\n".join(ticket_lines),
                    inline=False
                )
                
                embed.set_footer(
                    text=f"Страница {page}/{total_pages} • Используйте кнопки для навигации",
                    icon_url=self.bot.user.avatar.url if self.bot.user.avatar else self.bot.user.default_avatar.url
                )
                
                view = TicketHistoryView(tickets, page, total_pages, total_count, search_query=search)
                await inter.followup.send(embed=embed, view=view, ephemeral=True)
                return
            
            # Показываем последние тикеты с пагинацией
            offset = (page - 1) * per_page
            tickets = get_recent_tickets_paginated(per_page, offset)
            total_count = get_all_tickets_count()
            total_pages = max(1, (total_count + per_page - 1) // per_page)
            
            if not tickets:
                await inter.followup.send(
                    "❌ Тикеты не найдены!",
                    ephemeral=True
                )
                return
            
            embed = disnake.Embed(
                title="📜 AmethystCloud • История Тикетов",
                description=f"Всего тикетов: **{total_count}** | Страница **{page}/{total_pages}**",
                color=disnake.Color.purple(),
                timestamp=datetime.datetime.utcnow()
            )
            
            ticket_lines = []
            for t in tickets:
                dt = t["created_at"][:10] if t["created_at"] else "?"
                status = "🔒" if t["closed_at"] else "📂"
                line = f"{status} `{t['ticket_id']}` - {t['ticket_name']}\n   📅 {dt}"
                ticket_lines.append(line)
            
            # Ограничиваем длину списка
            tickets_value = "\n".join(ticket_lines)
            if len(tickets_value) > 1024:
                tickets_value = tickets_value[:1020] + "..."
            
            embed.add_field(
                name="📋 Тикеты",
                value=tickets_value,
                inline=False
            )
            
            embed.add_field(
                name="💡 Команды",
                value=(
                    "`/ticket_history ticket_id:ID` — Транскрипт тикета\n"
                    "`/ticket_history user:@user` — Тикеты пользователя\n"
                    "`/ticket_history search:запрос` — Поиск тикетов"
                ),
                inline=False
            )
            
            embed.set_footer(
                text=f"Страница {page}/{total_pages} • Используйте кнопки для навигации",
                icon_url=self.bot.user.avatar.url if self.bot.user.avatar else self.bot.user.default_avatar.url
            )
            
            view = TicketHistoryView(tickets, page, total_pages, total_count)
            await inter.followup.send(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            await inter.followup.send(
                f"❌ Ошибка: {str(e)}",
                ephemeral=True
            )



def setup(bot):
    bot.add_cog(Tickets(bot))