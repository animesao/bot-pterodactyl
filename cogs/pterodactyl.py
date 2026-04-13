import disnake
from disnake.ext import commands, tasks
import aiohttp
import os
import json
from dotenv import load_dotenv
import datetime
import traceback
from typing import Optional, Dict

load_dotenv()


class PterodactylStatus(commands.Cog):
    """Система мониторинга статуса Pterodactyl панели"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.api_url = "https://panel.mysite.ru/api/application"
        self.api_key = os.getenv("PTERODACTYL_API_KEY", "")
        
        # Загрузка конфигурации нод из .env
        # Формат: NODE_1=5:GER (Ryzen),NODE_2=9:GER2 (Epyc)
        self.nodes = {}  # {id: name}
        self.load_nodes_config()
        
        self.status_channel_id = int(os.getenv("PTERODACTYL_STATUS_CHANNEL_ID", 0))
        self.status_message_id: Optional[int] = None
        self.discord_limit = int(os.getenv("PTERODACTYL_DISCORD_LIMIT", 1))
        self.status_file = "cogs/pterodactyl_status.json"
        self.uptime_file = "cogs/pterodactyl_uptime.json"
        
        self.last_panel_status: Optional[bool] = None
        self.last_node_statuses: dict = {}
        self.node_uptime: Dict[str, Dict] = {}
        
        self.load_status_data()
        self.load_uptime_data()
        
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
            old_node_ids = os.getenv("PTERODACTYL_NODE_IDS", "ID,ID").split(",")
            for node_id in old_node_ids:
                node_id = node_id.strip()
                self.nodes[node_id] = f"#{node_id}"
        
        print(f"✅ Загружено {len(self.nodes)} нод: {', '.join([f'{k}={v}' for k, v in self.nodes.items()])}")

    async def cog_load(self):
        """Запуск задачи обновления при загрузке cog"""
        self.update_status.start()
        print("✅ Задача обновления статуса Pterodactyl запущена")

    def cog_unload(self):
        """Остановка задачи при выгрузке cog"""
        self.update_status.cancel()

    def load_status_data(self) -> None:
        """Загрузка данных о статусе из файла"""
        try:
            with open(self.status_file, 'r') as f:
                data = json.load(f)
                self.status_message_id = data.get('status_message_id')
                self.status_channel_id = data.get('status_channel_id', self.status_channel_id)
        except FileNotFoundError:
            pass

    def save_status_data(self) -> None:
        """Сохранение данных о статусе в файл"""
        data = {
            'status_message_id': self.status_message_id,
            'status_channel_id': self.status_channel_id
        }
        with open(self.status_file, 'w') as f:
            json.dump(data, f)
    
    def load_uptime_data(self) -> None:
        """Загрузка данных об аптайме из файла"""
        try:
            with open(self.uptime_file, 'r') as f:
                self.node_uptime = json.load(f)
        except FileNotFoundError:
            # Инициализация данных для каждой ноды
            self.node_uptime = {node_id: {"checks": 0, "online": 0} for node_id in self.nodes.keys()}
            self.save_uptime_data()
    
    def save_uptime_data(self) -> None:
        """Сохранение данных об аптайме в файл"""
        with open(self.uptime_file, 'w') as f:
            json.dump(self.node_uptime, f, indent=2)
    
    def update_uptime(self, node_id: str, is_online: bool) -> None:
        """Обновление статистики аптайма для ноды"""
        if node_id not in self.node_uptime:
            self.node_uptime[node_id] = {"checks": 0, "online": 0}
        
        self.node_uptime[node_id]["checks"] += 1
        if is_online:
            self.node_uptime[node_id]["online"] += 1
        
        self.save_uptime_data()
    
    def get_uptime_percentage(self, node_id: str) -> float:
        """Получение процента аптайма для ноды"""
        if node_id not in self.node_uptime or self.node_uptime[node_id]["checks"] == 0:
            return 0.0
        
        uptime_data = self.node_uptime[node_id]
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
                    self.update_uptime(node_id, node_online)  # Обновляем статистику аптайма

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
                            if count >= self.cog.discord_limit:
                                await inter.response.send_message(
                                    f"❌ Достигнут лимит аккаунтов для этого Discord: {self.cog.discord_limit}.",
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
            # Сбрасываем данные аптайма
            self.node_uptime = {node_id: {"checks": 0, "online": 0} for node_id in self.nodes.keys()}
            self.save_uptime_data()
            
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
                uptime_data = self.node_uptime.get(node_id, {"checks": 0, "online": 0})
                
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

    @commands.slash_command(name="register", description="Зарегистрироваться в панели Pterodactyl")
    async def register(self, inter: disnake.ApplicationCommandInteraction):
        """Регистрация в панели Pterodactyl"""
        modal = self.PterodactylRegisterModal(self)
        await inter.response.send_modal(modal)

def setup(bot):
    bot.add_cog(PterodactylStatus(bot))
