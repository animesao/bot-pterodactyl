# 📋 Changelog

All notable changes to AmethystCloud Bot will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.0.0] - 2026-08-12

### 🎉 Major Release - Full Database Migration

#### ✨ Added

**Database System**
- New SQLite database module (`cogs/database.py`)
- All data now stored in single database file (`cogs/bot_settings.db`)
- Automatic database creation on first run

**Admin Commands**
- `/admin` - Interactive admin panel with buttons
- `/db_stats` - View database statistics
- `/backup` - Create and download database backup
- `/backup_list` - List all available backups
- `/backup_delete` - Delete specific backup
- `/restore` - Restore database from uploaded backup

**Auto-Backups**
- Automatic backups every 24 hours
- Keeps last 7 backups in `backups/` folder
- Cleanup of old backups automatically

**Ticket System Improvements**
- `/ticket_history` - View ticket history with pagination
- Ticket history with page navigation buttons
- Search tickets by user
- Search tickets by keyword
- Export long transcripts as text files
- All messages in tickets now saved to database

**Server Security**
- `ALLOWED_GUILD_ID` environment variable
- Bot restricts to single Discord server
- Auto-leave from unauthorized servers

**Documentation**
- Updated `README.md` with full installation guide
- New `CONTRIBUTING.md` for contributors
- New `CHANGELOG.md` (this file)
- New `.env.example` template

#### 🔄 Changed

**Data Storage**
- Migrated all JSON files to SQLite database
- `invite_data/` folder no longer needed
- `ticket_logs/` folder no longer needed
- `pterodactyl_status.json` no longer needed
- `pterodactyl_uptime.json` no longer needed

**Ticket System**
- Ticket transcripts now stored in database
- Ticket logs now stored in database
- Ticket messages saved in real-time

**Invite System**
- Invite data stored in database
- Invited users history stored in database

**Pterodactyl**
- Status data stored in database settings
- Node uptime stored in database
- Registration toggle stored in database

#### 🗑️ Removed

- Deleted `invite_data/*.json` (32 files)
- Deleted `ticket_logs/*.json` (60 files)
- Deleted `cogs/pterodactyl_status.json`
- Deleted `cogs/pterodactyl_uptime.json`
- Removed file-based storage completely

#### 🔧 Fixed

- Requirements.txt encoding issue (was UTF-16)
- Long ticket transcripts causing Discord API errors
- Ticket history embed field length limit

---

## [1.2.0] - Previous Version

### ✨ Added
- Authorization system `/register`
- Pterodactyl server registration
- Server monitoring `/setup_pterodactyl_status`
- Invite tracking system
- Application system for staff

### ⚙ Improved
- GitHub API integration optimization
- Command interface design
- Auto language switching (RU/EN)

### 🐞 Fixed
- Critical bug fixes
- Command autocomplete
- Cache issues

---

## 📊 Statistics

### Database Tables

| Table | Description | Added in |
|-------|-------------|----------|
| `settings` | Bot configuration | 2.0.0 |
| `invites` | User invite counts | 2.0.0 |
| `invited_users` | Invitation history | 2.0.0 |
| `ticket_logs` | Ticket action logs | 2.0.0 |
| `ticket_transcripts` | Ticket transcripts | 2.0.0 |
| `ticket_messages` | All ticket messages | 2.0.0 |
| `node_uptime` | Pterodactyl node uptime | 2.0.0 |

### Commands Added in 2.0.0

| Command | Permission | Description |
|---------|------------|-------------|
| `/admin` | Admin | Admin panel |
| `/db_stats` | Admin | Database statistics |
| `/backup` | Admin | Create backup |
| `/backup_list` | Admin | List backups |
| `/backup_delete` | Admin | Delete backup |
| `/restore` | Admin | Restore backup |
| `/ticket_history` | Everyone | Ticket history |

---

## 📝 Version History

```
2.0.0 - Full database migration, admin commands, auto-backups
1.2.0 - Pterodactyl integration, invite tracking, applications
1.1.0 - Ticket system improvements
1.0.0 - Initial release
```

---

## 🔮 Planned

- [ ] Unit tests
- [ ] GitHub Actions CI/CD
- [ ] Web dashboard for database
- [ ] Multi-language support
- [ ] Docker deployment
- [ ] MySQL/PostgreSQL support

---

## 📬 Support

If you find any bugs or have feature requests:

1. Check [existing issues](https://github.com/animesao/bot-pterodactyl/issues)
2. Create a new issue with details
3. Or contact: igorerantaevigor66@gmail.com

---

<div align="center">

Made with ❤️ by AmethystCloud Team

</div>
