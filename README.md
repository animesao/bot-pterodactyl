<div align="center">

# 💎 AmethystCloud Bot

[![Discord](https://img.shields.io/badge/Discord-Join%20Server-blue)](https://dsc.gg/darkcube)
[![GitHub Stars](https://img.shields.io/github/stars/animesao/bot-pterodactyl?style=social)](https://github.com/animesao/bot-pterodactyl/stargazers)
[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)
[![Disnake](https://img.shields.io/badge/Disnake-Latest-purple.svg)](https://docs.disnake.dev/)

**Профессиональный Discord бот для управления Pterodactyl панелью с расширенным функционалом**

[Возможности](#-возможности) • [Установка](#-установка) • [Команды](#-команды) • [Changelog](#-changelog)

</div>

---

## 🆕 Версия 2.0.0

### ✨ Новые функции

#### 💎 Система мониторинга нод
- **Отслеживание аптайма** - статистика доступности каждой ноды в процентах
- **Кастомные имена нод** - настраиваемые названия (например: "GER (Ryzen)", "GER2 (Epyc)")
- **Визуальные индикаторы** - красивые прогресс-бары с символами ▰▱
- **Автообновление** - мониторинг каждые 30 секунд
- **Команды управления**:
  ```bash
  /setup_pterodactyl_status    # Создать панель мониторинга
  /pterodactyl_uptime          # Детальная статистика аптайма
  /reset_pterodactyl_uptime    # Сброс статистики
  ```

#### 📨 Система отслеживания приглашений
- **Автоматический трекинг** - отслеживание кто кого пригласил
- **Статистика пользователей** - количество приглашений и активных участников
- **Таблица лидеров** - топ пользователей по приглашениям
- **Красивые уведомления** - embed сообщения при входе/выходе участников
- **Команды**:
  ```bash
  /invites [пользователь]      # Статистика приглашений
  /leaderboard                  # Топ по приглашениям
  /reset_invites <пользователь> # Сброс статистики (админ)
  ```

#### 🎫 Система тикетов
- **Категории тикетов** - Помощь и Покупка тарифа
- **Модальные формы** - удобный ввод информации
- **Логирование** - полная история тикетов с транскриптами
- **Назначение ответственных** - система распределения тикетов
- **Команды**:
  ```bash
  /setup_tickets               # Настроить панель тикетов
  ```

#### 📝 Система заявок
- **Роли**: Media и PR Manager
- **Автоматическая обработка** - кнопки принятия/отклонения
- **Уведомления в ЛС** - автоматические сообщения заявителям
- **Логирование** - история всех заявок
- **Команды**:
  ```bash
  /setup_apply                 # Настроить панель заявок
  ```

#### 🔐 Регистрация в Pterodactyl
- **Автоматическое создание аккаунтов** - регистрация через Discord
- **Лимиты аккаунтов** - контроль количества аккаунтов на пользователя
- **Проверка email** - валидация уникальности
- **Команды**:
  ```bash
  /register                    # Регистрация в панели
  ```

### ⚙ Улучшения

#### 🎨 Единый дизайн AmethystCloud
- Фиолетовая цветовая схема (💎 Purple) для всех модулей
- Консистентные embed сообщения с иконками и футерами
- Профессиональное форматирование с жирным текстом
- Временные метки на всех сообщениях

#### 🚀 Оптимизация производительности
- Асинхронная обработка всех запросов
- Кэширование данных о приглашениях
- Оптимизированные запросы к Pterodactyl API
- Улучшенная обработка ошибок с подробным логированием

#### 📊 Улучшенная типизация
- Type hints для всех функций и методов
- Использование Optional, Dict, List из typing
- Улучшенная читаемость кода

### 🐞 Исправления
- Исправлена проблема с таймаутом команды `/setup_apply`
- Устранены ошибки при обновлении статуса мониторинга
- Исправлена проблема с отображением аптайма нод
- Оптимизирована работа с файлами логов
- Улучшена обработка исключений во всех модулях

---

## 🆕 Version 2.0.0

### ✨ New Features

#### 💎 Node Monitoring System
- **Uptime tracking** - availability statistics for each node in percentages
- **Custom node names** - configurable names (e.g., "GER (Ryzen)", "GER2 (Epyc)")
- **Visual indicators** - beautiful progress bars with ▰▱ symbols
- **Auto-refresh** - monitoring every 30 seconds
- **Management commands**:
  ```bash
  /setup_pterodactyl_status    # Create monitoring panel
  /pterodactyl_uptime          # Detailed uptime statistics
  /reset_pterodactyl_uptime    # Reset statistics
  ```

#### 📨 Invite Tracking System
- **Automatic tracking** - monitor who invited whom
- **User statistics** - invitation count and active members
- **Leaderboard** - top users by invitations
- **Beautiful notifications** - embed messages on member join/leave
- **Commands**:
  ```bash
  /invites [user]              # Invitation statistics
  /leaderboard                 # Top invitations
  /reset_invites <user>        # Reset statistics (admin)
  ```

#### 🎫 Ticket System
- **Ticket categories** - Help and Tariff Purchase
- **Modal forms** - convenient information input
- **Logging** - complete ticket history with transcripts
- **Staff assignment** - ticket distribution system
- **Commands**:
  ```bash
  /setup_tickets               # Setup ticket panel
  ```

#### 📝 Application System
- **Roles**: Media and PR Manager
- **Automatic processing** - accept/reject buttons
- **DM notifications** - automatic messages to applicants
- **Logging** - history of all applications
- **Commands**:
  ```bash
  /setup_apply                 # Setup application panel
  ```

#### 🔐 Pterodactyl Registration
- **Automatic account creation** - registration via Discord
- **Account limits** - control number of accounts per user
- **Email validation** - uniqueness check
- **Commands**:
  ```bash
  /register                    # Register in panel
  ```

### ⚙ Improvements

#### 🎨 Unified AmethystCloud Design
- Purple color scheme (💎) for all modules
- Consistent embed messages with icons and footers
- Professional formatting with bold text
- Timestamps on all messages

#### 🚀 Performance Optimization
- Asynchronous processing of all requests
- Caching of invitation data
- Optimized Pterodactyl API requests
- Enhanced error handling with detailed logging

#### 📊 Improved Typing
- Type hints for all functions and methods
- Using Optional, Dict, List from typing
- Improved code readability

### 🐞 Fixes
- Fixed `/setup_apply` command timeout issue
- Resolved monitoring status update errors
- Fixed node uptime display problem
- Optimized log file handling
- Improved exception handling in all modules

---

## 🚀 Возможности

- 💎 **Мониторинг Pterodactyl** - отслеживание статуса панели и нод с аптаймом
- 🎫 **Система тикетов** - профессиональная поддержка пользователей
- 📝 **Система заявок** - автоматизация приема в команду
- 📨 **Трекинг приглашений** - статистика и лидерборд
- 🔐 **Регистрация** - автоматическое создание аккаунтов
- 💳 **Команда оплаты** - реквизиты для оплаты услуг
- 🎨 **Единый дизайн** - профессиональный стиль AmethystCloud

## 📦 Установка

### Требования
- Python 3.12+
- Discord Bot Token
- Pterodactyl Application API Key

### Шаги установки

1. **Клонируйте репозиторий**:
   ```bash
   git clone https://github.com/animesao/bot-pterodactyl.git
   cd bot-pterodactyl
   ```

2. **Установите зависимости**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Настройте `.env` файл**:
   ```env
   # Discord Bot Token
   token=YOUR_BOT_TOKEN

   # Pterodactyl Configuration
   PTERODACTYL_API_KEY=YOUR_API_KEY
   PTERODACTYL_STATUS_CHANNEL_ID=CHANNEL_ID
   PTERODACTYL_DISCORD_LIMIT=1

   # Pterodactyl Nodes (можно добавить больше)
   PTERODACTYL_NODE_1=5:GER (Ryzen)
   PTERODACTYL_NODE_2=9:GER2 (Epyc)

   # Ticket System
   HELP_CATEGORY_ID=CATEGORY_ID
   TARIFF_CATEGORY_ID=CATEGORY_ID
   TICKET_LOGS_CHANNEL_ID=CHANNEL_ID
   STAFF_ROLE_IDS=ROLE_ID1,ROLE_ID2

   # Applications
   APPLICATIONS_CHANNEL_ID=CHANNEL_ID
   APPLICATION_LOGS_CHANNEL_ID=CHANNEL_ID

   # Invites
   INVITE_LOGS_CHANNEL_ID=CHANNEL_ID
   ```

4. **Запустите бота**:
   ```bash
   python main.py
   ```

## 📋 Команды

### Мониторинг
- `/setup_pterodactyl_status` - Создать панель мониторинга
- `/pterodactyl_uptime` - Детальная статистика аптайма
- `/reset_pterodactyl_status` - Сброс панели мониторинга
- `/reset_pterodactyl_uptime` - Сброс статистики аптайма

### Регистрация
- `/register` - Регистрация в Pterodactyl панели

### Тикеты
- `/setup_tickets` - Настроить систему тикетов

### Заявки
- `/setup_apply` - Настроить систему заявок

### Приглашения
- `/invites [пользователь]` - Статистика приглашений
- `/leaderboard` - Топ по приглашениям
- `/reset_invites <пользователь>` - Сброс статистики (админ)

### Общие
- `!оплата` - Показать реквизиты для оплаты

## 🛠️ Структура проекта

```
bot-pterodactyl/
├── cogs/
│   ├── pterodactyl.py      # Мониторинг и регистрация
│   ├── tickets.py          # Система тикетов
│   ├── apply.py            # Система заявок
│   └── invites.py          # Трекинг приглашений
├── main.py                 # Главный файл бота
├── requirements.txt        # Зависимости
├── .env                    # Конфигурация (создать)
└── README.md              # Документация
```

## 📬 Поддержка | Support

📧 Email: igorerantaevigor66@gmail.com  
💬 Discord: animesao  
🌐 Server: [dsc.gg/alfheimguide](https://dsc.gg/alfheimguide)

---

<div align="center">

**Сделано с 💎 для AmethystCloud**

[![GitHub Stars](https://img.shields.io/github/stars/animesao/bot-pterodactyl?style=social)](https://github.com/animesao/bot-pterodactyl/stargazers)
[![Discord](https://img.shields.io/badge/Discord-Join%20Server-blue)](https://dsc.gg/alfheimguide)

</div>
