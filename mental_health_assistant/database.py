from __future__ import annotations

from datetime import date, datetime, timezone
import hashlib
import hmac
import json
from pathlib import Path
import secrets
import sqlite3


BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = BASE_DIR / "mood_assistant.db"


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        120_000,
    ).hex()
    return f"{salt}${digest}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt, digest = stored_hash.split("$", maxsplit=1)
    except ValueError:
        return False

    calculated = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        120_000,
    ).hex()
    return hmac.compare_digest(digest, calculated)


class DatabaseManager:
    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH):
        self.db_path = Path(db_path)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    display_name TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS profiles (
                    user_id INTEGER PRIMARY KEY,
                    pronouns TEXT NOT NULL DEFAULT '',
                    age_group TEXT NOT NULL DEFAULT '',
                    support_focus TEXT NOT NULL DEFAULT '',
                    reminder_time TEXT NOT NULL DEFAULT '20:00',
                    reminders_enabled INTEGER NOT NULL DEFAULT 1,
                    affirmation_style TEXT NOT NULL DEFAULT 'gentle',
                    warning_signs TEXT NOT NULL DEFAULT '',
                    calming_plan TEXT NOT NULL DEFAULT '',
                    emergency_contact_name TEXT NOT NULL DEFAULT '',
                    emergency_contact_phone TEXT NOT NULL DEFAULT '',
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS mood_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    entry_date TEXT NOT NULL,
                    mood_score INTEGER NOT NULL,
                    mood_label TEXT NOT NULL,
                    emotions_json TEXT NOT NULL,
                    stress_level INTEGER NOT NULL,
                    energy_level INTEGER NOT NULL,
                    sleep_hours REAL NOT NULL,
                    journal_note TEXT NOT NULL DEFAULT '',
                    gratitude_note TEXT NOT NULL DEFAULT '',
                    coping_strategy TEXT NOT NULL DEFAULT '',
                    triggers_text TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE (user_id, entry_date),
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    source TEXT NOT NULL DEFAULT 'local',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS affirmations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    affirmation_text TEXT NOT NULL,
                    theme TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
                """
            )

    def register_user(self, display_name: str, email: str, password: str) -> int:
        cleaned_name = display_name.strip()
        cleaned_email = email.strip().lower()
        cleaned_password = password.strip()

        if not cleaned_name:
            raise ValueError("Display name cannot be empty.")
        if "@" not in cleaned_email:
            raise ValueError("Enter a valid email address.")
        if len(cleaned_password) < 8:
            raise ValueError("Password must be at least 8 characters long.")

        created_at = utc_timestamp()
        try:
            with self._connect() as connection:
                cursor = connection.execute(
                    """
                    INSERT INTO users (display_name, email, password_hash, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        cleaned_name,
                        cleaned_email,
                        hash_password(cleaned_password),
                        created_at,
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO profiles (
                        user_id,
                        updated_at
                    )
                    VALUES (?, ?)
                    """,
                    (cursor.lastrowid, created_at),
                )
                return cursor.lastrowid
        except sqlite3.IntegrityError as error:
            raise ValueError("An account with that email already exists.") from error

    def authenticate_user(self, email: str, password: str) -> dict[str, object] | None:
        cleaned_email = email.strip().lower()
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, display_name, email, password_hash, created_at
                FROM users
                WHERE email = ?
                """,
                (cleaned_email,),
            ).fetchone()
        if not row or not verify_password(password, row["password_hash"]):
            return None
        return {
            "id": row["id"],
            "display_name": row["display_name"],
            "email": row["email"],
            "created_at": row["created_at"],
        }

    def get_user(self, user_id: int) -> dict[str, object] | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, display_name, email, created_at
                FROM users
                WHERE id = ?
                """,
                (user_id,),
            ).fetchone()
        if not row:
            return None
        return dict(row)

    def get_profile(self, user_id: int) -> dict[str, object]:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    user_id,
                    pronouns,
                    age_group,
                    support_focus,
                    reminder_time,
                    reminders_enabled,
                    affirmation_style,
                    warning_signs,
                    calming_plan,
                    emergency_contact_name,
                    emergency_contact_phone,
                    updated_at
                FROM profiles
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()
        if not row:
            return {
                "user_id": user_id,
                "pronouns": "",
                "age_group": "",
                "support_focus": "",
                "reminder_time": "20:00",
                "reminders_enabled": 1,
                "affirmation_style": "gentle",
                "warning_signs": "",
                "calming_plan": "",
                "emergency_contact_name": "",
                "emergency_contact_phone": "",
            }
        return dict(row)

    def upsert_profile(
        self,
        user_id: int,
        pronouns: str,
        age_group: str,
        support_focus: str,
        reminder_time: str,
        reminders_enabled: bool,
        affirmation_style: str,
        warning_signs: str,
        calming_plan: str,
        emergency_contact_name: str,
        emergency_contact_phone: str,
    ) -> None:
        updated_at = utc_timestamp()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO profiles (
                    user_id,
                    pronouns,
                    age_group,
                    support_focus,
                    reminder_time,
                    reminders_enabled,
                    affirmation_style,
                    warning_signs,
                    calming_plan,
                    emergency_contact_name,
                    emergency_contact_phone,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    pronouns = excluded.pronouns,
                    age_group = excluded.age_group,
                    support_focus = excluded.support_focus,
                    reminder_time = excluded.reminder_time,
                    reminders_enabled = excluded.reminders_enabled,
                    affirmation_style = excluded.affirmation_style,
                    warning_signs = excluded.warning_signs,
                    calming_plan = excluded.calming_plan,
                    emergency_contact_name = excluded.emergency_contact_name,
                    emergency_contact_phone = excluded.emergency_contact_phone,
                    updated_at = excluded.updated_at
                """,
                (
                    user_id,
                    pronouns.strip(),
                    age_group.strip(),
                    support_focus.strip(),
                    reminder_time.strip() or "20:00",
                    int(reminders_enabled),
                    affirmation_style.strip() or "gentle",
                    warning_signs.strip(),
                    calming_plan.strip(),
                    emergency_contact_name.strip(),
                    emergency_contact_phone.strip(),
                    updated_at,
                ),
            )

    def get_today_entry(self, user_id: int) -> dict[str, object] | None:
        return self.get_mood_entry_for_date(user_id, date.today().isoformat())

    def get_mood_entry_for_date(
        self,
        user_id: int,
        entry_date: str,
    ) -> dict[str, object] | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM mood_entries
                WHERE user_id = ? AND entry_date = ?
                """,
                (user_id, entry_date),
            ).fetchone()
        if not row:
            return None
        return self._mood_row_to_dict(row)

    def upsert_mood_entry(
        self,
        user_id: int,
        entry_date: str,
        mood_score: int,
        mood_label: str,
        emotions: list[str],
        stress_level: int,
        energy_level: int,
        sleep_hours: float,
        journal_note: str,
        gratitude_note: str,
        coping_strategy: str,
        triggers_text: str,
    ) -> None:
        timestamp = utc_timestamp()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO mood_entries (
                    user_id,
                    entry_date,
                    mood_score,
                    mood_label,
                    emotions_json,
                    stress_level,
                    energy_level,
                    sleep_hours,
                    journal_note,
                    gratitude_note,
                    coping_strategy,
                    triggers_text,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, entry_date) DO UPDATE SET
                    mood_score = excluded.mood_score,
                    mood_label = excluded.mood_label,
                    emotions_json = excluded.emotions_json,
                    stress_level = excluded.stress_level,
                    energy_level = excluded.energy_level,
                    sleep_hours = excluded.sleep_hours,
                    journal_note = excluded.journal_note,
                    gratitude_note = excluded.gratitude_note,
                    coping_strategy = excluded.coping_strategy,
                    triggers_text = excluded.triggers_text,
                    updated_at = excluded.updated_at
                """,
                (
                    user_id,
                    entry_date,
                    int(mood_score),
                    mood_label.strip(),
                    json.dumps(emotions),
                    int(stress_level),
                    int(energy_level),
                    float(sleep_hours),
                    journal_note.strip(),
                    gratitude_note.strip(),
                    coping_strategy.strip(),
                    triggers_text.strip(),
                    timestamp,
                    timestamp,
                ),
            )

    def get_mood_entries(self, user_id: int, days: int = 120) -> list[dict[str, object]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM mood_entries
                WHERE user_id = ?
                ORDER BY entry_date DESC, updated_at DESC
                LIMIT ?
                """,
                (user_id, days),
            ).fetchall()
        return [self._mood_row_to_dict(row) for row in rows]

    def add_chat_message(self, user_id: int, role: str, content: str, source: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO chat_messages (
                    user_id,
                    role,
                    content,
                    source,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    role.strip(),
                    content.strip(),
                    source.strip(),
                    utc_timestamp(),
                ),
            )

    def get_chat_history(self, user_id: int, limit: int = 24) -> list[dict[str, object]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT role, content, source, created_at
                FROM chat_messages
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()
        history = [dict(row) for row in reversed(rows)]
        return history

    def clear_chat_history(self, user_id: int) -> None:
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM chat_messages WHERE user_id = ?",
                (user_id,),
            )

    def add_affirmation(self, user_id: int, affirmation_text: str, theme: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO affirmations (
                    user_id,
                    affirmation_text,
                    theme,
                    created_at
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    user_id,
                    affirmation_text.strip(),
                    theme.strip(),
                    utc_timestamp(),
                ),
            )

    def get_recent_affirmations(self, user_id: int, limit: int = 8) -> list[dict[str, object]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT affirmation_text, theme, created_at
                FROM affirmations
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def export_user_data(self, user_id: int) -> dict[str, object]:
        user = self.get_user(user_id)
        profile = self.get_profile(user_id)
        mood_entries = self.get_mood_entries(user_id, days=3650)
        affirmations = self.get_recent_affirmations(user_id, limit=3650)
        chat_history = self.get_chat_history(user_id, limit=5000)
        return {
            "user": user,
            "profile": profile,
            "mood_entries": mood_entries,
            "affirmations": affirmations,
            "chat_history": chat_history,
        }

    @staticmethod
    def _mood_row_to_dict(row: sqlite3.Row) -> dict[str, object]:
        data = dict(row)
        data["emotions"] = json.loads(data.pop("emotions_json"))
        return data
