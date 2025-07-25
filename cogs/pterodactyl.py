import disnake
from disnake.ext import commands, tasks
import aiohttp
import os
from dotenv import load_dotenv
import datetime
import traceback

load_dotenv()

class PterodactylStatus(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_url = "http://DOMEN/api/application"
        self.api_url_2 = "http://DOMEN/api/application"
        self.api_key = "Application API"
        self.api_key_2 = "Application API"
        self.node_id = "ID"
        self.node_id_2 = "ID"
        self.status_channel_id = int(os.getenv("PTERODACTYL_STATUS_CHANNEL_ID", 0))
        self.status_message_id = None
        self.update_status.start()

    def cog_unload(self):
        self.update_status.cancel()

    @tasks.loop(seconds=5)
    async def update_status(self):
        try:
            async with aiohttp.ClientSession() as session:
                # Проверяем доступность панели
                panel_online = False
                try:
                    headers = {
                        "Authorization": f"Bearer {self.api_key}",
                        "Accept": "application/json"
                    }
                    async with session.get(f"{self.api_url}/nodes", headers=headers, timeout=5) as resp:
                        panel_online = resp.status == 200
                except:
                    panel_online = False

                # Проверяем первую ноду
                maintenance_mode = 1
                node_online = False
                try:
                    headers = {
                        "Authorization": f"Bearer {self.api_key}",
                        "Accept": "application/json"
                    }
                    async with session.get(f"{self.api_url}/nodes/{self.node_id}", headers=headers, timeout=5) as resp:
                        if resp.status == 200:
                            node = (await resp.json())["attributes"]
                            maintenance_mode = node.get("maintenance_mode", 1)
                            node_online = maintenance_mode == 0
                except:
                    pass

                # Проверяем вторую ноду
                maintenance_mode_2 = 1
                node2_online = False
                try:
                    headers_2 = {
                        "Authorization": f"Bearer {self.api_key_2}",
                        "Accept": "application/json"
                    }
                    async with session.get(f"{self.api_url_2}/nodes/{self.node_id_2}", headers=headers_2, timeout=5) as resp:
                        if resp.status == 200:
                            node2 = (await resp.json())["attributes"]
                            maintenance_mode_2 = node2.get("maintenance_mode", 1)
                            node2_online = maintenance_mode_2 == 0
                except Exception as e:
                    print(f"Ошибка при проверке второй ноды: {str(e)}")
                    pass

                # Формируем embed
                embed = disnake.Embed(
                    title="HallCloud - Мониторинг",
                    color=disnake.Color.blue(),
                    timestamp=datetime.datetime.utcnow()
                )

                # Статус панели
                panel_status = "🟢 Панель: Включена" if panel_online else "🔴 Панель: Выключена"
                embed.add_field(name="Статус панели", value=panel_status, inline=False)

                # Статус ноды 1
                if not panel_online:
                    node_status = "🔴 Нода-1: Выключена"
                elif maintenance_mode == 1:
                    node_status = "🟡 Нода-1: Техническое обслуживание"
                elif node_online:
                    node_status = "🟢 Нода-1: Включена"
                else:
                    node_status = "🔴 Нода-1: Выключена"
                embed.add_field(name="Статус нод", value=node_status, inline=False)

                # Статус ноды 2
                if not panel_online:
                    node2_status = "🔴 Нода-2: Выключена"
                elif maintenance_mode_2 == 1:
                    node2_status = "🟡 Нода-2: Техническое обслуживание"
                elif node2_online:
                    node2_status = "🟢 Нода-2: Включена"
                else:
                    node2_status = "🔴 Нода-2: Выключена"
                embed.add_field(name="", value=node2_status, inline=False)

                embed.set_footer(
                    text=f"Последнее обновление: {datetime.datetime.now().strftime('%H:%M:%S')}",
                    icon_url=self.bot.user.avatar.url if self.bot.user.avatar else self.bot.user.default_avatar.url
                )
                await self._send_or_edit(embed)

        except Exception as e:
            print(traceback.format_exc())
            embed = disnake.Embed(
                title="HallCloud - Мониторинг",
                color=disnake.Color.red(),
                description="Панель: Выключена\nНода-1: Выключена\nНода-2: Выключена"
            )
            embed.set_footer(
                text=f"Последнее обновление: {datetime.datetime.now().strftime('%H:%M:%S')}",
                icon_url=self.bot.user.avatar.url if self.bot.user.avatar else self.bot.user.default_avatar.url
            )
            await self._send_or_edit(embed)

    async def _send_or_edit(self, embed):
        channel = self.bot.get_channel(self.status_channel_id)
        if not channel:
            return
        if self.status_message_id:
            try:
                msg = await channel.fetch_message(self.status_message_id)
                await msg.edit(embed=embed)
                return
            except Exception:
                pass
        msg = await channel.send(embed=embed)
        self.status_message_id = msg.id

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
            try:
                async with aiohttp.ClientSession() as session:
                    headers = {
                        "Authorization": f"Bearer {self.cog.api_key}",
                        "Content-Type": "application/json",
                        "Accept": "application/json"
                    }
                    # Проверка: есть ли уже пользователь с таким email
                    check_url = f"{self.cog.api_url}/users?filter[email]={email}"
                    async with session.get(check_url, headers=headers) as check_resp:
                        if check_resp.status == 200:
                            data = await check_resp.json()
                            if data.get("data"):
                                await inter.response.send_message(
                                    "❌ На этот Discord-аккаунт уже зарегистрирован пользователь в панели.",
                                    ephemeral=True
                                )
                                return
                    # Если не найден — создаём
                    payload = {
                        "username": username,
                        "email": email,
                        "first_name": str(inter.author),
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
        embed = disnake.Embed(title="HallCloud - Мониторинг", description="Загрузка статуса...", color=disnake.Color.blue())
        msg = await inter.channel.send(embed=embed)
        self.status_message_id = msg.id
        self.status_channel_id = inter.channel.id
        await inter.response.send_message("Панель мониторинга HallCloud успешно создана!", ephemeral=True)

    @commands.slash_command(name="register", description="Зарегистрироваться в панели Pterodactyl")
    async def register(self, inter: disnake.ApplicationCommandInteraction):
        modal = self.PterodactylRegisterModal(self)
        await inter.response.send_modal(modal)

def setup(bot):
    bot.add_cog(PterodactylStatus(bot))
