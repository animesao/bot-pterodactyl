import disnake
from disnake.ext import commands
import os
from dotenv import load_dotenv
import datetime
from typing import Optional

load_dotenv()


class ApplicationButtons(disnake.ui.View):
    """Кнопки для управления заявками"""
    
    def __init__(self):
        super().__init__(timeout=None)

    @disnake.ui.button(label="Принять", style=disnake.ButtonStyle.green, custom_id="accept_application")
    async def accept_button(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        try:
            # Defer immediately
            await inter.response.defer(ephemeral=True)
            
            if not inter.message.embeds:
                await inter.followup.send("Ошибка: сообщение не содержит embed.", ephemeral=True)
                return

            # Get the original embed
            original_embed = inter.message.embeds[0]
            
            embed = disnake.Embed(
                title=original_embed.title,
                description=original_embed.description,
                color=disnake.Color.green(),
                timestamp=original_embed.timestamp
            )
            
            for field in original_embed.fields:
                embed.add_field(
                    name=field.name,
                    value=field.value,
                    inline=field.inline
                )
            
            embed.add_field(
                name="✅ Статус",
                value=f"**Принято**\n{inter.author.mention}",
                inline=False
            )
            
            embed.set_footer(text=f"Принял: {inter.author} • ID: {inter.author.id}")
            
            await inter.message.edit(embed=embed, view=None)
            
            # Get the applicant
            try:
                applicant_mention = original_embed.fields[-1].value
                applicant_id = int(applicant_mention.replace("<@", "").replace(">", ""))
                applicant = inter.guild.get_member(applicant_id)
                
                if applicant:
                    # Send DM to applicant
                    try:
                        dm_embed = disnake.Embed(
                            title="💎 AmethystCloud • Заявка принята!",
                            description=f"🎉 Поздравляем! Ваша заявка была принята!\n\n"
                                      f"**Принял:** {inter.author.mention}\n\n"
                                      f"Скоро с вами свяжется администрация для дальнейших инструкций.",
                            color=0x9B59B6
                        )
                        await applicant.send(embed=dm_embed)
                    except disnake.Forbidden:
                        pass
            except (ValueError, IndexError):
                pass
            
            # Send to logs channel
            try:
                logs_channel_id = int(os.getenv("APPLICATION_LOGS_CHANNEL_ID", 0))
                if logs_channel_id:
                    logs_channel = inter.guild.get_channel(logs_channel_id)
                    if logs_channel:
                        await logs_channel.send(embed=embed)
            except (ValueError, AttributeError):
                pass
            
            success_embed = disnake.Embed(
                title="✅ Успешно!",
                description="Заявка успешно принята!",
                color=0x9B59B6
            )
            await inter.followup.send(embed=success_embed, ephemeral=True)
        except Exception as e:
            if not inter.response.is_done():
                await inter.response.send_message(
                    f"Произошла ошибка при принятии заявки: {str(e)}",
                    ephemeral=True
                )

    @disnake.ui.button(label="Отклонить", style=disnake.ButtonStyle.red, custom_id="reject_application")
    async def reject_button(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        try:
            # Defer immediately
            await inter.response.defer(ephemeral=True)
            
            if not inter.message.embeds:
                await inter.followup.send("Ошибка: сообщение не содержит embed.", ephemeral=True)
                return

            # Get the original embed
            original_embed = inter.message.embeds[0]
            
            embed = disnake.Embed(
                title=original_embed.title,
                description=original_embed.description,
                color=disnake.Color.red(),
                timestamp=original_embed.timestamp
            )
            
            for field in original_embed.fields:
                embed.add_field(
                    name=field.name,
                    value=field.value,
                    inline=field.inline
                )
            
            embed.add_field(
                name="❌ Статус",
                value=f"**Отклонено**\n{inter.author.mention}",
                inline=False
            )
            
            embed.set_footer(text=f"Отклонил: {inter.author} • ID: {inter.author.id}")
            
            await inter.message.edit(embed=embed, view=None)
            
            # Get the applicant
            try:
                applicant_mention = original_embed.fields[-1].value
                applicant_id = int(applicant_mention.replace("<@", "").replace(">", ""))
                applicant = inter.guild.get_member(applicant_id)
                
                if applicant:
                    # Send DM to applicant
                    try:
                        dm_embed = disnake.Embed(
                            title="💎 AmethystCloud • Заявка отклонена",
                            description=f"😔 К сожалению, ваша заявка была отклонена.\n\n"
                                      f"**Отклонил:** {inter.author.mention}\n\n"
                                      f"Вы можете подать новую заявку через 30 дней.",
                            color=0xFF0000
                        )
                        await applicant.send(embed=dm_embed)
                    except disnake.Forbidden:
                        pass
            except (ValueError, IndexError):
                pass
            
            # Send to logs channel
            try:
                logs_channel_id = int(os.getenv("APPLICATION_LOGS_CHANNEL_ID", 0))
                if logs_channel_id:
                    logs_channel = inter.guild.get_channel(logs_channel_id)
                    if logs_channel:
                        await logs_channel.send(embed=embed)
            except (ValueError, AttributeError):
                pass
            
            success_embed = disnake.Embed(
                title="✅ Успешно!",
                description="Заявка успешно отклонена!",
                color=0x9B59B6
            )
            await inter.followup.send(embed=success_embed, ephemeral=True)
        except Exception as e:
            if not inter.response.is_done():
                await inter.response.send_message(
                    f"Произошла ошибка при отклонении заявки: {str(e)}",
                    ephemeral=True
                )

class ApplySelect(disnake.ui.Select):
    """Выбор категории заявки"""
    
    def __init__(self):
        options = [
            disnake.SelectOption(
                label="Media",
                description="Подать заявку на должность Media",
                value="media",
                emoji="📷"
            ),
            disnake.SelectOption(
                label="PR Manager",
                description="Подать заявку на должность PR Manager",
                value="pr_manager",
                emoji="📢"
            )
        ]
        super().__init__(
            placeholder="Выберите категорию заявки",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="apply_select"
        )

    async def callback(self, inter: disnake.MessageInteraction):
        try:
            if not inter.values:
                if not inter.response.is_done():
                    await inter.response.send_message("Ошибка: не выбрана категория заявки.", ephemeral=True)
                return

            # Create modal based on selected category
            if inter.values[0] == "media":
                modal = MediaApplyModal()
            else:
                modal = PRManagerApplyModal()
            
            await inter.response.send_modal(modal)
        except Exception as e:
            if not inter.response.is_done():
                await inter.response.send_message(
                    f"Произошла ошибка: {str(e)}",
                    ephemeral=True
                )

class SupportApplyModal(disnake.ui.Modal):
    def __init__(self):
        components = [
            disnake.ui.TextInput(
                label="👤 Ваше имя",
                placeholder="Введите ваш никнейм",
                custom_id="name",
                style=disnake.TextInputStyle.short,
                required=True,
                max_length=100
            ),
            disnake.ui.TextInput(
                label="🎂 Ваш возраст",
                placeholder="Введите ваш возраст",
                custom_id="age",
                style=disnake.TextInputStyle.short,
                required=True,
                max_length=3
            ),
            disnake.ui.TextInput(
                label="⏰ Время работы",
                placeholder="Сколько часов в день можете работать?",
                custom_id="time",
                style=disnake.TextInputStyle.short,
                required=True,
                max_length=100
            ),
            disnake.ui.TextInput(
                label="🌍 Часовой пояс",
                placeholder="Введите ваш часовой пояс",
                custom_id="timezone",
                style=disnake.TextInputStyle.short,
                required=True,
                max_length=100
            ),
            disnake.ui.TextInput(
                label="💬 О себе",
                placeholder="Расскажите о своем опыте и почему хотите стать частью команды",
                custom_id="about",
                style=disnake.TextInputStyle.paragraph,
                required=True,
                max_length=1000
            )
        ]
        super().__init__(
            title="🎮 Заявка на роль саппорта",
            custom_id="support_apply",
            components=components
        )

    async def callback(self, inter: disnake.ModalInteraction):
        try:
            # Get the applications channel
            channel_id = int(os.getenv("APPLICATIONS_CHANNEL_ID", 0))
            channel = inter.guild.get_channel(channel_id)
            
            if not channel:
                await inter.response.send_message(
                    "Канал для заявок не найден. Пожалуйста, сообщите администратору.",
                    ephemeral=True
                )
                return

            # Create embed for the application
            embed = disnake.Embed(
                title="🎮 Новая заявка на роль саппорта",
                description="Привет! Если вы хотите присоединиться к нашей команде техподдержки, пожалуйста, заполните следующую анкету.",
                color=disnake.Color.blue(),
                timestamp=inter.created_at
            )
            
            # Add basic information
            embed.add_field(
                name="📋 Основная информация",
                value=inter.text_values["name"],
                inline=False
            )
            
            # Add age
            embed.add_field(
                name="🎂 Возраст",
                value=inter.text_values["age"],
                inline=False
            )
            
            # Add time
            embed.add_field(
                name="⏰ Время работы",
                value=inter.text_values["time"],
                inline=False
            )
            
            # Add timezone
            embed.add_field(
                name="🌍 Часовой пояс",
                value=inter.text_values["timezone"],
                inline=False
            )
            
            # Add about
            embed.add_field(
                name="💬 О себе",
                value=inter.text_values["about"],
                inline=False
            )
            
            # Add applicant info
            embed.add_field(
                name="👤 Заявитель",
                value=inter.author.mention,
                inline=False
            )
            
            # Create view with buttons
            view = ApplicationButtons()
            
            # Send application to the channel
            await channel.send(embed=embed, view=view)
            
            await inter.response.send_message(
                "Ваша заявка успешно отправлена! Ожидайте ответа от администрации.",
                ephemeral=True
            )
        except Exception as e:
            await inter.response.send_message(
                f"Произошла ошибка при отправке заявки: {str(e)}",
                ephemeral=True
            )

class MediaApplyModal(disnake.ui.Modal):
    """Модальное окно заявки на Media"""
    
    def __init__(self):
        components = [
            disnake.ui.TextInput(
                label="👤 Ваше имя",
                placeholder="Например: @username",
                custom_id="name",
                style=disnake.TextInputStyle.short,
                required=True,
                max_length=100
            ),
            disnake.ui.TextInput(
                label="🎂 Возраст",
                placeholder="Например: 25",
                custom_id="age",
                style=disnake.TextInputStyle.short,
                required=True,
                max_length=3
            ),
            disnake.ui.TextInput(
                label="📱 Платформы",
                placeholder="YouTube, TikTok, Instagram и т.д.",
                custom_id="platforms",
                style=disnake.TextInputStyle.short,
                required=True,
                max_length=200
            ),
            disnake.ui.TextInput(
                label="🌐 Языки",
                placeholder="Русский, Английский и т.д.",
                custom_id="languages",
                style=disnake.TextInputStyle.short,
                required=True,
                max_length=200
            ),
            disnake.ui.TextInput(
                label="🛡️ Работа с негативом",
                placeholder="Опишите ваш подход к работе с негативными комментариями",
                custom_id="negativity",
                style=disnake.TextInputStyle.paragraph,
                required=True,
                max_length=1000
            )
        ]
        super().__init__(
            title="💎 Заявка на Media",
            custom_id="media_apply",
            components=components
        )

    async def callback(self, inter: disnake.ModalInteraction):
        try:
            # Get the applications channel
            channel_id = int(os.getenv("APPLICATIONS_CHANNEL_ID", 0))
            channel = inter.guild.get_channel(channel_id)
            
            if not channel:
                await inter.response.send_message(
                    "Канал для заявок не найден. Пожалуйста, сообщите администратору.",
                    ephemeral=True
                )
                return

            # Create embed for the application
            embed = disnake.Embed(
                title="💎 AmethystCloud • Заявка на Media",
                description="Новая заявка на должность медиамейкера",
                color=0x9B59B6,
                timestamp=inter.created_at
            )
            
            embed.add_field(name="👤 Имя", value=f"`{inter.text_values['name']}`", inline=True)
            embed.add_field(name="🎂 Возраст", value=f"`{inter.text_values['age']}`", inline=True)
            embed.add_field(name="📱 Платформы", value=inter.text_values["platforms"], inline=False)
            embed.add_field(name="🌐 Языки", value=inter.text_values["languages"], inline=False)
            embed.add_field(name="🛡️ Работа с негативом", value=f"```\n{inter.text_values['negativity']}\n```", inline=False)
            embed.add_field(name="👤 Заявитель", value=inter.author.mention, inline=False)
            
            embed.set_footer(
                text="AmethystCloud Applications",
                icon_url=inter.bot.user.avatar.url if inter.bot.user.avatar else inter.bot.user.default_avatar.url
            )
            
            # Create view with buttons
            view = ApplicationButtons()
            
            # Send application to the channel
            await channel.send(embed=embed, view=view)
            
            await inter.response.send_message(
                "Ваша заявка успешно отправлена! Ожидайте ответа от администрации.",
                ephemeral=True
            )
        except Exception as e:
            await inter.response.send_message(
                f"Произошла ошибка при отправке заявки: {str(e)}",
                ephemeral=True
            )

class PRManagerApplyModal(disnake.ui.Modal):
    """Модальное окно заявки на PR Manager"""
    
    def __init__(self):
        components = [
            disnake.ui.TextInput(
                label="👤 Ваше имя",
                placeholder="Например: @username",
                custom_id="name",
                style=disnake.TextInputStyle.short,
                required=True,
                max_length=100
            ),
            disnake.ui.TextInput(
                label="🎂 Возраст",
                placeholder="Например: 16",
                custom_id="age",
                style=disnake.TextInputStyle.short,
                required=True,
                max_length=3
            ),
            disnake.ui.TextInput(
                label="⏰ Время работы",
                placeholder="Сколько часов в день можете работать?",
                custom_id="time",
                style=disnake.TextInputStyle.short,
                required=True,
                max_length=100
            ),
            disnake.ui.TextInput(
                label="🌍 Часовой пояс",
                placeholder="GMT+3 (Московское время)",
                custom_id="timezone",
                style=disnake.TextInputStyle.short,
                required=True,
                max_length=100
            ),
            disnake.ui.TextInput(
                label="🤝 Мотивация",
                placeholder="Почему вы хотите стать частью нашей команды?",
                custom_id="motivation",
                style=disnake.TextInputStyle.paragraph,
                required=True,
                max_length=1000
            )
        ]
        super().__init__(
            title="💎 Заявка на PR Manager",
            custom_id="pr_manager_apply",
            components=components
        )

    async def callback(self, inter: disnake.ModalInteraction):
        try:
            # Get the applications channel
            channel_id = int(os.getenv("APPLICATIONS_CHANNEL_ID", 0))
            channel = inter.guild.get_channel(channel_id)
            
            if not channel:
                await inter.response.send_message(
                    "Канал для заявок не найден. Пожалуйста, сообщите администратору.",
                    ephemeral=True
                )
                return

            # Create embed for the application
            embed = disnake.Embed(
                title="💎 AmethystCloud • Заявка на PR Manager",
                description="Новая заявка на должность пиар-менеджера",
                color=0x9B59B6,
                timestamp=inter.created_at
            )
            
            embed.add_field(name="👤 Имя", value=f"`{inter.text_values['name']}`", inline=True)
            embed.add_field(name="🎂 Возраст", value=f"`{inter.text_values['age']}`", inline=True)
            embed.add_field(name="⏰ Время работы", value=inter.text_values["time"], inline=False)
            embed.add_field(name="🌍 Часовой пояс", value=inter.text_values["timezone"], inline=False)
            embed.add_field(name="🤝 Мотивация", value=f"```\n{inter.text_values['motivation']}\n```", inline=False)
            embed.add_field(name="👤 Заявитель", value=inter.author.mention, inline=False)
            
            embed.set_footer(
                text="AmethystCloud Applications",
                icon_url=inter.bot.user.avatar.url if inter.bot.user.avatar else inter.bot.user.default_avatar.url
            )
            
            # Create view with buttons
            view = ApplicationButtons()
            
            # Send application to the channel
            await channel.send(embed=embed, view=view)
            
            success_embed = disnake.Embed(
                title="✅ Заявка отправлена!",
                description="Ваша заявка успешно отправлена администрации. Ожидайте ответа!",
                color=disnake.Color.green(),
                timestamp=datetime.datetime.utcnow()
            )
            success_embed.set_footer(text="AmethystCloud Applications")
            
            await inter.response.send_message(embed=success_embed, ephemeral=True)
        except Exception as e:
            await inter.response.send_message(
                f"❌ Произошла ошибка при отправке заявки: {str(e)}",
                ephemeral=True
            )


class ApplyView(disnake.ui.View):
    """Представление с выбором категории заявки"""
    
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ApplySelect())

class Apply(commands.Cog):
    """Система подачи заявок"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.persistent_views_added = False

    async def cog_load(self):
        """Загрузка постоянных представлений при запуске"""
        try:
            if not self.persistent_views_added:
                self.bot.add_view(ApplyView())
                self.bot.add_view(ApplicationButtons())
                self.persistent_views_added = True
                print("✅ Постоянные представления заявок добавлены")
        except Exception as e:
            print(f"❌ Ошибка добавления постоянных представлений: {str(e)}")

    @commands.slash_command(
        name="setup_apply",
        description="Настроить панель заявок",
        default_member_permissions=disnake.Permissions(administrator=True)
    )
    async def setup_apply(self, inter: disnake.ApplicationCommandInteraction):
        """Настройка панели заявок"""
        try:
            # Defer сразу чтобы избежать таймаута
            await inter.response.defer(ephemeral=True)
            
            channel_id = int(os.getenv("APPLICATIONS_CHANNEL_ID", 0))
            if not channel_id:
                await inter.edit_original_response(
                    content="❌ Канал для заявок не настроен. Пожалуйста, настройте переменную окружения APPLICATIONS_CHANNEL_ID."
                )
                return

            embed = disnake.Embed(
                title="💎 AmethystCloud • Система Заявок",
                description=(
                    "**📷 Заявка на роль медиамейкера**\n"
                    "Привет! Если вы хотите присоединиться к нашей команде в роли медиамейкера "
                    "(YouTuber, TikToker и т.д.), пожалуйста, заполните следующую анкету.\n\n"
                    "**📋 Основная информация**\n"
                    "1. Ваше имя (никнейм):\n"
                    "2. Возраст:\n\n"
                    "**📈 Навыки и опыт**\n"
                    "3. Платформы, на которых вы создаете контент:\n"
                    "   Перечислите платформы, где вы активны.\n"
                    "4. Языки, на которых вы говорите:\n\n"
                    "**🎨 Креативность и идеи**\n"
                    "5. Как вы справляетесь с негативными комментариями и критикой?\n"
                    "   Опишите ваш подход к управлению репутацией и работе с негативом.\n\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    "**📢 Заявка на роль пиар-менеджера**\n"
                    "Привет! Если вы хотите присоединиться к нашей команде в роли пиар-менеджера, "
                    "пожалуйста, заполните следующую анкету.\n\n"
                    "**📋 Основная информация**\n"
                    "1. Ваше имя (никнейм):\n"
                    "   Пример: @username\n"
                    "2. Возраст:\n"
                    "   Пример: 16\n"
                    "3. Время, которое вы можете уделять работе ежедневно:\n"
                    "4. Часовой пояс:\n"
                    "   Пример: GMT+3 (Московское время)\n\n"
                    "**🤝 Дополнительная информация**\n"
                    "5. Почему вы хотите стать частью нашей команды пиар-менеджеров?\n"
                    "   Напишите, что вас мотивирует и почему вы хотите присоединиться к нам."
                ),
                color=0x9B59B6
            )
            embed.set_footer(
                text="AmethystCloud Applications",
                icon_url=self.bot.user.avatar.url if self.bot.user.avatar else self.bot.user.default_avatar.url
            )
            embed.set_thumbnail(url=self.bot.user.avatar.url if self.bot.user.avatar else self.bot.user.default_avatar.url)
            
            view = ApplyView()
            
            await inter.channel.send(embed=embed, view=view)
            
            success_embed = disnake.Embed(
                title="✅ Успешно!",
                description="Панель заявок успешно создана!",
                color=disnake.Color.purple()
            )
            await inter.edit_original_response(embed=success_embed)
        except Exception as e:
            error_embed = disnake.Embed(
                title="❌ Ошибка",
                description=f"Произошла ошибка при создании панели заявок: {str(e)}",
                color=disnake.Color.red()
            )
            try:
                await inter.edit_original_response(embed=error_embed)
            except:
                pass

    @commands.Cog.listener()
    async def on_select(self, inter: disnake.MessageInteraction):
        try:
            if inter.component.custom_id == "apply_select":
                if not inter.values:
                    if not inter.response.is_done():
                        await inter.response.send_message("Ошибка: не выбрана категория заявки.", ephemeral=True)
                    return

                # Create modal based on selected category
                if inter.values[0] == "media":
                    modal = MediaApplyModal()
                else:
                    modal = PRManagerApplyModal()
                
                await inter.response.send_modal(modal)
        except Exception as e:
            if not inter.response.is_done():
                await inter.response.send_message(
                    f"Произошла ошибка: {str(e)}",
                    ephemeral=True
                )

def setup(bot):
    bot.add_cog(Apply(bot))