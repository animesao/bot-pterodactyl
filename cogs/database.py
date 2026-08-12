import sqlite3
import json
import os
import datetime
from typing import Any, Optional, Dict, List

DB_PATH = os.getenv("BOT_DB_PATH", "cogs/bot_settings.db")

_connection: Optional[sqlite3.Connection] = None


def get_connection() -> sqlite3.Connection:
    """Получить соединение с БД (создаётся при первом вызове)"""
    global _connection
    if _connection is None:
        _connection = sqlite3.connect(DB_PATH)
        _connection.row_factory = sqlite3.Row
        _init_tables()
    return _connection


def close_connection() -> None:
    """Закрыть соединение с БД"""
    global _connection
    if _connection is not None:
        _connection.close()
        _connection = None


def reinitialize_connection() -> None:
    """Переинициализировать соединение с БД (после замены файла)"""
    close_connection()
    get_connection()


def _init_tables() -> None:
    """Создание таблиц если их нет"""
    conn = _connection
    
    # Таблица настроек бота
    conn.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Таблица приглашений пользователей
    conn.execute("""
        CREATE TABLE IF NOT EXISTS invites (
            user_id INTEGER PRIMARY KEY,
            total_invites INTEGER DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Таблица истории приглашений
    conn.execute("""
        CREATE TABLE IF NOT EXISTS invited_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            inviter_id INTEGER NOT NULL,
            invited_user_id INTEGER NOT NULL,
            invited_username TEXT,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (inviter_id) REFERENCES invites(user_id)
        )
    """)
    
    # Таблица логов тикетов
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ticket_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id INTEGER NOT NULL,
            ticket_name TEXT,
            action TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            user_name TEXT,
            reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Таблица транскриптов тикетов
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ticket_transcripts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id INTEGER NOT NULL,
            ticket_name TEXT,
            channel_name TEXT,
            transcript TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Таблица аптайма нод Pterodactyl
    conn.execute("""
        CREATE TABLE IF NOT EXISTS node_uptime (
            node_id TEXT PRIMARY KEY,
            checks INTEGER DEFAULT 0,
            online INTEGER DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Таблица сообщений тикетов
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ticket_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id INTEGER NOT NULL,
            message_id INTEGER,
            user_id INTEGER NOT NULL,
            user_name TEXT,
            content TEXT,
            attachments TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()


def get_setting(key: str, default: Any = None) -> Any:
    """Получить настройку из БД"""
    conn = get_connection()
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    if row is None:
        return default
    try:
        return json.loads(row["value"])
    except (json.JSONDecodeError, TypeError):
        return row["value"]


def set_setting(key: str, value: Any) -> None:
    """Сохранить настройку в БД"""
    conn = get_connection()
    json_value = json.dumps(value)
    conn.execute("""
        INSERT INTO settings (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
    """, (key, json_value))
    conn.commit()


def is_registration_enabled() -> bool:
    """Проверить включена ли регистрация"""
    return get_setting("registration_enabled", True)


def set_registration_enabled(enabled: bool) -> None:
    """Включить/выключить регистрацию"""
    set_setting("registration_enabled", enabled)


# ==================== INVITES ====================

def get_invite_data(user_id: int) -> Dict:
    """Получить данные о приглашениях пользователя"""
    conn = get_connection()
    row = conn.execute(
        "SELECT total_invites FROM invites WHERE user_id = ?",
        (user_id,)
    ).fetchone()
    
    total = row["total_invites"] if row else 0
    
    # Получаем список приглашенных
    invited_rows = conn.execute(
        "SELECT invited_user_id, invited_username, joined_at FROM invited_users WHERE inviter_id = ? ORDER BY joined_at DESC",
        (user_id,)
    ).fetchall()
    
    invited_users = [
        {
            "user_id": r["invited_user_id"],
            "username": r["invited_username"],
            "joined_at": r["joined_at"]
        }
        for r in invited_rows
    ]
    
    return {"total_invites": total, "invited_users": invited_users}


def save_invite_data(user_id: int, data: Dict) -> None:
    """Сохранить данные о приглашениях пользователя"""
    conn = get_connection()
    
    conn.execute("""
        INSERT INTO invites (user_id, total_invites, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(user_id) DO UPDATE SET
            total_invites = excluded.total_invites,
            updated_at = CURRENT_TIMESTAMP
    """, (user_id, data.get("total_invites", 0)))
    
    conn.commit()


def add_invited_user(inviter_id: int, invited_user_id: int, invited_username: str) -> None:
    """Добавить приглашенного пользователя"""
    conn = get_connection()
    
    conn.execute("""
        INSERT INTO invited_users (inviter_id, invited_user_id, invited_username, joined_at)
        VALUES (?, ?, ?, ?)
    """, (inviter_id, invited_user_id, invited_username, datetime.datetime.utcnow().isoformat()))
    
    # Увеличиваем счетчик
    conn.execute("""
        INSERT INTO invites (user_id, total_invites, updated_at)
        VALUES (?, 1, CURRENT_TIMESTAMP)
        ON CONFLICT(user_id) DO UPDATE SET
            total_invites = total_invites + 1,
            updated_at = CURRENT_TIMESTAMP
    """, (inviter_id,))
    
    conn.commit()


def remove_invited_user(inviter_id: int, invited_user_id: int) -> int:
    """Удалить приглашенного пользователя и уменьшить счетчик. Возвращает новый счетчик."""
    conn = get_connection()
    
    conn.execute(
        "DELETE FROM invited_users WHERE inviter_id = ? AND invited_user_id = ?",
        (inviter_id, invited_user_id)
    )
    
    # Уменьшаем счетчик (но не меньше 0)
    conn.execute("""
        UPDATE invites SET
            total_invites = MAX(0, total_invites - 1),
            updated_at = CURRENT_TIMESTAMP
        WHERE user_id = ?
    """, (inviter_id,))
    
    conn.commit()
    
    row = conn.execute("SELECT total_invites FROM invites WHERE user_id = ?", (inviter_id,)).fetchone()
    return row["total_invites"] if row else 0


def find_inviter_by_user(invited_user_id: int) -> Optional[int]:
    """Найти кто пригласил пользователя. Возвращает inviter_id или None."""
    conn = get_connection()
    row = conn.execute(
        "SELECT inviter_id FROM invited_users WHERE invited_user_id = ? LIMIT 1",
        (invited_user_id,)
    ).fetchone()
    return row["inviter_id"] if row else None


def get_all_invite_data() -> List[Dict]:
    """Получить данные всех пользователей для leaderboard"""
    conn = get_connection()
    rows = conn.execute(
        "SELECT user_id, total_invites FROM invites WHERE total_invites > 0 ORDER BY total_invites DESC"
    ).fetchall()
    
    return [{"user_id": r["user_id"], "total_invites": r["total_invites"]} for r in rows]


def reset_invite_data(user_id: int) -> None:
    """Сбросить данные приглашений пользователя"""
    conn = get_connection()
    
    conn.execute("DELETE FROM invited_users WHERE inviter_id = ?", (user_id,))
    conn.execute("DELETE FROM invites WHERE user_id = ?", (user_id,))
    
    conn.commit()


# ==================== TICKET LOGS ====================

def add_ticket_log(ticket_id: int, ticket_name: str, action: str, user_id: int, user_name: str, reason: Optional[str] = None) -> None:
    """Добавить запись в логи тикета"""
    conn = get_connection()
    
    conn.execute("""
        INSERT INTO ticket_logs (ticket_id, ticket_name, action, user_id, user_name, reason, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (ticket_id, ticket_name, action, user_id, user_name, reason, datetime.datetime.utcnow().isoformat()))
    
    conn.commit()


def get_ticket_logs(ticket_id: int) -> List[Dict]:
    """Получить логи тикета"""
    conn = get_connection()
    rows = conn.execute(
        "SELECT action, user_id, user_name, reason, created_at FROM ticket_logs WHERE ticket_id = ? ORDER BY created_at ASC",
        (ticket_id,)
    ).fetchall()
    
    return [
        {
            "action": r["action"],
            "user_id": r["user_id"],
            "user_name": r["user_name"],
            "reason": r["reason"],
            "created_at": r["created_at"]
        }
        for r in rows
    ]


def save_ticket_transcript(ticket_id: int, ticket_name: str, channel_name: str, transcript: str) -> None:
    """Сохранить транскрипт тикета"""
    conn = get_connection()
    
    conn.execute("""
        INSERT INTO ticket_transcripts (ticket_id, ticket_name, channel_name, transcript, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (ticket_id, ticket_name, channel_name, transcript, datetime.datetime.utcnow().isoformat()))
    
    conn.commit()


def get_ticket_transcript(ticket_id: int) -> Optional[str]:
    """Получить транскрипт тикета"""
    conn = get_connection()
    row = conn.execute(
        "SELECT transcript FROM ticket_transcripts WHERE ticket_id = ? ORDER BY created_at DESC LIMIT 1",
        (ticket_id,)
    ).fetchone()
    return row["transcript"] if row else None


def get_recent_tickets(limit: int = 10) -> List[Dict]:
    """Получить список последних уникальных тикетов"""
    conn = get_connection()
    rows = conn.execute("""
        SELECT ticket_id, ticket_name, 
               MIN(created_at) as created_at,
               MAX(CASE WHEN action = 'Закрыт' THEN created_at END) as closed_at
        FROM ticket_logs 
        GROUP BY ticket_id 
        ORDER BY created_at DESC 
        LIMIT ?
    """, (limit,)).fetchall()
    
    return [
        {
            "ticket_id": r["ticket_id"],
            "ticket_name": r["ticket_name"],
            "created_at": r["created_at"],
            "closed_at": r["closed_at"]
        }
        for r in rows
    ]


def search_tickets(query: str, limit: int = 10) -> List[Dict]:
    """Поиск тикетов по имени канала или пользователю"""
    conn = get_connection()
    rows = conn.execute("""
        SELECT ticket_id, ticket_name, user_name, action, created_at
        FROM ticket_logs 
        WHERE ticket_name LIKE ? OR user_name LIKE ?
        GROUP BY ticket_id
        ORDER BY created_at DESC 
        LIMIT ?
    """, (f"%{query}%", f"%{query}%", limit)).fetchall()
    
    return [
        {
            "ticket_id": r["ticket_id"],
            "ticket_name": r["ticket_name"],
            "user_name": r["user_name"],
            "action": r["action"],
            "created_at": r["created_at"]
        }
        for r in rows
    ]


# ==================== TICKET MESSAGES ====================

def save_ticket_message(ticket_id: int, message_id: int, user_id: int, user_name: str, content: str, attachments: Optional[str] = None) -> None:
    """Сохранить сообщение из тикета"""
    conn = get_connection()
    
    conn.execute("""
        INSERT INTO ticket_messages (ticket_id, message_id, user_id, user_name, content, attachments, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (ticket_id, message_id, user_id, user_name, content, attachments, datetime.datetime.utcnow().isoformat()))
    
    conn.commit()


def get_ticket_messages(ticket_id: int, limit: int = 100) -> List[Dict]:
    """Получить сообщения тикета"""
    conn = get_connection()
    rows = conn.execute("""
        SELECT message_id, user_id, user_name, content, attachments, created_at
        FROM ticket_messages 
        WHERE ticket_id = ?
        ORDER BY created_at ASC
        LIMIT ?
    """, (ticket_id, limit)).fetchall()
    
    return [
        {
            "message_id": r["message_id"],
            "user_id": r["user_id"],
            "user_name": r["user_name"],
            "content": r["content"],
            "attachments": r["attachments"],
            "created_at": r["created_at"]
        }
        for r in rows
    ]


def get_ticket_messages_count(ticket_id: int) -> int:
    """Получить количество сообщений в тикете"""
    conn = get_connection()
    row = conn.execute(
        "SELECT COUNT(*) as count FROM ticket_messages WHERE ticket_id = ?",
        (ticket_id,)
    ).fetchone()
    return row["count"] if row else 0


def get_tickets_by_user(user_id: int, limit: int = 10, offset: int = 0) -> List[Dict]:
    """Получить тикеты пользователя по user_id"""
    conn = get_connection()
    rows = conn.execute("""
        SELECT ticket_id, ticket_name, user_name, action, created_at
        FROM ticket_logs 
        WHERE user_id = ?
        GROUP BY ticket_id
        ORDER BY created_at DESC 
        LIMIT ? OFFSET ?
    """, (user_id, limit, offset)).fetchall()
    
    return [
        {
            "ticket_id": r["ticket_id"],
            "ticket_name": r["ticket_name"],
            "user_name": r["user_name"],
            "action": r["action"],
            "created_at": r["created_at"]
        }
        for r in rows
    ]


def get_tickets_by_user_count(user_id: int) -> int:
    """Получить количество тикетов пользователя"""
    conn = get_connection()
    row = conn.execute(
        "SELECT COUNT(DISTINCT ticket_id) as count FROM ticket_logs WHERE user_id = ?",
        (user_id,)
    ).fetchone()
    return row["count"] if row else 0


def get_recent_tickets_paginated(limit: int = 10, offset: int = 0) -> List[Dict]:
    """Получить список тикетов с пагинацией"""
    conn = get_connection()
    rows = conn.execute("""
        SELECT ticket_id, ticket_name, 
               MIN(created_at) as created_at,
               MAX(CASE WHEN action = 'Закрыт' THEN created_at END) as closed_at
        FROM ticket_logs 
        GROUP BY ticket_id 
        ORDER BY created_at DESC 
        LIMIT ? OFFSET ?
    """, (limit, offset)).fetchall()
    
    return [
        {
            "ticket_id": r["ticket_id"],
            "ticket_name": r["ticket_name"],
            "created_at": r["created_at"],
            "closed_at": r["closed_at"]
        }
        for r in rows
    ]


def get_all_tickets_count() -> int:
    """Получить общее количество тикетов"""
    conn = get_connection()
    row = conn.execute(
        "SELECT COUNT(DISTINCT ticket_id) as count FROM ticket_logs"
    ).fetchone()
    return row["count"] if row else 0


def search_tickets_paginated(query: str, limit: int = 10, offset: int = 0) -> List[Dict]:
    """Поиск тикетов с пагинацией"""
    conn = get_connection()
    rows = conn.execute("""
        SELECT ticket_id, ticket_name, user_name, action, created_at
        FROM ticket_logs 
        WHERE ticket_name LIKE ? OR user_name LIKE ?
        GROUP BY ticket_id
        ORDER BY created_at DESC 
        LIMIT ? OFFSET ?
    """, (f"%{query}%", f"%{query}%", limit, offset)).fetchall()
    
    return [
        {
            "ticket_id": r["ticket_id"],
            "ticket_name": r["ticket_name"],
            "user_name": r["user_name"],
            "action": r["action"],
            "created_at": r["created_at"]
        }
        for r in rows
    ]


def search_tickets_count(query: str) -> int:
    """Получить количество тикетов по поиску"""
    conn = get_connection()
    row = conn.execute(
        "SELECT COUNT(DISTINCT ticket_id) as count FROM ticket_logs WHERE ticket_name LIKE ? OR user_name LIKE ?",
        (f"%{query}%", f"%{query}%")
    ).fetchone()
    return row["count"] if row else 0


# ==================== MIGRATION ====================

def migrate_invites_from_json(json_dir: str = "invite_data") -> int:
    """Миграция данных приглашений из JSON файлов в SQLite. Возвращает количество мигрированных записей."""
    if not os.path.exists(json_dir):
        return 0
    
    count = 0
    conn = get_connection()
    
    for filename in os.listdir(json_dir):
        if not filename.endswith(".json"):
            continue
        
        try:
            user_id = int(filename.replace(".json", ""))
            file_path = os.path.join(json_dir, filename)
            
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            total = data.get("total_invites", 0)
            
            conn.execute("""
                INSERT INTO invites (user_id, total_invites, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id) DO UPDATE SET
                    total_invites = MAX(total_invites, excluded.total_invites),
                    updated_at = CURRENT_TIMESTAMP
            """, (user_id, total))
            
            for invited in data.get("invited_users", []):
                invited_user_id = invited.get("user_id")
                if invited_user_id:
                    conn.execute("""
                        INSERT OR IGNORE INTO invited_users (inviter_id, invited_user_id, invited_username, joined_at)
                        VALUES (?, ?, ?, ?)
                    """, (user_id, invited_user_id, invited.get("username", ""), invited.get("joined_at", datetime.datetime.utcnow().isoformat())))
            
            count += 1
        except Exception as e:
            print(f"❌ Ошибка миграции {filename}: {e}")
    
    conn.commit()
    return count


# ==================== PTERODACTYL ====================

def get_node_uptime(node_id: str) -> Dict:
    """Получить данные аптайма ноды"""
    conn = get_connection()
    row = conn.execute(
        "SELECT checks, online FROM node_uptime WHERE node_id = ?",
        (node_id,)
    ).fetchone()
    
    if row:
        return {"checks": row["checks"], "online": row["online"]}
    return {"checks": 0, "online": 0}


def get_all_node_uptime() -> Dict[str, Dict]:
    """Получить данные аптайма всех нод"""
    conn = get_connection()
    rows = conn.execute("SELECT node_id, checks, online FROM node_uptime").fetchall()
    
    return {
        r["node_id"]: {"checks": r["checks"], "online": r["online"]}
        for r in rows
    }


def update_node_uptime(node_id: str, is_online: bool) -> None:
    """Обновить данные аптайма ноды"""
    conn = get_connection()
    
    conn.execute("""
        INSERT INTO node_uptime (node_id, checks, online, updated_at)
        VALUES (?, 1, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(node_id) DO UPDATE SET
            checks = checks + 1,
            online = online + ?,
            updated_at = CURRENT_TIMESTAMP
    """, (node_id, 1 if is_online else 0, 1 if is_online else 0))
    
    conn.commit()


def reset_node_uptime(node_id: Optional[str] = None) -> None:
    """Сбросить данные аптайма (все ноды или конкретную)"""
    conn = get_connection()
    
    if node_id:
        conn.execute("DELETE FROM node_uptime WHERE node_id = ?", (node_id,))
    else:
        conn.execute("DELETE FROM node_uptime")
    
    conn.commit()


def migrate_pterodactyl_uptime_from_json(json_file: str = "cogs/pterodactyl_uptime.json") -> int:
    """Миграция данных аптайма из JSON в SQLite"""
    if not os.path.exists(json_file):
        return 0
    
    count = 0
    conn = get_connection()
    
    try:
        with open(json_file, "r") as f:
            data = json.load(f)
        
        for node_id, uptime_data in data.items():
            checks = uptime_data.get("checks", 0)
            online = uptime_data.get("online", 0)
            
            conn.execute("""
                INSERT INTO node_uptime (node_id, checks, online, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(node_id) DO UPDATE SET
                    checks = excluded.checks,
                    online = excluded.online,
                    updated_at = CURRENT_TIMESTAMP
            """, (node_id, checks, online))
            count += 1
    except Exception as e:
        print(f"Error migrating uptime: {e}")
    
    conn.commit()
    return count


# ==================== DB STATS ====================

def get_db_stats() -> Dict:
    """Получить статистику всех таблиц БД"""
    conn = get_connection()
    
    stats = {}
    
    # Settings
    stats["settings"] = conn.execute("SELECT COUNT(*) as count FROM settings").fetchone()["count"]
    
    # Invites
    stats["invites"] = conn.execute("SELECT COUNT(*) as count FROM invites").fetchone()["count"]
    stats["total_invites"] = conn.execute("SELECT COALESCE(SUM(total_invites), 0) as total FROM invites").fetchone()["total"]
    stats["invited_users"] = conn.execute("SELECT COUNT(*) as count FROM invited_users").fetchone()["count"]
    
    # Tickets
    stats["ticket_logs"] = conn.execute("SELECT COUNT(*) as count FROM ticket_logs").fetchone()["count"]
    stats["ticket_transcripts"] = conn.execute("SELECT COUNT(*) as count FROM ticket_transcripts").fetchone()["count"]
    stats["unique_tickets"] = conn.execute("SELECT COUNT(DISTINCT ticket_id) as count FROM ticket_logs").fetchone()["count"]
    
    # Node uptime
    stats["node_uptime"] = conn.execute("SELECT COUNT(*) as count FROM node_uptime").fetchone()["count"]
    
    # DB file size
    stats["db_size"] = os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else 0
    
    return stats


def migrate_ticket_logs_from_json(json_dir: str = "ticket_logs") -> int:
    """Миграция логов тикетов из JSON файлов в SQLite. Возвращает количество мигрированных записей."""
    if not os.path.exists(json_dir):
        return 0
    
    count = 0
    conn = get_connection()
    
    for filename in os.listdir(json_dir):
        if not filename.endswith(".json"):
            continue
        
        try:
            ticket_id = int(filename.replace(".json", ""))
            file_path = os.path.join(json_dir, filename)
            
            with open(file_path, "r", encoding="utf-8") as f:
                logs = json.load(f)
            
            if not isinstance(logs, list):
                continue
            
            for entry in logs:
                conn.execute("""
                    INSERT INTO ticket_logs (ticket_id, ticket_name, action, user_id, user_name, reason, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    ticket_id,
                    entry.get("ticket_name", ""),
                    entry.get("action", ""),
                    entry.get("user_id", 0),
                    entry.get("user_name", ""),
                    entry.get("reason"),
                    entry.get("created_at", datetime.datetime.utcnow().isoformat())
                ))
            
            count += len(logs)
        except Exception as e:
            print(f"❌ Ошибка миграции {filename}: {e}")
    
    conn.commit()
    return count
