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
        self.api_key = "API-KEY-AP"
        self.node_id = 1
        self.status_channel_id = int(os.getenv("PTERODACTYL_STATUS_CHANNEL_ID", 0))
        self.status_message_id = None
        self.update_status.start()

    def cog_unload(self):
        self.update_status.cancel()

    @tasks.loop(seconds=5)
    async def update_status(self):
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Accept": "application/json"
                }
                
                # Проверяем доступность панели
                try:
                    async with session.get(f"{self.api_url}/nodes/{self.node_id}", headers=headers, timeout=5) as resp:
                        panel_online = resp.status == 200
                        if panel_online:
                            node = (await resp.json())["attributes"]
                            node_online = node.get("maintenance_mode", 1) == 0
                        else:
                            node_online = False
                except:
                    panel_online = False
                    node_online = False

                # Формируем embed
                embed = disnake.Embed(
                    title="HallCloud - Мониторинг",
                    color=disnake.Color.blue(),
                    timestamp=datetime.datetime.utcnow()
                )

                # Статус панели
                panel_status = "🟢 Панель: Включена" if panel_online else "🔴 Панель: Выключена"
                embed.add_field(name="Статус панели", value=panel_status, inline=False)

                # Статус ноды
                node_status = "🟢 Нода-1: Включена" if node_online else "🔴 Нода-1: Выключена"
                embed.add_field(name="Статус ноды", value=node_status, inline=False)

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
                description="Панель: Выключена\n Нода-1: Выключена"
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

    @commands.slash_command(name="setup_pterodactyl_status", description="Настроить панель мониторинга Pterodactyl")
    @commands.has_permissions(administrator=True)
    async def setup_pterodactyl_status(self, inter: disnake.ApplicationCommandInteraction):
        embed = disnake.Embed(title="HallCloud - Мониторинг", description="Загрузка статуса...", color=disnake.Color.blue())
        msg = await inter.channel.send(embed=embed)
        self.status_message_id = msg.id
        self.status_channel_id = inter.channel.id
        await inter.response.send_message("Панель мониторинга HallCloud успешно создана!", ephemeral=True)

def setup(bot):
    bot.add_cog(PterodactylStatus(bot))
