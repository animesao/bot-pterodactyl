import disnake
from disnake.ext import commands, tasks
import aiohttp
import os
import json
from dotenv import load_dotenv
import datetime
import traceback
from typing import Optional, Dict
from .database import (
    is_registration_enabled, set_registration_enabled, get_setting, set_setting,
    get_node_uptime, get_all_node_uptime, update_node_uptime, reset_node_uptime,
    get_db_stats, DB_PATH, reinitialize_connection, close_connection
)

load_dotenv()

BACKUP_DIR = "backups"
MAX_BACKUPS = 7  # Хранить последние 7 бэкапов


class PterodactylStatus(commands.Cog):
    """Система мониторинга статуса Pterodactyl панели"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.api_url = "https://panel.amethystcloud.online/api/application"
        self.api_key = os.getenv("PTERODACTYL_API_KEY", "")
        
        # Загрузка конфигурации нод из .env
        # Формат: NODE_1=5:GER (Ryzen),NODE_2=9:GER2 (Epyc)
        self.nodes = {}  # {id: name}
        self.load_nodes_config()
        
        self.status_channel_id = int(os.getenv("PTERODACTYL_STATUS_CHANNEL_ID", 0))
        self.status_message_id: Optional[int] = None
        self.discord_limit = int(os.getenv("PTERODACTYL_DISCORD_LIMIT", 1))
        
        self.last_panel_status: Optional[bool] = None
        self.last_node_statuses: dict = {}
        
        self.load_status_data()
        
        if self.status_message_id and not self.status_channel_id:
            self.status_message_id = None
            self.save_status_data()
    
    def load_nodes_config(self) -> None:
        """Загрузка конфигурации нод из .env"""
        # Пытаемся загрузить из переменных NODE_1, NODE_2, и т.д.
        node_index = 1
        while True:
            node_config = os.getenv(f"PTERODACTYL_NODE_{node_index}")
            if not node_config:
                break
            
            # Формат: "5:GER (Ryzen)" или просто "5"
            if ":" in node_config:
                node_id, node_name = node_config.split(":", 1)
                self.nodes[node_id.strip()] = node_name.strip()
            else:
                # Если имя не указано, используем ID
                node_id = node_config.strip()
                self.nodes[node_id] = f"#{node_id}"
            
            node_index += 1
        
        # Если ноды не настроены, используем старый формат
        if not self.nodes:
            old_node_ids = os.getenv("PTERODACTYL_NODE_IDS", "5,9").split(",")
            for node_id in old_node_ids:
                node_id = node_id.strip()
                self.nodes[node_id] = f"#{node_id}"
        
        print(f"✅ Загружено {len(self.nodes)} нод: {', '.join([f'{k}={v}' for k, v in self.nodes.items()])}")

    async def cog_load(self):
        """Запуск задач при загрузке cog"""
        self.update_status.start()
        self.daily_backup.start()
        os.makedirs(BACKUP_DIR, exist_ok=True)
        print("✅ Задачи Pterodactyl запущены")

    def cog_unload(self):
        """Остановка задач при выгрузке cog"""
        self.update_status.cancel()
        self.daily_backup.cancel()

    def load_status_data(self) -> None:
        """Загрузка данных о статусе из БД"""
        self.status_message_id = get_setting('status_message_id')
        self.status_channel_id = int(get_setting('status_channel_id', self.status_channel_id))

    def save_status_data(self) -> None:
        """Сохранение данных о статусе в БД"""
        set_setting('status_message_id', self.status_message_id)
        set_setting('status_channel_id', self.status_channel_id)
    
    def get_uptime_percentage(self, node_id: str) -> float:
        """Получение процента аптайма для ноды"""
        uptime_data = get_node_uptime(node_id)
        if uptime_data["checks"] == 0:
            return 0.0
        return (uptime_data["online"] / uptime_data["checks"]) * 100

    @tasks.loop(seconds=30)
    async def update_status(self):
        """Обновление статуса панели и нод"""
        if not self.status_message_id or not self.status_channel_id:
            return
            
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Accept": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                # Проверка панели
                panel_online = False
                try:
                    async with session.get(f"{self.api_url}/nodes", headers=headers, timeout=5) as resp:
                        panel_online = resp.status == 200
                        if not panel_online:
                            response_text = await resp.text()
                            print(f"⚠️ Панель недоступна. Статус: {resp.status}, Ответ: {response_text[:200]}")
                except Exception as e:
                    print(f"⚠️ Ошибка проверки панели: {type(e).__name__}: {e}")
                    panel_online = False

                # Проверка нод
                node_statuses = {}
                for node_id in self.nodes.keys():
                    node_online = False
                    try:
                        async with session.get(f"{self.api_url}/nodes/{node_id}", headers=headers, timeout=5) as resp:
                            node_online = resp.status == 200
                            if not node_online:
                                print(f"⚠️ Нода {node_id} ({self.nodes[node_id]}) недоступна. Статус: {resp.status}")
                    except Exception as e:
                        print(f"⚠️ Ошибка проверки ноды {node_id} ({self.nodes[node_id]}): {e}")
                        node_online = False
                    
                    node_statuses[node_id] = node_online
                    update_node_uptime(node_id, node_online)  # Обновляем статистику аптайма

                # Формирование embed
                embed_color = disnake.Color.purple()
                
                panel_emoji = "💎" if panel_online else "🔴"
                panel_text = "Работает стабильно" if panel_online else "Недоступна"
                
                node_lines = []
                online_count = sum(1 for online in node_statuses.values() if online)
                total_count = len(node_statuses)
                
                for node_id, online in node_statuses.items():
                    emoji = "💎" if online else "🔴"
                    status_bar = "▰▰▰▰▰▰▰▰▰▰" if online else "▱▱▱▱▱▱▱▱▱▱"
                    status = "UPTIME" if online else "Отключена"
                    uptime = self.get_uptime_percentage(node_id)
                    node_name = self.nodes.get(node_id, f"#{node_id}")
                    node_lines.append(f"{emoji} `{node_name}` {status_bar} **{status}** • `{uptime:.1f}%`")
                
                embed = disnake.Embed(
                    title="💎 AmethystCloud • Панель Мониторинга",
                    color=embed_color
                )
                
                embed.add_field(
                    name="🌐 Панель Управления",
                    value=f"\n{panel_emoji} **{panel_text}**\n\n━━━━━━━━━━━━━━━━━━━━",
                    inline=False
                )
                
                embed.add_field(
                    name=f"⚡ Статус Нод ({online_count}/{total_count})",
                    value="\n━━━━━━━━━━━━━━━━━━━━\n".join(node_lines),
                    inline=False
                )
                
                # Общий статус
                all_online = panel_online and all(node_statuses.values())
                if all_online:
                    overall_status = "▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰ **100%**"
                elif panel_online:
                    percentage = int((online_count / total_count) * 100) if total_count > 0 else 0
                    bar_filled = int((online_count / total_count) * 20) if total_count > 0 else 0
                    bar = "▰" * bar_filled + "▱" * (20 - bar_filled)
                    overall_status = f"{bar} **{percentage}%**"
                else:
                    overall_status = "▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱ **0%**"
                
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
                
                # Обновление сообщения
                channel = self.bot.get_channel(self.status_channel_id)
                if channel:
                    try:
                        msg = await channel.fetch_message(self.status_message_id)
                        await msg.edit(embed=embed)
                        print(f"✅ Статус обновлен: Панель={panel_online}, Ноды={online_count}/{total_count}")
                    except disnake.errors.NotFound:
                        print("⚠️ Сообщение статуса не найдено, сбрасываем ID")
                        self.status_message_id = None
                        self.save_status_data()
                    except Exception as e:
                        print(f"❌ Ошибка обновления сообщения: {e}")

        except Exception as e:
            print(f"❌ Критическая ошибка в update_status: {e}")
            print(traceback.format_exc())

    @update_status.before_loop
    async def before_update_status(self):
        """Ожидание готовности бота перед запуском задачи"""
        await self.bot.wait_until_ready()
        print("✅ Бот готов, задача мониторинга Pterodactyl начинает работу")

    # ==================== AUTO BACKUP ====================

    def create_backup(self) -> Optional[str]:
        """Создать бэкап БД. Возвращает имя файла или None при ошибке."""
        try:
            import shutil
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f"amethystcloud_backup_{timestamp}.db"
            backup_path = os.path.join(BACKUP_DIR, backup_filename)
            
            shutil.copy2(DB_PATH, backup_path)
            print(f"✅ Авто-бэкап создан: {backup_filename}")
            return backup_path
        except Exception as e:
            print(f"❌ Ошибка создания авто-бэкапа: {e}")
            return None

    def cleanup_old_backups(self) -> None:
        """Удалить старые бэкапы, оставив только MAX_BACKUPS последних"""
        try:
            if not os.path.exists(BACKUP_DIR):
                return
            
            # Получаем список бэкапов
            backups = []
            for f in os.listdir(BACKUP_DIR):
                if f.startswith('amethystcloud_backup_') and f.endswith('.db'):
                    filepath = os.path.join(BACKUP_DIR, f)
                    backups.append((filepath, os.path.getmtime(filepath)))
            
            # Сортируем по дате (новые первые)
            backups.sort(key=lambda x: x[1], reverse=True)
            
            # Удаляем старые
            for filepath, _ in backups[MAX_BACKUPS:]:
                os.remove(filepath)
                print(f"🗑️ Удален старый бэкап: {os.path.basename(filepath)}")
                
        except Exception as e:
            print(f"❌ Ошибка очистки бэкапов: {e}")

    @tasks.loop(hours=24)
    async def daily_backup(self):
        """Ежедневный бэкап базы данных"""
        try:
            # Создаем бэкап
            backup_path = self.create_backup()
            
            if backup_path:
                # Удаляем старые бэкапы
                self.cleanup_old_backups()
                
                # Считаем бэкапы
                backups_count = len([f for f in os.listdir(BACKUP_DIR) 
                                    if f.startswith('amethystcloud_backup_') and f.endswith('.db')])
                print(f"✅ Авто-бэкап завершен. Всего бэкапов: {backups_count}/{MAX_BACKUPS}")
                
        except Exception as e:
            print(f"❌ Ошибка в daily_backup: {e}")
            print(traceback.format_exc())

    @daily_backup.before_loop
    async def before_daily_backup(self):
        """Ожидание готовности бота перед запуском задачи"""
        await self.bot.wait_until_ready()
        print("✅ Задача авто-бэкапа запущена")

    class PterodactylRegisterModal(disnake.ui.Modal):
        """Модальное окно регистрации в Pterodactyl"""
        
        def __init__(self, cog: 'PterodactylStatus'):
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
            """Обработка регистрации пользователя"""
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
                    
                    check_url_id = f"{self.cog.api_url}/users?filter[first_name]={discord_id}"
                    async with session.get(check_url_id, headers=headers) as check_resp_id:
                        if check_resp_id.status == 200:
                            data_id = await check_resp_id.json()
                            count = len(data_id.get("data", []))
                            discord_limit = int(get_setting("discord_limit", self.cog.discord_limit))
                            if count >= discord_limit:
                                await inter.response.send_message(
                                    f"❌ Достигнут лимит аккаунтов для этого Discord: {discord_limit}.",
                                    ephemeral=True
                                )
                                return
                    
                    payload = {
                        "username": username,
                        "email": email,
                        "first_name": discord_id,
                        "last_name": "discord",
                        "password": password
                    }
                    
                    async with session.post(f"{self.cog.api_url}/users", headers=headers, json=payload) as resp:
                        if resp.status == 201:
                            success_embed = disnake.Embed(
                                title="✅ Регистрация успешна!",
                                description="Ваш аккаунт успешно создан в панели Pterodactyl",
                                color=disnake.Color.green(),
                                timestamp=datetime.datetime.utcnow()
                            )
                            success_embed.add_field(name="👤 Логин", value=f"`{username}`", inline=True)
                            success_embed.add_field(name="📧 Email", value=f"`{email}`", inline=True)
                            success_embed.add_field(name="🔑 Пароль", value=f"||`{password}`||", inline=False)
                            success_embed.set_footer(text="AmethystCloud Pterodactyl")
                            
                            await inter.response.send_message(embed=success_embed, ephemeral=True)
                        else:
                            data = await resp.text()
                            await inter.response.send_message(
                                f"❌ Не удалось зарегистрировать аккаунт. Код: {resp.status}\n```\n{data}\n```",
                                ephemeral=True
                            )
            except Exception as e:
                await inter.response.send_message(
                    f"❌ Ошибка при регистрации: {e}",
                    ephemeral=True
                )

    @commands.slash_command(name="setup_pterodactyl_status", description="Настроить панель мониторинга Pterodactyl")
    @commands.has_permissions(administrator=True)
    async def setup_pterodactyl_status(self, inter: disnake.ApplicationCommandInteraction):
        """Настройка панели мониторинга"""
        embed = disnake.Embed(
            title="💎 AmethystCloud • Панель Мониторинга", 
            description="⏳ Инициализация системы мониторинга...\n`████████░░░░░░░░░░░░` 40%", 
            color=disnake.Color.purple()
        )
        
        msg = await inter.channel.send(embed=embed)
        self.status_message_id = msg.id
        self.status_channel_id = inter.channel.id
        self.save_status_data()
        
        success_embed = disnake.Embed(
            title="✅ Успешно!",
            description="Панель мониторинга AmethystCloud успешно инициализирована!",
            color=disnake.Color.green()
        )
        await inter.response.send_message(embed=success_embed, ephemeral=True)

    @commands.slash_command(name="reset_pterodactyl_status", description="Сбросить панель мониторинга")
    @commands.has_permissions(administrator=True)
    async def reset_pterodactyl_status(self, inter: disnake.ApplicationCommandInteraction):
        """Сброс панели мониторинга"""
        try:
            # Удаляем старое сообщение если есть
            if self.status_message_id and self.status_channel_id:
                try:
                    channel = self.bot.get_channel(self.status_channel_id)
                    if channel:
                        msg = await channel.fetch_message(self.status_message_id)
                        await msg.delete()
                except:
                    pass
            
            # Сбрасываем данные
            self.status_message_id = None
            self.save_status_data()
            
            success_embed = disnake.Embed(
                title="✅ Сброшено!",
                description="Панель мониторинга сброшена. Используйте `/setup_pterodactyl_status` для создания новой.",
                color=disnake.Color.green()
            )
            await inter.response.send_message(embed=success_embed, ephemeral=True)
        except Exception as e:
            await inter.response.send_message(
                f"❌ Ошибка: {str(e)}",
                ephemeral=True
            )

    @commands.slash_command(name="reset_pterodactyl_uptime", description="Сбросить статистику аптайма нод")
    @commands.has_permissions(administrator=True)
    async def reset_pterodactyl_uptime(self, inter: disnake.ApplicationCommandInteraction):
        """Сброс статистики аптайма"""
        try:
            # Сбрасываем данные аптайма в БД
            reset_node_uptime()
            
            embed = disnake.Embed(
                title="✅ Статистика сброшена!",
                description="Статистика аптайма всех нод была сброшена.",
                color=disnake.Color.green()
            )
            await inter.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await inter.response.send_message(
                f"❌ Ошибка: {str(e)}",
                ephemeral=True
            )

    @commands.slash_command(name="pterodactyl_uptime", description="Показать детальную статистику аптайма")
    async def pterodactyl_uptime(self, inter: disnake.ApplicationCommandInteraction):
        """Показать детальную статистику аптайма нод"""
        try:
            embed = disnake.Embed(
                title="💎 AmethystCloud • Статистика Аптайма",
                color=disnake.Color.purple(),
                timestamp=datetime.datetime.utcnow()
            )
            
            for node_id, node_name in self.nodes.items():
                uptime_percentage = self.get_uptime_percentage(node_id)
                uptime_data = get_node_uptime(node_id)
                
                # Определяем цвет статуса
                if uptime_percentage >= 99:
                    status_emoji = "💎"
                    status_text = "Отличный"
                elif uptime_percentage >= 95:
                    status_emoji = "🟢"
                    status_text = "Хороший"
                elif uptime_percentage >= 90:
                    status_emoji = "🟡"
                    status_text = "Удовлетворительный"
                else:
                    status_emoji = "🔴"
                    status_text = "Плохой"
                
                embed.add_field(
                    name=f"{status_emoji} {node_name}",
                    value=(
                        f"**Аптайм:** `{uptime_percentage:.2f}%`\n"
                        f"**Статус:** {status_text}\n"
                        f"**Проверок:** `{uptime_data['checks']}`\n"
                        f"**Онлайн:** `{uptime_data['online']}`"
                    ),
                    inline=True
                )
            
            embed.set_footer(
                text="Статистика обновляется каждые 30 секунд",
                icon_url=self.bot.user.avatar.url if self.bot.user.avatar else self.bot.user.default_avatar.url
            )
            
            await inter.response.send_message(embed=embed)
            
        except Exception as e:
            await inter.response.send_message(
                f"❌ Ошибка: {str(e)}",
                ephemeral=True
            )

    @commands.slash_command(name="db_stats", description="Показать статистику базы данных")
    @commands.has_permissions(administrator=True)
    async def db_stats(self, inter: disnake.ApplicationCommandInteraction):
        """Показать статистику базы данных"""
        try:
            stats = get_db_stats()
            
            # Форматируем размер БД
            db_size = stats["db_size"]
            if db_size < 1024:
                size_str = f"{db_size} B"
            elif db_size < 1024 * 1024:
                size_str = f"{db_size / 1024:.2f} KB"
            else:
                size_str = f"{db_size / (1024 * 1024):.2f} MB"
            
            embed = disnake.Embed(
                title="📊 AmethystCloud • Статистика БД",
                description="Текущее состояние базы данных бота",
                color=disnake.Color.purple(),
                timestamp=datetime.datetime.utcnow()
            )
            
            embed.add_field(
                name="⚙️ Настройки",
                value=f"`{stats['settings']}` записей",
                inline=True
            )
            
            embed.add_field(
                name="📨 Приглашения",
                value=(
                    f"`{stats['invites']}` пользователей\n"
                    f"`{stats['total_invites']}` всего приглашений\n"
                    f"`{stats['invited_users']}` приглашенных"
                ),
                inline=True
            )
            
            embed.add_field(
                name="🎫 Тикеты",
                value=(
                    f"`{stats['unique_tickets']}` уникальных\n"
                    f"`{stats['ticket_logs']}` записей логов\n"
                    f"`{stats['ticket_transcripts']}` транскриптов"
                ),
                inline=True
            )
            
            embed.add_field(
                name="🖥️ Pterodactyl",
                value=f"`{stats['node_uptime']}` нод отслеживается",
                inline=True
            )
            
            embed.add_field(
                name="💾 Размер БД",
                value=f"`{size_str}`",
                inline=True
            )
            
            embed.set_footer(
                text="AmethystCloud Database Stats",
                icon_url=self.bot.user.avatar.url if self.bot.user.avatar else self.bot.user.default_avatar.url
            )
            
            await inter.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            await inter.response.send_message(
                f"❌ Ошибка: {str(e)}",
                ephemeral=True
            )

    @commands.slash_command(name="backup", description="Создать бэкап базы данных")
    @commands.has_permissions(administrator=True)
    async def backup(self, inter: disnake.ApplicationCommandInteraction):
        """Создать бэкап базы данных и отправить файл"""
        try:
            await inter.response.defer(ephemeral=True)
            
            # Формируем имя файла с датой
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f"amethystcloud_backup_{timestamp}.db"
            
            # Копируем БД во временный файл
            import shutil
            shutil.copy2(DB_PATH, backup_filename)
            
            # Получаем размер файла
            file_size = os.path.getsize(backup_filename)
            if file_size < 1024:
                size_str = f"{file_size} B"
            elif file_size < 1024 * 1024:
                size_str = f"{file_size / 1024:.2f} KB"
            else:
                size_str = f"{file_size / (1024 * 1024):.2f} MB"
            
            # Отправляем файл
            embed = disnake.Embed(
                title="💾 AmethystCloud • Бэкап БД",
                description=f"Бэкап базы данных успешно создан!",
                color=disnake.Color.green(),
                timestamp=datetime.datetime.utcnow()
            )
            embed.add_field(name="📁 Файл", value=f"`{backup_filename}`", inline=True)
            embed.add_field(name="📏 Размер", value=f"`{size_str}`", inline=True)
            embed.set_footer(
                text="AmethystCloud Backup",
                icon_url=self.bot.user.avatar.url if self.bot.user.avatar else self.bot.user.default_avatar.url
            )
            
            # Отправляем файл как вложение
            await inter.followup.send(
                embed=embed,
                file=disnake.File(backup_filename, filename=backup_filename),
                ephemeral=True
            )
            
            # Удаляем временный файл
            os.remove(backup_filename)
            
        except Exception as e:
            await inter.followup.send(
                f"❌ Ошибка при создании бэкапа: {str(e)}",
                ephemeral=True
            )

    @commands.slash_command(name="backup_list", description="Показать список всех бэкапов")
    @commands.has_permissions(administrator=True)
    async def backup_list(self, inter: disnake.ApplicationCommandInteraction):
        """Показать список всех бэкапов"""
        try:
            await inter.response.defer(ephemeral=True)
            
            if not os.path.exists(BACKUP_DIR):
                embed = disnake.Embed(
                    title="📁 AmethystCloud • Список Бэкапов",
                    description="Папка с бэкапами не найдена.",
                    color=disnake.Color.orange(),
                    timestamp=datetime.datetime.utcnow()
                )
                await inter.followup.send(embed=embed, ephemeral=True)
                return
            
            # Получаем список бэкапов
            backups = []
            for f in os.listdir(BACKUP_DIR):
                if f.startswith('amethystcloud_backup_') and f.endswith('.db'):
                    filepath = os.path.join(BACKUP_DIR, f)
                    mtime = os.path.getmtime(filepath)
                    size = os.path.getsize(filepath)
                    backups.append((f, mtime, size))
            
            # Сортируем по дате (новые первые)
            backups.sort(key=lambda x: x[1], reverse=True)
            
            if not backups:
                embed = disnake.Embed(
                    title="📁 AmethystCloud • Список Бэкапов",
                    description="Бэкапы не найдены.",
                    color=disnake.Color.orange(),
                    timestamp=datetime.datetime.utcnow()
                )
                await inter.followup.send(embed=embed, ephemeral=True)
                return
            
            embed = disnake.Embed(
                title="📁 AmethystCloud • Список Бэкапов",
                description=f"Найдено бэкапов: **{len(backups)}** (макс. {MAX_BACKUPS})",
                color=disnake.Color.purple(),
                timestamp=datetime.datetime.utcnow()
            )
            
            # Формируем список
            backup_lines = []
            total_size = 0
            
            for i, (filename, mtime, size) in enumerate(backups[:10], 1):  # Показываем макс. 10
                dt = datetime.datetime.fromtimestamp(mtime)
                date_str = dt.strftime('%d.%m.%Y %H:%M')
                
                if size < 1024:
                    size_str = f"{size} B"
                elif size < 1024 * 1024:
                    size_str = f"{size / 1024:.2f} KB"
                else:
                    size_str = f"{size / (1024 * 1024):.2f} MB"
                
                emoji = "🆕" if i == 1 else "💾"
                backup_lines.append(f"{emoji} `{filename}`\n   📅 {date_str} • 📏 {size_str}")
                total_size += size
            
            if len(backups) > 10:
                backup_lines.append(f"\n... и еще {len(backups) - 10} бэкапов")
            
            embed.add_field(
                name="📋 Бэкапы",
                value="\n".join(backup_lines),
                inline=False
            )
            
            # Общий размер
            if total_size < 1024 * 1024:
                total_str = f"{total_size / 1024:.2f} KB"
            else:
                total_str = f"{total_size / (1024 * 1024):.2f} MB"
            
            embed.add_field(
                name="📊 Статистика",
                value=f"**Всего:** {len(backups)} бэкапов\n**Общий размер:** {total_str}\n**Хранится:** {MAX_BACKUPS} последних",
                inline=True
            )
            
            embed.set_footer(
                text="AmethystCloud Backup List",
                icon_url=self.bot.user.avatar.url if self.bot.user.avatar else self.bot.user.default_avatar.url
            )
            
            await inter.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            await inter.followup.send(
                f"❌ Ошибка: {str(e)}",
                ephemeral=True
            )

    @commands.slash_command(name="backup_delete", description="Удалить конкретный бэкап")
    @commands.has_permissions(administrator=True)
    async def backup_delete(self, inter: disnake.ApplicationCommandInteraction, filename: str):
        """Удалить конкретный бэкап по имени файла"""
        try:
            await inter.response.defer(ephemeral=True)
            
            # Проверяем что файл существует и это бэкап
            if not filename.startswith('amethystcloud_backup_') or not filename.endswith('.db'):
                await inter.followup.send(
                    "❌ Неверный формат имени файла! Имя должно начинаться с `amethystcloud_backup_` и заканчиваться на `.db`",
                    ephemeral=True
                )
                return
            
            filepath = os.path.join(BACKUP_DIR, filename)
            
            if not os.path.exists(filepath):
                await inter.followup.send(
                    f"❌ Файл `{filename}` не найден!",
                    ephemeral=True
                )
                return
            
            # Получаем размер файла перед удалением
            file_size = os.path.getsize(filepath)
            if file_size < 1024:
                size_str = f"{file_size} B"
            elif file_size < 1024 * 1024:
                size_str = f"{file_size / 1024:.2f} KB"
            else:
                size_str = f"{file_size / (1024 * 1024):.2f} MB"
            
            # Удаляем файл
            os.remove(filepath)
            
            # Считаем оставшиеся бэкапы
            remaining = len([f for f in os.listdir(BACKUP_DIR) 
                            if f.startswith('amethystcloud_backup_') and f.endswith('.db')]) if os.path.exists(BACKUP_DIR) else 0
            
            embed = disnake.Embed(
                title="🗑️ AmethystCloud • Бэкап Удален",
                description="Бэкап успешно удален!",
                color=disnake.Color.green(),
                timestamp=datetime.datetime.utcnow()
            )
            embed.add_field(name="📁 Файл", value=f"`{filename}`", inline=True)
            embed.add_field(name="📏 Размер", value=f"`{size_str}`", inline=True)
            embed.add_field(name="📊 Осталось", value=f"`{remaining}` бэкапов", inline=True)
            embed.set_footer(
                text="AmethystCloud Backup Delete",
                icon_url=self.bot.user.avatar.url if self.bot.user.avatar else self.bot.user.default_avatar.url
            )
            
            await inter.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            await inter.followup.send(
                f"❌ Ошибка при удалении: {str(e)}",
                ephemeral=True
            )

    @commands.slash_command(name="restore", description="Восстановить БД из бэкапа")
    @commands.has_permissions(administrator=True)
    async def restore(self, inter: disnake.ApplicationCommandInteraction, file: disnake.Attachment):
        """Восстановить базу данных из загруженного бэкапа"""
        try:
            await inter.response.defer(ephemeral=True)
            
            # Проверяем расширение файла
            if not file.filename.endswith('.db'):
                await inter.followup.send(
                    "❌ Неверный формат файла! Допускаются только `.db` файлы.",
                    ephemeral=True
                )
                return
            
            # Скачиваем файл
            temp_path = f"temp_restore_{file.filename}"
            await file.save(temp_path)
            
            # Проверяем что это валидный SQLite файл
            import sqlite3
            try:
                test_conn = sqlite3.connect(temp_path)
                # Проверяем наличие основных таблиц
                tables = test_conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
                table_names = [t[0] for t in tables]
                test_conn.close()
                
                required_tables = ['settings', 'invites', 'ticket_logs']
                missing = [t for t in required_tables if t not in table_names]
                
                if missing:
                    os.remove(temp_path)
                    await inter.followup.send(
                        f"❌ Файл не является валидным бэкапом! Отсутствуют таблицы: {', '.join(missing)}",
                        ephemeral=True
                    )
                    return
                    
            except Exception as e:
                os.remove(temp_path)
                await inter.followup.send(
                    f"❌ Ошибка чтения файла: {str(e)}",
                    ephemeral=True
                )
                return
            
            # Создаем бэкап текущей БД перед восстановлением
            import shutil
            backup_before = f"backup_before_restore_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            shutil.copy2(DB_PATH, backup_before)
            
            # Закрываем текущее соединение
            close_connection()
            
            # Заменяем файл БД
            shutil.move(temp_path, DB_PATH)
            
            # Переинициализируем соединение
            reinitialize_connection()
            
            # Формируем ответ
            file_size = os.path.getsize(DB_PATH)
            if file_size < 1024:
                size_str = f"{file_size} B"
            elif file_size < 1024 * 1024:
                size_str = f"{file_size / 1024:.2f} KB"
            else:
                size_str = f"{file_size / (1024 * 1024):.2f} MB"
            
            embed = disnake.Embed(
                title="✅ AmethystCloud • БД Восстановлена",
                description="База данных успешно восстановлена из бэкапа!",
                color=disnake.Color.green(),
                timestamp=datetime.datetime.utcnow()
            )
            embed.add_field(name="📁 Файл", value=f"`{file.filename}`", inline=True)
            embed.add_field(name="📏 Размер", value=f"`{size_str}`", inline=True)
            embed.add_field(
                name="⚠️ Важно",
                value="Перезапустите бота для полного применения изменений.",
                inline=False
            )
            embed.set_footer(
                text="AmethystCloud Restore",
                icon_url=self.bot.user.avatar.url if self.bot.user.avatar else self.bot.user.default_avatar.url
            )
            
            await inter.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            except:
                pass
            await inter.followup.send(
                f"❌ Ошибка при восстановлении: {str(e)}",
                ephemeral=True
            )

    @commands.slash_command(name="register", description="Зарегистрироваться в панели Pterodactyl")
    async def register(self, inter: disnake.ApplicationCommandInteraction):
        """Регистрация в панели Pterodactyl"""
        if not is_registration_enabled():
            embed = disnake.Embed(
                title="🔒 Регистрация отключена",
                description="Регистрация в панели Pterodactyl временно отключена администратором.\n\nПопробуйте позже.",
                color=disnake.Color.red(),
                timestamp=datetime.datetime.utcnow()
            )
            await inter.response.send_message(embed=embed, ephemeral=True)
            return
        modal = self.PterodactylRegisterModal(self)
        await inter.response.send_modal(modal)

    # ==================== ADMIN PANEL ====================

    class AdminPanelView(disnake.ui.View):
        """Панель управления для администраторов"""
        
        def __init__(self, cog: 'PterodactylStatus'):
            super().__init__(timeout=None)
            self.cog = cog
            self._update_buttons()
        
        def _update_buttons(self):
            """Обновить кнопки в зависимости от состояния"""
            self.clear_items()
            
            reg_enabled = is_registration_enabled()
            
            # Кнопка toggle регистрации
            reg_emoji = "✅" if reg_enabled else "❌"
            reg_label = "Выключить регистрацию" if reg_enabled else "Включить регистрацию"
            reg_style = disnake.ButtonStyle.danger if reg_enabled else disnake.ButtonStyle.success
            
            reg_button = disnake.ui.Button(
                label=reg_label,
                emoji=reg_emoji,
                style=reg_style,
                custom_id="admin_toggle_registration"
            )
            self.add_item(reg_button)
            
            # Кнопка toggle лимита Discord
            limit = int(get_setting("discord_limit", 1))
            limit_label = f"Лимит аккаунтов: {limit}"
            limit_button = disnake.ui.Button(
                label=limit_label,
                emoji="🔢",
                style=disnake.ButtonStyle.secondary,
                custom_id="admin_toggle_limit"
            )
            self.add_item(limit_button)
            
            # Кнопка обновления
            refresh_button = disnake.ui.Button(
                label="Обновить",
                emoji="🔄",
                style=disnake.ButtonStyle.primary,
                custom_id="admin_refresh_panel"
            )
            self.add_item(refresh_button)

    def _build_admin_embed(self) -> disnake.Embed:
        """Создать embed для админ-панели"""
        reg_enabled = is_registration_enabled()
        discord_limit = int(get_setting("discord_limit", 1))
        
        status_emoji = "✅" if reg_enabled else "❌"
        status_text = "Включена" if reg_enabled else "Выключена"
        status_color = disnake.Color.green() if reg_enabled else disnake.Color.red()
        
        embed = disnake.Embed(
            title="⚙️ AmethystCloud • Панель Администратора",
            description="Управление настройками бота и Pterodactyl панели",
            color=status_color,
            timestamp=datetime.datetime.utcnow()
        )
        
        embed.add_field(
            name="🔐 Регистрация",
            value=f"**Статус:** {status_emoji} {status_text}\n"
                  f"**Лимит аккаунтов на Discord:** `{discord_limit}`\n\n"
                  f"*Нажмите кнопку ниже для переключения*",
            inline=False
        )
        
        embed.add_field(
            name="📋 Доступные команды",
            value=(
                "`/admin` — Открыть эту панель\n"
                "`/setup_pterodactyl_status` — Настроить мониторинг\n"
                "`/reset_pterodactyl_status` — Сбросить мониторинг\n"
                "`/reset_pterodactyl_uptime` — Сбросить статистику"
            ),
            inline=False
        )
        
        embed.set_footer(
            text="AmethystCloud Admin Panel",
            icon_url=self.bot.user.avatar.url if self.bot.user.avatar else self.bot.user.default_avatar.url
        )
        
        return embed

    @commands.slash_command(
        name="admin",
        description="Открыть панель администратора",
        default_member_permissions=disnake.Permissions(administrator=True)
    )
    async def admin_panel(self, inter: disnake.ApplicationCommandInteraction):
        """Панель администратора для управления ботом"""
        embed = self._build_admin_embed()
        view = self.AdminPanelView(self)
        await inter.response.send_message(embed=embed, view=view, ephemeral=True)

    @commands.Cog.listener()
    async def on_button_click(self, inter: disnake.MessageInteraction):
        """Обработка нажатий кнопок админ-панели"""
        try:
            if inter.component.custom_id == "admin_toggle_registration":
                # Переключение регистрации
                current = is_registration_enabled()
                set_registration_enabled(not current)
                
                # Обновляем панель
                panel_embed = self._build_admin_embed()
                view = self.AdminPanelView(self)
                await inter.response.edit_message(embed=panel_embed, view=view)
                
            elif inter.component.custom_id == "admin_toggle_limit":
                # Циклическое переключение лимита: 1 -> 2 -> 3 -> 5 -> 1
                current_limit = int(get_setting("discord_limit", 1))
                limits = [1, 2, 3, 5]
                idx = limits.index(current_limit) if current_limit in limits else 0
                new_limit = limits[(idx + 1) % len(limits)]
                set_setting("discord_limit", new_limit)
                
                # Обновляем панель
                panel_embed = self._build_admin_embed()
                view = self.AdminPanelView(self)
                await inter.response.edit_message(embed=panel_embed, view=view)
                
            elif inter.component.custom_id == "admin_refresh_panel":
                # Обновление панели
                panel_embed = self._build_admin_embed()
                view = self.AdminPanelView(self)
                await inter.response.edit_message(embed=panel_embed, view=view)
        except Exception as e:
            try:
                if not inter.response.is_done():
                    await inter.response.send_message(
                        f"❌ Ошибка: {str(e)}",
                        ephemeral=True
                    )
            except Exception:
                pass


def setup(bot):
    bot.add_cog(PterodactylStatus(bot))