import disnake
from disnake.ext import commands
import os
from dotenv import load_dotenv
import datetime

load_dotenv()

class ApplicationButtons(disnake.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @disnake.ui.button(label="Принять", style=disnake.ButtonStyle.green, custom_id="accept_application")
    async def accept_button(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        try:
            if not inter.message.embeds:
                if not inter.response.is_done():
                    await inter.response.send_message("Ошибка: сообщение не содержит embed.", ephemeral=True)
                return

            # Get the original embed
            original_embed = inter.message.embeds[0]
            
            # Create new embed with acceptance status
            embed = disnake.Embed(
                title=original_embed.title,
                description=original_embed.description,
                color=disnake.Color.green(),
                timestamp=original_embed.timestamp
            )
            
            # Copy all fields from original embed
            for field in original_embed.fields:
                embed.add_field(
                    name=field.name,
                    value=field.value,
                    inline=field.inline
                )
            
            # Add acceptance information
            embed.add_field(
                name="Статус",
                value=f"✅ Принято {inter.author.mention}",
                inline=False
            )
            
            # Update the message
            await inter.message.edit(embed=embed, view=None)
            
            # Get the applicant
            try:
                applicant_mention = original_embed.fields[-1].value  # Last field is applicant info
                applicant_id = int(applicant_mention.replace("<@", "").replace(">", ""))
                applicant = inter.guild.get_member(applicant_id)
                
                if applicant:
                    # Send DM to applicant
                    try:
                        await applicant.send(
                            f"🎉 Поздравляем! Ваша заявка была принята {inter.author.mention}!\n"
                            f"Скоро с вами свяжется администрация для дальнейших инструкций."
                        )
                    except disnake.Forbidden:
                        pass  # If we can't send DM, just continue
            except (ValueError, IndexError):
                pass  # If we can't get applicant info, just continue
            
            # Send to logs channel
            try:
                logs_channel_id = int(os.getenv("APPLICATION_LOGS_CHANNEL_ID", 0))
                if logs_channel_id:
                    logs_channel = inter.guild.get_channel(logs_channel_id)
                    if logs_channel:
                        await logs_channel.send(embed=embed)
            except (ValueError, AttributeError):
                pass  # If we can't send to logs, just continue
            
            if not inter.response.is_done():
                await inter.response.send_message(
                    "Заявка успешно принята!",
                    ephemeral=True
                )
        except Exception as e:
            if not inter.response.is_done():
                await inter.response.send_message(
                    f"Произошла ошибка при принятии заявки: {str(e)}",
                    ephemeral=True
                )

    @disnake.ui.button(label="Отклонить", style=disnake.ButtonStyle.red, custom_id="reject_application")
    async def reject_button(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        try:
            if not inter.message.embeds:
                if not inter.response.is_done():
                    await inter.response.send_message("Ошибка: сообщение не содержит embed.", ephemeral=True)
                return

            # Get the original embed
            original_embed = inter.message.embeds[0]
            
            # Create new embed with rejection status
            embed = disnake.Embed(
                title=original_embed.title,
                description=original_embed.description,
                color=disnake.Color.red(),
                timestamp=original_embed.timestamp
            )
            
            # Copy all fields from original embed
            for field in original_embed.fields:
                embed.add_field(
                    name=field.name,
                    value=field.value,
                    inline=field.inline
                )
            
            # Add rejection information
            embed.add_field(
                name="Статус",
                value=f"❌ Отклонено {inter.author.mention}",
                inline=False
            )
            
            # Update the message
            await inter.message.edit(embed=embed, view=None)
            
            # Get the applicant
            try:
                applicant_mention = original_embed.fields[-1].value  # Last field is applicant info
                applicant_id = int(applicant_mention.replace("<@", "").replace(">", ""))
                applicant = inter.guild.get_member(applicant_id)
                
                if applicant:
                    # Send DM to applicant
                    try:
                        await applicant.send(
                            f"😔 К сожалению, ваша заявка была отклонена {inter.author.mention}.\n"
                            f"Вы можете подать новую заявку через 30 дней."
                        )
                    except disnake.Forbidden:
                        pass  # If we can't send DM, just continue
            except (ValueError, IndexError):
                pass  # If we can't get applicant info, just continue
            
            # Send to logs channel
            try:
                logs_channel_id = int(os.getenv("APPLICATION_LOGS_CHANNEL_ID", 0))
                if logs_channel_id:
                    logs_channel = inter.guild.get_channel(logs_channel_id)
                    if logs_channel:
                        await logs_channel.send(embed=embed)
            except (ValueError, AttributeError):
                pass  # If we can't send to logs, just continue
            
            if not inter.response.is_done():
                await inter.response.send_message(
                    "Заявка успешно отклонена!",
                    ephemeral=True
                )
        except Exception as e:
            if not inter.response.is_done():
                await inter.response.send_message(
                    f"Произошла ошибка при отклонении заявки: {str(e)}",
                    ephemeral=True
                )

class ApplySelect(disnake.ui.Select):
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
    def __init__(self):
        components = [
            disnake.ui.TextInput(
                label="👤 Ваше имя (никнейм)",
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
                placeholder="Например: YouTube, TikTok, Instagram",
                custom_id="platforms",
                style=disnake.TextInputStyle.short,
                required=True,
                max_length=200
            ),
            disnake.ui.TextInput(
                label="🌐 Языки",
                placeholder="Например: Русский, Английский",
                custom_id="languages",
                style=disnake.TextInputStyle.short,
                required=True,
                max_length=200
            ),
            disnake.ui.TextInput(
                label="🛡️ Работа с негативом",
                placeholder="Опишите ваш подход к управлению репутацией и работе с негативом",
                custom_id="negativity",
                style=disnake.TextInputStyle.paragraph,
                required=True,
                max_length=1000
            )
        ]
        super().__init__(
            title="🎥 Заявка на роль медиамейкера",
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
                title="🎥 Новая заявка на роль медиамейкера",
                description="Привет! Если вы хотите присоединиться к нашей команде в роли медиамейкера (YouTuber, TikToker и т.д.), пожалуйста, заполните следующую анкету.",
                color=disnake.Color.blue(),
                timestamp=inter.created_at
            )
            
            # Add name
            embed.add_field(
                name="👤 Ваше имя (никнейм)",
                value=inter.text_values["name"],
                inline=False
            )
            
            # Add age
            embed.add_field(
                name="🎂 Возраст",
                value=inter.text_values["age"],
                inline=False
            )
            
            # Add platforms
            embed.add_field(
                name="📱 Платформы",
                value=inter.text_values["platforms"],
                inline=False
            )
            
            # Add languages
            embed.add_field(
                name="🌐 Языки",
                value=inter.text_values["languages"],
                inline=False
            )
            
            # Add negativity handling
            embed.add_field(
                name="🛡️ Работа с негативом",
                value=inter.text_values["negativity"],
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

class PRManagerApplyModal(disnake.ui.Modal):
    def __init__(self):
        components = [
            disnake.ui.TextInput(
                label="👤 Ваше имя (никнейм)",
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
                placeholder="Например: GMT+3 (Московское время)",
                custom_id="timezone",
                style=disnake.TextInputStyle.short,
                required=True,
                max_length=100
            ),
            disnake.ui.TextInput(
                label="🤝 Мотивация",
                placeholder="Почему вы хотите стать частью нашей команды пиар-менеджеров?",
                custom_id="motivation",
                style=disnake.TextInputStyle.paragraph,
                required=True,
                max_length=1000
            )
        ]
        super().__init__(
            title="📢 Заявка на роль пиар-менеджера",
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
                title="📢 Новая заявка на роль пиар-менеджера",
                description="Привет! Если вы хотите присоединиться к нашей команде в роли пиар-менеджера, пожалуйста, заполните следующую анкету.",
                color=disnake.Color.blue(),
                timestamp=inter.created_at
            )
            
            # Add name
            embed.add_field(
                name="👤 Ваше имя (никнейм)",
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
            
            # Add motivation
            embed.add_field(
                name="🤝 Мотивация",
                value=inter.text_values["motivation"],
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

class ApplyView(disnake.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ApplySelect())

class Apply(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.persistent_views_added = False

    async def cog_load(self):
        try:
            # Add persistent views when the cog is loaded
            if not self.persistent_views_added:
                self.bot.add_view(ApplyView())
                self.bot.add_view(ApplicationButtons())
                self.persistent_views_added = True
                print("Persistent views added successfully")
        except Exception as e:
            print(f"Error adding persistent views: {str(e)}")

    @commands.slash_command(
        name="setup_apply",
        description="Настроить панель заявок",
        default_member_permissions=disnake.Permissions(administrator=True)
    )
    async def setup_apply(self, inter: disnake.ApplicationCommandInteraction):
        try:
            # Check if the channel is set up
            channel_id = int(os.getenv("APPLICATIONS_CHANNEL_ID", 0))
            if not channel_id:
                await inter.response.send_message(
                    "Канал для заявок не настроен. Пожалуйста, настройте переменную окружения APPLICATIONS_CHANNEL_ID.",
                    ephemeral=True
                )
                return

            # Create the embed
            embed = disnake.Embed(
                title="ㅤHALLCLOUD",
                description="""🎥 Заявка на роль медиамейкера
Привет! Если вы хотите присоединиться к нашей команде в роли медиамейкера (YouTuber, TikToker и т.д.), пожалуйста, заполните следующую анкету.

📋 Основная информация
1. Ваше имя (никнейм):

2. Возраст:

📈 Навыки и опыт

3. Платформы, на которых вы создаете контент:
Перечислите платформы, где вы активны.

4. Языки, на которых вы говорите:

🎨 Креативность и идеи
5. Как вы справляетесь с негативными комментариями и критикой?
Опишите ваш подход к управлению репутацией и работе с негативом. 
HALLCLOUD

📢 Заявка на роль пиар-менеджера
Привет! Если вы хотите присоединиться к нашей команде в роли пиар-менеджера, пожалуйста, заполните следующую анкету.

📋 Основная информация
1. Ваше имя (никнейм):
Пример: @username

2. Возраст:
Пример: 16

3. Время, которое вы можете уделять работе ежедневно:

4. Часовой пояс:
Пример: GMT+3 (Московское время)

---

🤝 Дополнительная информация
5. Почему вы хотите стать частью нашей команды пиар-менеджеров?
Напишите, что вас мотивирует и почему вы хотите присоединиться к нам.""",
                color=0x0047df
            )
            
            # Create and add the view
            view = ApplyView()
            
            # Send the message
            await inter.channel.send(embed=embed, view=view)
            
            # Send confirmation
            await inter.response.send_message(
                "Панель заявок успешно создана!",
                ephemeral=True
            )
        except Exception as e:
            if not inter.response.is_done():
                await inter.response.send_message(
                    f"Произошла ошибка при создании панели заявок: {str(e)}",
                    ephemeral=True
                )

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