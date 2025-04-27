import disnake
from disnake.ext import commands, tasks
import aiohttp
import os
from dotenv import load_dotenv
import datetime
import traceback
import asyncio

load_dotenv()

class PterodactylStatus(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_url = "http://DOMEN/api/application"
        self.api_key = "API KEY"
        self.node_id = 1
        self.status_channel_id = int(os.getenv("PTERODACTYL_STATUS_CHANNEL_ID", 0))
        self.status_message_id = None
        self.update_status.start()

    def cog_unload(self):
        self.update_status.cancel()

    def format_bytes(self, mb):
        try:
            mb = float(mb)
            if mb < 1024:
                return f"{mb:.0f} MB"
            gb = mb / 1024
            return f"{gb:.2f} GB"
        except Exception:
            return "-"

    @tasks.loop(seconds=1)
    async def update_status(self):
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Accept": "application/json"
                }
                # Получаем инфо о ноде
                async with session.get(f"{self.api_url}/nodes/{self.node_id}", headers=headers) as resp:
                    if resp.status != 200:
                        embed = disnake.Embed(title="HallCloud - Мониторинг", color=disnake.Color.red(), description=f"Ошибка API: {resp.status}")
                        await self._send_or_edit(embed)
                        return
                    node = (await resp.json())["attributes"]
                # Получаем аллокации
                async with session.get(f"{self.api_url}/nodes/{self.node_id}/allocations", headers=headers) as resp:
                    allocations = (await resp.json()).get("data", []) if resp.status == 200 else []
                # Получаем все сервера
                async with session.get(f"{self.api_url}/servers", headers=headers) as resp:
                    servers = (await resp.json()).get("data", []) if resp.status == 200 else []
                node_servers = [s for s in servers if s["attributes"]["node"] == self.node_id]
                # Считаем занято/свободно RAM и диск
                total_ram_limit = node.get('memory', 0)
                total_disk_limit = node.get('disk', 0)
                used_ram = sum(s['attributes'].get('memory', 0) for s in node_servers)
                used_disk = sum(s['attributes'].get('disk', 0) for s in node_servers)
                free_ram = max(total_ram_limit - used_ram, 0)
                free_disk = max(total_disk_limit - used_disk, 0)
                # Формируем embed
                embed = disnake.Embed(
                    title="HallCloud - Мониторинг",
                    color=disnake.Color.blue(),
                    timestamp=datetime.datetime.utcnow()
                )
                # Статус панели (всегда включена, так как мы к ней обращаемся)
                panel_status = "🟢 Панель: Включена" if node.get("maintenance_mode", 1) == 0 else "🔴 Панель: Выключена"
                embed.add_field(name="Статус панели", value=panel_status, inline=False)
                # Статус ноды
                node_status = "🟢 Нода-1: Включена" if node.get("maintenance_mode", 1) == 0 else "🔴 Нода-1: Выключена"
                embed.add_field(name="Статус ноды", value=node_status, inline=False)
                # --- Остальные поля считаются, но не добавляются в embed ---
                # embed.add_field(name="ID", value=node['id'])
                # embed.add_field(name="Локация", value=node.get('location_id', '—'))
                # embed.add_field(name="Описание", value=node.get('description', '—'), inline=False)
                # embed.add_field(name="RAM лимит", value=self.format_bytes(total_ram_limit), inline=True)
                # embed.add_field(name="RAM занято", value=self.format_bytes(used_ram), inline=True)
                # embed.add_field(name="RAM свободно", value=self.format_bytes(free_ram), inline=True)
                # embed.add_field(name="Диск лимит", value=self.format_bytes(total_disk_limit), inline=True)
                # embed.add_field(name="Диск занято", value=self.format_bytes(used_disk), inline=True)
                # embed.add_field(name="Диск свободно", value=self.format_bytes(free_disk), inline=True)
                # embed.add_field(name="CPU лимит", value=f"{node.get('cpu', 0)}%", inline=True)
                # embed.add_field(name="Свободные аллокации", value=str(len([a for a in allocations if not a['attributes']['assigned']])), inline=True)
                # embed.add_field(name="Всего аллокаций", value=str(len(allocations)), inline=True)
                # --- Список серверов также не отображаем ---
                # if node_servers:
                #     server_lines = [f"`{s['attributes']['identifier']}` {s['attributes']['name']}" for s in node_servers]
                #     embed.add_field(name=f"Серверы на ноде ({len(node_servers)})", value="\n".join(server_lines), inline=False)
                # else:
                #     embed.add_field(name="Серверы на ноде", value="Нет серверов", inline=False)
                embed.set_footer(text=f"Последнее обновление: {datetime.datetime.now().strftime('%H:%M:%S')}")
                await self._send_or_edit(embed)
        except Exception as e:
            print(traceback.format_exc())
            embed = disnake.Embed(title="HallCloud - Мониторинг", color=disnake.Color.red(), description=f"Ошибка: {e}")
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
