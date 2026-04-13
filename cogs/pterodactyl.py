import disnake
from disnake.ext import commands, tasks
import aiohttp
import os
import json
from dotenv import load_dotenv
import datetime
import traceback

load_dotenv()

class PterodactylStatus(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_url = "https://mysite/api/application"
        self.api_key = "Application API"
        self.node_ids = ["ID", "ID"]
        self.status_channel_id = int(os.getenv("PTERODACTYL_STATUS_CHANNEL_ID", 0))
        self.status_message_id = None
        self.discord_limit = int(os.getenv("PTERODACTYL_DISCORD_LIMIT", 1))
        self.status_file = "cogs/pterodactyl_status.json"
        self.load_status_data()
        
        # Кэш предыдущих статусов для избежания лишних обновлений
        self.last_panel_status = None
        self.last_node_statuses = {}
        
        self.update_status.start()
        
        # Проверка на корректность сохраненных данных
        if self.status_message_id and not self.status_channel_id:
            self.status_message_id = None
            self.save_status_data()

    def cog_unload(self):
        self.update_status.cancel()

    def load_status_data(self):
        try:
            with open(self.status_file, 'r') as f:
                data = json.load(f)
                self.status_message_id = data.get('status_message_id')
                self.status_channel_id = data.get('status_channel_id', self.status_channel_id)
        except FileNotFoundError:
            pass

    def save_status_data(self):
        data = {
            'status_message_id': self.status_message_id,
            'status_channel_id': self.status_channel_id
        }
        with open(self.status_file, 'w') as f:
            json.dump(data, f)

    @tasks.loop(seconds=30)
    async def update_status(self):
        try:
            async with aiohttp.ClientSession() as session:
                # Проверяем доступность панели
                panel_online = False
                try:
                    async with session.get(f"{self.api_url}/nodes", timeout=5) as resp:
                        panel_online = resp.status == 200
                except:
                    panel_online = False

                # Проверяем ноды
                node_statuses = {}
                for node_id in self.node_ids:
                    node_online = False
                    try:
                        async with session.get(f"{self.api_url}/nodes/{node_id}", timeout=5) as resp:
                            node_online = resp.status == 200
                    except:
                        node_online = False
                    node_statuses[node_id] = node_online

                # Проверяем, изменился ли статус нод
                nodes_changed = self.last_node_statuses != node_statuses
                
                # Сохраняем текущий статус
                self.last_panel_status = panel_online
                self.last_node_statuses = node_statuses.copy()

                # Формируем embed в фиолетовой стиле AmethystCloud
                all_online = panel_online and all(node_statuses.values())
                
                # Фиолетовая цветовая схема AmethystCloud
                embed_color = 0x9B59B6  # Фиолетовый цвет
                
                # Статус панели (без изменений в тексте)
                panel_emoji = "💎" if panel_online else "🔴"
                panel_text = "Работает стабильно" if panel_online else "Недоступна"
                
                # Статусы нод с прогресс-барами
                node_lines = []
                online_count = sum(1 for online in node_statuses.values() if online)
                total_count = len(node_statuses)
                
                for node_id, online in node_statuses.items():
                    emoji = "💎" if online else "🔴"
                    status_bar = "████████░░" if online else "░░░░░░░░░░"
                    status = "Активна" if online else "Отключена"
                    node_lines.append(f"{emoji} `Нода #{node_id}` {status_bar} {status}")
                
                # Если ноды не изменились, обновляем только время
                if not nodes_changed and self.status_message_id:
                    channel = self.bot.get_channel(self.status_channel_id)
                    if channel:
                        try:
                            msg = await channel.fetch_message(self.status_message_id)
                            embed = msg.embeds[0] if msg.embeds else None
                            if embed:
                                current_time = datetime.datetime.now().strftime('%d.%m.%Y • %H:%M:%S')
                                embed.set_footer(
                                    text=f"🕐 Обновлено: {current_time}",
                                    icon_url=self.bot.user.avatar.url if self.bot.user.avatar else self.bot.user.default_avatar.url
                                )
                                await msg.edit(embed=embed)
                                return
                        except:
                            pass
                
                # Создаем полный embed только если статус нод изменился
                embed = disnake.Embed(
                    title="💎 AmethystCloud • Панель Мониторинга",
                    color=embed_color
                )
                
                embed.add_field(
                    name="🌐 Панель Управления",
                    value=f"{panel_emoji} {panel_text}",
                    inline=False
                )
                
                embed.add_field(
                    name=f"⚡ Статус Нод ({online_count}/{total_count})",
                    value="\n".join(node_lines),
                    inline=False
                )
                
                # Общий статус с прогресс-индикатором
                if all_online:
                    overall_status = "✨ Все системы функционируют оптимально\n`████████████████████` 100%"
                elif panel_online:
                    percentage = int((online_count / total_count) * 100)
                    bar_filled = int((online_count / total_count) * 20)
                    bar = "█" * bar_filled + "░" * (20 - bar_filled)
                    overall_status = f"⚠️ Частичная работоспособность\n`{bar}` {percentage}%"
                else:
                    overall_status = "🚨 Критическая ошибка системы\n`░░░░░░░░░░░░░░░░░░░░` 0%"
                
                embed.add_field(
                    name="📊 Общая Производительность",
                    value=overall_status,
                    inline=False
                )

                current_time = datetime.datetime.now().strftime('%d.%m.%Y • %H:%M:%S')
                embed.set_footer(
                    text=f"🕐 Обновлено: {current_time}",
                    icon_url=self.bot.user.avatar.url if self.bot.user.avatar else self.bot.user.default_avatar.url
                )
                
                embed.set_thumbnail(url=self.bot.user.avatar.url if self.bot.user.avatar else self.bot.user.default_avatar.url)
                await self._send_or_edit(embed)

        except Exception as e:
            print(traceback.format_exc())
            embed = disnake.Embed(
                title="💎 AmethystCloud • Панель Мониторинга",
                color=0x9B59B6
            )
            
            embed.add_field(
                name="🌐 Панель Управления",
                value="🔴 Недоступна",
                inline=False
            )
            
            node_error_lines = [f"🔴 `Нода #{node_id}` ░░░░░░░░░░ Отключена" for node_id in self.node_ids]
            embed.add_field(
                name=f"⚡ Статус Нод (0/{len(self.node_ids)})",
                value="\n".join(node_error_lines),
                inline=False
            )
            
            embed.add_field(
                name="📊 Общая Производительность",
                value="🚨 Критическая ошибка подключения\n`░░░░░░░░░░░░░░░░░░░░` 0%",
                inline=False
            )
            
            current_time = datetime.datetime.now().strftime('%d.%m.%Y • %H:%M:%S')
            embed.set_footer(
                text=f"🕐 Обновлено: {current_time}",
                icon_url=self.bot.user.avatar.url if self.bot.user.avatar else self.bot.user.default_avatar.url
            )
            
            embed.set_thumbnail(url=self.bot.user.avatar.url if self.bot.user.avatar else self.bot.user.default_avatar.url)
            await self._send_or_edit(embed)

    async def _send_or_edit(self, embed):
        channel = self.bot.get_channel(self.status_channel_id)
        if not channel:
            return
        
        # Попытка редактировать существующее сообщение
        if self.status_message_id:
            try:
                msg = await channel.fetch_message(self.status_message_id)
                await msg.edit(embed=embed)
                return
            except disnake.errors.NotFound:
                # Сообщение не найдено, сбрасываем ID
                self.status_message_id = None
                self.save_status_data()
            except Exception as e:
                print(f"Error editing status message: {e}")
                return
        
        # Если сообщение не существует, создаем новое
        try:
            msg = await channel.send(embed=embed)
            self.status_message_id = msg.id
            self.save_status_data()
        except Exception as e:
            print(f"Error sending status message: {e}")

    class PterodactylRegisterModal(disnake.ui.Modal):
        def __init__(self, cog):
            self.cog = cog
            components = [
                disnake.ui.TextInput(
                    label="Имя пользователя",
                    placeholder="Введите желаемый username",
                    custom_id="username",
                    style=disnake.TextInputStyle.short,
                    required=True,
                    max_length=32
                ),
                disnake.ui.TextInput(
                    label="Email",
                    placeholder="Введите ваш email",
                    custom_id="email",
                    style=disnake.TextInputStyle.short,
                    required=True,
                    max_length=100
                ),
                disnake.ui.TextInput(
                    label="Пароль",
                    placeholder="Введите желаемый пароль (минимум 8 символов)",
                    custom_id="password",
                    style=disnake.TextInputStyle.short,
                    required=True,
                    min_length=8,
                    max_length=64
                )
            ]
            super().__init__(
                title="Регистрация в панели Pterodactyl",
                custom_id="pterodactyl_register",
                components=components
            )

        async def callback(self, inter: disnake.ModalInteraction):
            username = inter.text_values["username"]
            email = inter.text_values["email"]
            password = inter.text_values["password"]
            discord_id = str(inter.author.id)
            try:
                async with aiohttp.ClientSession() as session:
                    headers = {
                        "Authorization": f"Bearer {self.cog.api_key}",
                        "Content-Type": "application/json",
                        "Accept": "application/json"
                    }
                    # Проверка: есть ли уже пользователь с таким email
                    check_url_email = f"{self.cog.api_url}/users?filter[email]={email}"
                    async with session.get(check_url_email, headers=headers) as check_resp_email:
                        if check_resp_email.status == 200:
                            data_email = await check_resp_email.json()
                            if data_email.get("data"):
                                await inter.response.send_message(
                                    "❌ На этот email уже зарегистрирован пользователь в панели.",
                                    ephemeral=True
                                )
                                return
                    # Проверка: сколько пользователей с таким Discord ID (в поле first_name)
                    check_url_id = f"{self.cog.api_url}/users?filter[first_name]={discord_id}"
                    async with session.get(check_url_id, headers=headers) as check_resp_id:
                        if check_resp_id.status == 200:
                            data_id = await check_resp_id.json()
                            count = len(data_id.get("data", []))
                            if count >= self.cog.discord_limit:
                                await inter.response.send_message(
                                    f"❌ Достигнут лимит аккаунтов для этого Discord: {self.cog.discord_limit}.",
                                    ephemeral=True
                                )
                                return
                    # Если не найден — создаём
                    payload = {
                        "username": username,
                        "email": email,
                        "first_name": discord_id,
                        "last_name": "discord",
                        "password": password
                    }
                    async with session.post(f"{self.cog.api_url}/users", headers=headers, json=payload) as resp:
                        if resp.status == 201:
                            await inter.response.send_message(
                                f"✅ Аккаунт успешно зарегистрирован!\nЛогин: `{username}`\nEmail: `{email}`\nПароль: `{password}`",
                                ephemeral=True
                            )
                        else:
                            data = await resp.text()
                            await inter.response.send_message(
                                f"❌ Не удалось зарегистрировать аккаунт. Код: {resp.status}\n{data}",
                                ephemeral=True
                            )
            except Exception as e:
                await inter.response.send_message(f"❌ Ошибка при регистрации: {e}", ephemeral=True)

    @commands.slash_command(name="setup_pterodactyl_status", description="Настроить панель мониторинга Pterodactyl")
    @commands.has_permissions(administrator=True)
    async def setup_pterodactyl_status(self, inter: disnake.ApplicationCommandInteraction):
        embed = disnake.Embed(
            title="💎 AmethystCloud • Панель Мониторинга", 
            description="⏳ Инициализация системы мониторинга...\n`████████░░░░░░░░░░░░` 40%", 
            color=0x9B59B6
        )
        msg = await inter.channel.send(embed=embed)
        self.status_message_id = msg.id
        self.status_channel_id = inter.channel.id
        self.save_status_data()
        await inter.response.send_message("✨ Панель мониторинга AmethystCloud успешно инициализирована!", ephemeral=True)

    @commands.slash_command(name="register", description="Зарегистрироваться в панели Pterodactyl")
    async def register(self, inter: disnake.ApplicationCommandInteraction):
        modal = self.PterodactylRegisterModal(self)
        await inter.response.send_modal(modal)

def setup(bot):
    bot.add_cog(PterodactylStatus(bot))
