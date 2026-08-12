<div align="center">

# 🤖 AmethystCloud Bot

### Discord Bot for Pterodactyl Panel Integration

[![GitHub Stars](https://img.shields.io/github/stars/animesao/bot-pterodactyl?style=social)](https://github.com/animesao/bot-pterodactyl/stargazers)
[![GitHub Issues](https://img.shields.io/github/issues/animesao/bot-pterodactyl)](https://github.com/animesao/bot-pterodactyl/issues)
[![Python](https://img.shields.io/badge/Python-3.10+-blue)](https://www.python.org/)
[![Disnake](https://img.shields.io/badge/Disnake-2.9+-purple)](https://disnake.readthedocs.io/)

</div>

---

## ✨ Features

### 🎫 Ticket System
- Multi-category ticket creation (Help, Tariff, etc.)
- Automatic transcripts and logging
- Staff assignment and management
- Full message history in SQLite database

### 🖥️ Pterodactyl Integration
- Server registration and management
- Real-time node status monitoring
- Uptime tracking with statistics
- Auto-limit account creation

### 📨 Invite Tracking
- Track who invited whom
- Leaderboard with rankings
- Invite reset commands

### 📝 Application System
- Staff applications with approval workflow
- Automatic role assignment
- Application logging

### 🔧 Admin Commands
- `/admin` - Admin panel with toggles
- `/db_stats` - Database statistics
- `/backup` - Create database backup
- `/backup_list` - List all backups
- `/restore` - Restore from backup
- `/ticket_history` - View ticket history with pagination

---

## 📋 Requirements

- **Python 3.10+**
- **Discord Bot Token** ([Discord Developer Portal](https://discord.com/developers/applications))
- **Pterodactyl Panel** with API access

---

## 🚀 Installation

### 1. Clone the repository

```bash
git clone https://github.com/animesao/bot-pterodactyl.git
cd bot-pterodactyl
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` and fill in your values:

```env
# Discord Bot Token (required)
token=YOUR_BOT_TOKEN_HERE

# Server restriction (optional)
# Set your server ID to restrict bot to one server
# Set to 0 to allow on all servers
ALLOWED_GUILD_ID=0

# Category IDs for tickets
HELP_CATEGORY_ID=YOUR_HELP_CATEGORY_ID
TARIFF_CATEGORY_ID=YOUR_TARIFF_CATEGORY_ID

# Channel IDs
TICKET_PANEL_CHANNEL_ID=YOUR_TICKET_PANEL_CHANNEL_ID
TICKET_LOGS_CHANNEL_ID=YOUR_TICKET_LOGS_CHANNEL_ID
INVITE_LOGS_CHANNEL_ID=YOUR_INVITE_LOGS_CHANNEL_ID
APPLICATIONS_CHANNEL_ID=YOUR_APPLICATIONS_CHANNEL_ID
APPLICATION_LOGS_CHANNEL_ID=YOUR_APPLICATION_LOGS_CHANNEL_ID

# Staff Role IDs (comma-separated)
STAFF_ROLE_IDS=ROLE_ID_1,ROLE_ID_2,ROLE_ID_3

# Pterodactyl Configuration
PTERODACTYL_URL=https://your-panel-url.com
PTERODACTYL_API_KEY=YOUR_PTERODACTYL_API_KEY
PTERODACTYL_STATUS_CHANNEL_ID=YOUR_STATUS_CHANNEL_ID
PTERODACTYL_DISCORD_LIMIT=1

# Pterodactyl Nodes (format: NODE_ID:NODE_NAME)
PTERODACTYL_NODE_1=1:Node 1
PTERODACTYL_NODE_2=2:Node 2
```

### 4. Run the bot

```bash
python main.py
```

---

## 📁 Project Structure

```
bot-pterodactyl/
├── main.py                 # Bot entry point
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables (not in git)
├── .env.example            # Environment template
├── .gitignore
├── README.md               # Project documentation
├── CONTRIBUTING.md         # Contribution guidelines
├── CHANGELOG.md            # Version history
├── cogs/
│   ├── __init__.py
│   ├── database.py         # SQLite database module
│   ├── pterodactyl.py      # Pterodactyl commands & monitoring
│   ├── tickets.py          # Ticket system
│   ├── invites.py          # Invite tracking
│   └── apply.py            # Application system
└── backups/                # Auto-backups (not in git)
```

---

## 💾 Database

The bot uses SQLite for all data storage. The database file is created automatically:

```
cogs/bot_settings.db
```

### Tables

| Table | Description |
|-------|-------------|
| `settings` | Bot settings and configuration |
| `invites` | User invite counts |
| `invited_users` | Invitation history |
| `ticket_logs` | Ticket action logs |
| `ticket_transcripts` | Ticket message transcripts |
| `ticket_messages` | All messages in ticket channels |
| `node_uptime` | Pterodactyl node uptime |

### Backups

- **Auto-backups**: Created every 24 hours (keeps last 7)
- **Manual backups**: Use `/backup` command
- **Restore**: Use `/restore` command with a backup file

---

## 🎮 Commands

### Admin Commands
| Command | Description |
|---------|-------------|
| `/admin` | Open admin panel |
| `/db_stats` | View database statistics |
| `/backup` | Create and download backup |
| `/backup_list` | List all backups |
| `/backup_delete` | Delete a specific backup |
| `/restore` | Restore database from backup |

### Ticket Commands
| Command | Description |
|---------|-------------|
| `/ticket_history` | View ticket history |
| `/ticket_history user:@user` | View user's tickets |
| `/ticket_history ticket_id:ID` | View ticket transcript |

### Pterodactyl Commands
| Command | Description |
|---------|-------------|
| `/register` | Register with Pterodactyl |
| `/setup_pterodactyl_status` | Setup status channel |

### Invite Commands
| Command | Description |
|---------|-------------|
| `/leaderboard` | View invite leaderboard |

---

## 🔒 Security Features

- **Server restriction**: Set `ALLOWED_GUILD_ID` to restrict bot to one server
- **Auto-leave**: Bot automatically leaves unauthorized servers
- **Admin-only commands**: Database and backup commands require admin role

---

## 🤝 Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## 📋 Changelog

See [CHANGELOG.md](CHANGELOG.md) for full version history and updates.

---

## 🛠️ Troubleshooting

### Bot doesn't start
- Check that `token` is set correctly in `.env`
- Ensure all required channel/category IDs are configured

### Commands don't work
- Verify bot has proper permissions in your server
- Check that slash commands are synced (restart bot)

### Database errors
- Ensure `cogs/` folder is writable
- Check disk space for backups

---

## 📄 License

See [LICENSE.txt](LICENSE.txt) for details.

---

## 📬 Support

- **Email**: igorerantaevigor66@gmail.com
- **Discord**: animesao
- **GitHub**: [animesao/bot-pterodactyl](https://github.com/animesao/bot-pterodactyl)

---

<div align="center">

Made with ❤️ for the community

</div>
